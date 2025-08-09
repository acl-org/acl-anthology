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

from attrs import define, field
from enum import Enum
from typing import Any, Iterator, Optional, Sequence, TYPE_CHECKING
from ..utils.attrs import auto_validate_types
from ..utils.ids import AnthologyIDTuple, build_id_from_tuple, is_valid_orcid
from . import Name

if TYPE_CHECKING:
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


@define(field_transformer=auto_validate_types)
class Person:
    """A natural person.

    Info:
        The connection between persons and Anthology items is currently derived from [name specifications][acl_anthology.people.name.NameSpecification] on volumes and papers, and not stored explicitly. This means that Person objects **cannot be used to make changes to paper metadata**, e.g. which person a paper is associated with; change the information on papers instead.

    Attributes:
        id: A unique ID for this person.
        parent: The parent Anthology instance to which this person belongs.
        item_ids: A list of volume and/or paper IDs this person has authored or edited.
        orcid: The person's ORCID.
        comment: A comment for disambiguation purposes.
        degree: The person's institution of highest degree, for disambiguation purposes.
        similar_ids: A list of person IDs with names that should be considered similar to this one.  Do **not** use this to _find_ people with similar names; that should be done via [`PersonIndex.similar`][acl_anthology.people.index.PersonIndex].  This attribute can be used to explicitly add more "similar IDs" to `PersonIndex.similar`.
        disable_name_matching: If True, no items should be assigned to this person unless they explicitly specify this person's ID.
        is_explicit: If True, this person's ID is explicitly defined in `people.yaml`.
    """

    id: str = field()
    parent: Anthology = field(repr=False, eq=False)
    _names: list[tuple[Name, NameLink]] = field(
        factory=list, converter=_name_list_converter
    )
    item_ids: list[AnthologyIDTuple] = field(
        factory=list, repr=lambda x: f"<list of {len(x)} AnthologyIDTuple objects>"
    )
    orcid: Optional[str] = field(default=None)  # validator defined below
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

    @orcid.validator
    def _check_orcid(self, _: Any, value: Optional[str]) -> None:
        if value is not None and not is_valid_orcid(value):
            raise ValueError("ORCID is not valid (wrong format or checksum)")

    @property
    def names(self) -> list[Name]:
        return [name for (name, _) in self._names]

    @names.setter
    def names(self, values: list[Name]) -> None:
        self._names = _name_list_converter(values)

    @property
    def canonical_name(self) -> Name:
        """
        Returns:
            The canonical name for this person.
        """
        try:
            # By convention, the first entry of `self.names` is treated as the
            # canonical entry
            return self._names[0][0]
        except IndexError:
            raise ValueError(f"No names defined for person '{self.id}'")

    @canonical_name.setter
    def canonical_name(self, name: Name) -> None:
        self.set_canonical_name(name)

    def add_name(self, name: Name, inferred: bool = False) -> None:
        """Add a name for this person.

        Parameters:
            name: Name that can refer to this person.
            inferred: If True, will be marked as `NameLinkingType.INFERRED`, which will e.g. cause this name to not be written to `people.yaml`.  Used when building the [`PersonIndex`][acl_anthology.people.index.PersonIndex] from the XML data; you probably don't want to set this manually.  Defaults to False.
        """
        link_type = NameLink.INFERRED if inferred else NameLink.EXPLICIT
        if not self.has_name(name):
            self._names.append((name, link_type))
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

    def has_name(self, name: Name) -> bool:
        """
        Parameters:
            name: Name to be checked.

        Returns:
            True if the given name can refer to this person.
        """
        return any(existing_name == name for (existing_name, _) in self._names)

    def set_canonical_name(self, name: Name, inferred: bool = False) -> None:
        """Set the canonical name for this person.

        Parameters:
            name: Name that should be treated as canonical for this person.
        """
        link_type = NameLink.INFERRED if inferred else NameLink.EXPLICIT
        if not self.has_name(name):
            self._names.insert(0, (name, link_type))
        else:
            self._names = [(name, link_type)] + [x for x in self._names if x[0] != name]

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
