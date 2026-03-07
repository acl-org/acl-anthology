# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import attrs
from attrs import define, field, setters
from enum import Enum
from typing import Any, Iterator, Optional, Sequence, TYPE_CHECKING
import warnings

from ..exceptions import AnthologyException, AnthologyInvalidIDError
from ..utils.attrs import auto_validate_types
from ..utils.ids import (
    AnthologyID,
    AnthologyIDTuple,
    build_id_from_tuple,
    is_valid_orcid,
    is_verified_person_id,
    parse_id,
    RE_ORCID,
)
from . import Name

if TYPE_CHECKING:
    from . import NameSpecification
    from ..anthology import Anthology
    from ..collections import Paper, Volume


class NameLink(Enum):
    """How a Name was connected to a Person."""

    EXPLICIT = "explicit"
    """Name is explicitly listed in `people.yaml` file."""

    INFERRED = "inferred"
    """Name was connected to this Person via slug matching heuristic."""


def _name_list_converter(
    name_list: Sequence[Name | tuple[Name, NameLink]],
) -> list[tuple[Name, NameLink]]:
    return [
        (item, NameLink.EXPLICIT) if isinstance(item, Name) else item
        for item in name_list
    ]


def _orcid_converter_and_validator(
    _: Person, __: attrs.Attribute[Any], value: object
) -> Optional[str]:
    if value is None:
        return None
    value = str(value).upper()
    # e.g. "https://orcid.org/0000-0002-1297-6794" -> "0000-0002-1297-6794"
    if len(value) > 19 and (m := RE_ORCID.search(value)) is not None:
        value = m.group(0)
    if not is_valid_orcid(value):
        raise ValueError(f"ORCID is not valid (wrong format or checksum): {value}")
    return value


def _update_person_index(person: Person, attr: attrs.Attribute[Any], value: str) -> str:
    """Update the [PersonIndex][acl_anthology.people.index.PersonIndex].

    Intended to be called from `on_setattr` of an [attrs.field][].
    """
    index = person.parent.people
    if attr.name == "id":
        index._update_id(person.id, value)
    elif attr.name == "orcid":
        index._update_orcid(person.id, person.orcid, value)
    return value


@define(field_transformer=auto_validate_types)
class Person:
    """A natural person.

    Info:
        The connection between persons and Anthology items is derived from [name specifications][acl_anthology.people.name.NameSpecification] on volumes and papers, and not stored explicitly. This means that Person objects **cannot be used to make changes to paper metadata**, e.g. which person a paper is associated with or under which name; change the information on papers instead.

        Person objects **can** be used to make changes to metadata that appears in `people.yaml`, such as ORCID, comment, degree, and alternative names for this person.

    Attributes:
        id: A unique ID for this person.  Do not change this attribute directly; use [`change_id()`][acl_anthology.people.person.Person.change_id], [`make_explicit()`][acl_anthology.people.person.Person.make_explicit], or [`merge_into()`][acl_anthology.people.person.Person.merge_into] instead.
        parent: The parent Anthology instance to which this person belongs.
        item_ids: A list of volume and/or paper IDs this person has authored or edited.
        orcid: The person's ORCID.
        comment: A comment for disambiguation purposes.
        degree: The person's institution of highest degree, for disambiguation purposes.
        similar_ids: A list of person IDs with names that should be considered similar to this one.  Do **not** use this to _find_ people with similar names; that should be done via [`PersonIndex.similar`][acl_anthology.people.index.PersonIndex].  This attribute can be used to explicitly add more "similar IDs" that are not automatically derived via similar names.
        disable_name_matching: If True, no items should be assigned to this person unless they explicitly specify this person's ID.
        is_explicit: If True, this person's ID is explicitly defined in `people.yaml`.  You probably want to use [`make_explicit()`][acl_anthology.people.person.Person.make_explicit] rather than change this attribute.
    """

    id: str = field(on_setattr=[setters.validate, _update_person_index])
    parent: Anthology = field(repr=False, eq=False)
    _names: list[tuple[Name, NameLink]] = field(
        factory=list, converter=_name_list_converter
    )
    item_ids: list[AnthologyIDTuple] = field(
        factory=list, repr=lambda x: f"<list of {len(x)} AnthologyIDTuple objects>"
    )
    orcid: Optional[str] = field(
        default=None,
        on_setattr=[_orcid_converter_and_validator, _update_person_index],
    )
    comment: Optional[str] = field(default=None)
    degree: Optional[str] = field(default=None)
    similar_ids: list[str] = field(factory=list)
    disable_name_matching: Optional[bool] = field(default=False, converter=bool)
    is_explicit: Optional[bool] = field(default=False, converter=bool)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Person):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def names(self) -> list[Name]:
        """A list of all names associated with this person."""
        return [name for (name, _) in self._names]

    @names.setter
    def names(self, values: list[Name]) -> None:
        for name, _ in self._names:
            self.parent.people._remove_name(self.id, name)
        for name in values:
            self.parent.people._add_name(self.id, name)
        self._names = _name_list_converter(values)

    @property
    def canonical_name(self) -> Name:
        """The canonical name for this person."""
        try:
            # By convention, the first entry of `self.names` is treated as the
            # canonical entry
            return self._names[0][0]
        except IndexError:
            raise ValueError(f"No names defined for person '{self.id}'")

    @canonical_name.setter
    def canonical_name(self, name: Name) -> None:
        self._set_canonical_name(name)

    def _set_canonical_name(self, name: Name, inferred: bool = False) -> None:
        """Set the canonical name for this person.

        Outside of the library, use Person.canonical_name = ...

        Parameters:
            name: Name that should be treated as canonical for this person.
            inferred: Marks the canonical name as inferred (used inside the name slug matching algorithm).
        """
        link_type = NameLink.INFERRED if inferred else NameLink.EXPLICIT
        if not self.has_name(name):
            self._names.insert(0, (name, link_type))
        else:
            self._names = [(name, link_type)] + [x for x in self._names if x[0] != name]

    def add_name(self, name: Name, inferred: bool = False) -> None:
        """Add a name for this person.

        Parameters:
            name: Name that can refer to this person.
            inferred: If True, will be marked as `NameLinkingType.INFERRED`, which will e.g. cause this name to not be written to `people.yaml`.  Used when building the [`PersonIndex`][acl_anthology.people.index.PersonIndex] from the XML data; you probably don't want to set this manually.  Defaults to False.
        """
        link_type = NameLink.INFERRED if inferred else NameLink.EXPLICIT
        if not self.has_name(name):
            self._names.append((name, link_type))
            self.parent.people._add_name(self.id, name)
        elif (name, link_type) not in self._names:
            # ensure that name is re-inserted at same position
            idx = self.names.index(name)
            del self._names[idx]
            self._names.insert(idx, (name, link_type))

    def remove_name(self, name: Name) -> None:
        """Remove an explicit name for this person.

        Warning:
            If the name is still used on a paper or volume with the ID of this person, this may result in an Exception during index building.  Names that were implicitly linked to this person cannot be removed this way, as the name would simply reappear on next load.

        Parameters:
            name: Name that should be removed from this person.

        Raises:
            ValueError: If this name was not explicitly linked to this person.
        """
        self._names.remove((name, NameLink.EXPLICIT))
        self.parent.people._remove_name(self.id, name)

    def has_name(self, name: Name) -> bool:
        """
        Parameters:
            name: Name to be checked.

        Returns:
            True if the given name can refer to this person.
        """
        return any(existing_name == name for (existing_name, _) in self._names)

    def change_id(self, new_id: str) -> None:
        """Change this person's ID.

        This updates `self.id`, but also ensures that all papers/items with the old ID are updated to the new one.

        Parameters:
            new_id: The new ID for this person, which must match [`RE_VERIFIED_PERSON_ID`][acl_anthology.utils.ids.RE_VERIFIED_PERSON_ID].

        Raises:
            AnthologyException: If `self.explicit` is False.
            AnthologyInvalidIDError: If the supplied ID is not well-formed, or if it already exists in the PersonIndex.
        """
        if new_id in self.parent.people:
            exc = AnthologyInvalidIDError(new_id, f"Person ID already exists: {new_id}")
            exc.add_note("Did you want to use merge_into() instead?")
            raise exc
        if not self.is_explicit:
            exc2 = AnthologyException("Can only update ID for explicit person")
            exc2.add_note("Did you want to use make_explicit() instead?")
            raise exc2
        if not is_verified_person_id(new_id):
            raise AnthologyInvalidIDError(
                new_id, f"Not a valid verified-person ID: {new_id}"
            )

        for namespec in list(self.namespecs()):
            # We're not calling .set_id_on_items() since only _explicitly_
            # linked papers should get updated with the new ID
            if namespec.id == self.id:
                namespec.id = new_id
        self.id = new_id  # triggers update in PersonIndex

    def make_explicit(
        self, new_id: Optional[str] = None, skip_setting_ids: bool = False
    ) -> None:
        """Turn this person that was implicitly created into an explicitly-represented one.

        This will result in this person having an explicit entry in `people.yaml` with all names that are currently associated with this person.  It will also add their new explicit ID to all papers and volumes currently associated with this person.

        Parameters:
            new_id: The new ID for this person, which must match [`RE_VERIFIED_PERSON_ID`][acl_anthology.utils.ids.RE_VERIFIED_PERSON_ID].  If not specified, will try to generate one automatically based on this person's canonical name (and, potentially, ORCID).

        Raises:
            AnthologyException: If `self.explicit` is already True, or if the ID already exists in the PersonIndex (both if it was supplied or auto-generated).
            AnthologyInvalidIDError: If the supplied ID is not valid.
        """
        if self.is_explicit:
            raise AnthologyException(f"Person '{self.id}' is already explicit")
        if new_id is None:
            new_id = self.parent.people.generate_person_id(self)
        elif not is_verified_person_id(new_id):
            raise AnthologyInvalidIDError(
                new_id, f"Not a valid verified-person ID: {new_id}"
            )
        elif new_id in self.parent.people:
            raise AnthologyException(f"ID already exists in the index: {new_id}")

        self.is_explicit = True
        if not skip_setting_ids:
            self.set_id_on_items()
        self.id = new_id  # triggers update in PersonIndex
        self._names = [(name, NameLink.EXPLICIT) for name, _ in self._names]

    @warnings.deprecated(
        "Person.merge_with_explicit() is deprecated in favor of Person.merge_into()"
    )
    def merge_with_explicit(self, person: Person) -> None:  # pragma: no cover
        self.merge_into(person)

    def merge_into(self, other: Person) -> None:
        """Merge this person and all their publications into another person.

        This will move all attributes, papers, and volumes currently associated with this person over to the `other` person.  The other person's ID will be explicitly set on all items currently associated with this person.  If an attribute (e.g. ORCID iD, comment) is already set on the other person, it will _not_ be changed.

        Parameters:
            other: A person to merge this person into.  Must be explicit.

        Raises:
            AnthologyException: If `other.explicit` is False.
        """
        if not other.is_explicit:
            raise AnthologyException(
                f"Can only merge with explicit persons; not '{other.id}'"
            )

        for namespec in list(self.namespecs()):
            namespec.id = other.id
        other.item_ids.extend(self.item_ids)
        self.item_ids = []

        for attr in ("orcid", "comment", "degree", "disable_name_matching"):
            if (
                getattr(other, attr) is None
                and (value := getattr(self, attr)) is not None
            ):
                setattr(other, attr, value)
        other.similar_ids.extend(self.similar_ids)
        for name in self.names:
            other.add_name(name, inferred=False)

    def set_id_on_items(
        self, exclude: Optional[list[AnthologyID | Paper | Volume]] = None
    ) -> None:
        """Set this person's ID explicitly on all Anthology items associated with them.

        Parameters:
            exclude: An optional list of Anthology items or IDs that should be excluded.

        Warning:
            This should only be done if it is certain that all papers currently linked to this person actually belong to them, including those that were implicitly linked (i.e. via name matching).

        Raises:
            AnthologyException: If `self.explicit` is False.
        """
        if not self.is_explicit:
            exc = AnthologyException("Can only set ID for explicit person")
            exc.add_note("Did you want to use make_explicit() instead?")
            raise exc

        from ..collections import Paper, Volume

        excluded_ids = set()
        if exclude:
            for item in exclude:
                if isinstance(item, (Paper, Volume)):
                    excluded_ids.add(item.full_id_tuple)
                else:
                    excluded_ids.add(parse_id(item))

        for namespec in list(self.namespecs()):
            if not (
                isinstance(namespec.parent, (Paper, Volume))
                and namespec.parent.full_id_tuple in excluded_ids
            ):
                namespec.id = self.id

    def anthology_items(self) -> Iterator[Paper | Volume]:
        """Returns an iterator over all Anthology items associated with this person, regardless of their type."""
        # TODO: This does not consider talks yet!
        for anthology_id in self.item_ids:
            item = self.parent.get(anthology_id)
            if item is None:
                raise ValueError(
                    f"Person {self.id} lists associated item {build_id_from_tuple(anthology_id)}, which doesn't exist"
                )  # pragma: no cover
            # TODO: typing issue will be resolved later with CollectionItem refactoring
            yield item  # type: ignore

    def namespecs(self) -> Iterator[NameSpecification]:
        """Returns an iterator over all NameSpecifications that resolve to this person."""
        for item in self.anthology_items():
            yield item.get_namespec_for(self)

    def papers(self) -> Iterator[Paper]:
        """Returns an iterator over all papers associated with this person.

        Note:
            This will return papers where this person is an author, as well as frontmatter of volumes where they are an editor. It will _not_ include all other papers in volumes they have edited.
        """
        for anthology_id in self.item_ids:
            paper_id = anthology_id[-1]
            if paper_id is not None:
                paper = self.parent.get_paper(anthology_id)
                if paper is None:
                    raise ValueError(
                        f"Person {self.id} lists associated paper {build_id_from_tuple(anthology_id)}, which doesn't exist"
                    )  # pragma: no cover
                yield paper

    def volumes(self) -> Iterator[Volume]:
        """Returns an iterator over all volumes this person has edited."""
        for anthology_id in self.item_ids:
            paper_id = anthology_id[-1]
            if paper_id is None:
                volume = self.parent.get_volume(anthology_id)
                if volume is None:
                    raise ValueError(
                        f"Person {self.id} lists associated volume {build_id_from_tuple(anthology_id)}, which doesn't exist"
                    )  # pragma: no cover
                yield volume
