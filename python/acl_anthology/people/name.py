# Copyright 2023-2025 Marcel Bollmann <marcel@bollmann.me>
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

from attrs import define, field, setters, validators as v
from functools import cache, cached_property
from lxml import etree
from lxml.builder import E
import re
from slugify import slugify
from typing import Any, Optional, cast, Self, TypeAlias, TYPE_CHECKING
import yaml

try:
    from yaml import CDumper as Dumper
except ImportError:  # pragma: no cover
    from yaml import Dumper  # type: ignore

from ..exceptions import AnthologyException
from ..utils.attrs import track_namespec_modifications
from ..utils.ids import RE_VERIFIED_PERSON_ID
from ..utils.latex import latex_encode

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..collections import Volume, Paper, Talk
    from ..people import Person


SLUGIFY_REPLACEMENTS = (
    ["ʼ", "-"],
    ["’", "-"],
)
"""Custom replacement rules for name slugs."""


LAST_NAME_LOWERCASE_PREFIXES = {
    "al",
    "bin",
    "bint",
    "da",
    "de",
    "del",
    "de la",
    "dela",
    "della",
    "di",
    "dos",
    "du",
    "el",
    "la",
    "le",
    "van",
    "van den",
    "van der",
    "von",
    "von der",
}
"""Strings that tend to be lowercased when prefixing a last name; used for [`NameSpecification.case_normalize()`][acl_anthology.people.name.NameSpecification.case_normalize]."""

# Automatically compile LAST_NAME_LOWERCASE_PREFIXES into a regex; the prefixes
# are reverse-sorted by length so that it is always the longest string that
# matches (e.g. so that "von der Weide" matches "von der", not just "von").
_LAST_NAME_LOWERCASE_REGEX = re.compile(
    f"^({'|'.join(sorted(LAST_NAME_LOWERCASE_PREFIXES, key=lambda s: -len(s)))}) ",
    flags=re.IGNORECASE,
)

LAST_NAME_CAPITALIZATION_RULES = ((r"^Mc([a-z])", lambda p: "Mc" + p.group(1).upper()),)
"""Regex rules for heuristically normalizing last names; used for [`NameSpecification.case_normalize()`][acl_anthology.people.name.NameSpecification.case_normalize]."""


@define(frozen=True)
class Name:
    """A person's name.

    Note:
        Name objects are _frozen_, meaning they are immutable.  This allows them to be used as dictionary keys, but means that in order to change a name somewhere, you need to replace it with a new `Name` instance.

    Attributes:
        first: First name part. Can be given as `None` for people who
            only have a single name, but cannot be omitted.
        last: Last name part.
        script: The script in which the name is written; only used for non-Latin script name variants.

    Examples:
        >>> Name("Yang", "Liu")
        >>> Name(last="Liu", first="Yang")
        >>> Name(None, "Mausam")
    """

    first: Optional[str] = field(
        eq=lambda x: x if x else None, validator=v.optional(v.instance_of(str))
    )
    last: str = field(validator=(v.instance_of(str), v.min_len(1)))
    script: Optional[str] = field(
        default=None, repr=False, eq=False, validator=v.optional(v.instance_of(str))
    )

    def as_first_last(self) -> str:
        """
        Returns:
            The person's full name in the form '{first} {last}'.
        """
        if not self.first:
            return self.last
        return f"{self.first} {self.last}"

    def as_last_first(self) -> str:
        """
        Returns:
            The person's full name in the form '{last}, {first}'.
        """
        if not self.first:
            return self.last
        return f"{self.last}, {self.first}"

    def as_full(self) -> str:
        """
        Builds the full name, determining the appropriate format based on the script.

        Returns:
            For Han names, this will be '{last}{first}'; for other scripts (or if no script is given), this will be '{first} {last}'.
        """
        if not self.first:
            return self.last
        if self.script == "hani":
            return f"{self.last}{self.first}"
        return f"{self.first} {self.last}"

    @cache
    def as_bibtex(self) -> str:
        """
        Returns:
            The person's full name as formatted in a BibTeX entry.
        """
        return latex_encode(self.as_last_first())

    def score(self) -> float:
        """
        Returns:
            A score for this name that is intended for comparing different names that generate the same ID.  Names that are more likely to be the correct canonical variant should return higher scores via this function.
        """
        name = self.as_first_last()
        # Prefer longer variants
        score = float(len(name))
        # Prefer variants with non-ASCII characters or dashes
        score += sum((ord(c) > 127 or c == "-") for c in name)
        # Penalize upper-case characters after word boundaries
        score -= sum(any(c.isupper() for c in w[1:]) for w in re.split(r"\W+", name))
        # Penalize lower-case characters at word boundaries
        score -= sum(w[0].islower() if w else 0 for w in re.split(r"\W+", name))
        if name[0].islower():  # extra penalty for first name
            score -= 1
        # Penalize first names that are longer than last names (this is
        # intended to make a difference when a person has both "C, A B" and "B
        # C, A" as names)
        if self.first and len(self.first) > len(self.last):
            score += 0.5
        return score

    @cache
    def slugify(self) -> str:
        """
        Returns:
            A [slugified string](https://github.com/un33k/python-slugify#how-to-use) of the full name.
        """
        return slugify(self.as_first_last(), replacements=SLUGIFY_REPLACEMENTS)

    @classmethod
    def from_dict(cls, name: dict[str, str]) -> Name:
        """
        Parameters:
            name: A dictionary with "first" and "last" keys.

        Returns:
            A corresponding Name object.
        """
        return cls(
            name.get("first"),
            name["last"],
        )

    @classmethod
    def from_xml(cls, variant: etree._Element) -> Name:
        """
        Parameters:
            variant: An XML element of a `<variant>` block.

        Returns:
            A corresponding Name object.

        Note:
            This will work for `<author>` and `<editor>` tags as well, but those
            are more efficiently parsed within
            [NameSpecification.from_xml()][acl_anthology.people.name.NameSpecification.from_xml].
        """
        first: Optional[str] = None
        last: Optional[str] = None
        script = variant.get("script")

        for element in variant:
            if element.tag == "first":
                first = element.text
            elif element.tag == "last":
                last = element.text
        return cls(first, cast(str, last), script)

    @classmethod
    def from_string(cls, name: str) -> Name:
        """Instantiate a Name from a single string.

        Parameters:
            name: A name string given as either "{first} {last}" or "{last}, {first}".

        Returns:
            A corresponding Name object.

        Raises:
            ValueError: If `name` cannot be unambiguously parsed into first/last components; in this case, you should instantiate Name directly instead.
        """
        name = name.strip()
        if ", " in name:
            components = name.split(", ")[::-1]
        else:
            components = name.split(" ")
        if len(components) == 1:
            return cls(None, components[0])
        elif len(components) > 2:
            raise ValueError(
                f"Name string cannot be unambiguously parsed into first/last components: {name}"
            )
        return cls(components[0], components[1])

    @classmethod
    def from_(cls, name: ConvertableIntoName) -> Name:
        """Instantiate a Name dynamically from any type that can be converted into a Name.

        Parameters:
            name: A name as a string, dict, tuple, or Name instance.

        Returns:
            A corresponding Name object.

        Raises:
            ValueError:
            TypeError:
        """
        if isinstance(name, cls):
            return name
        elif isinstance(name, dict):
            return cls.from_dict(name)
        elif isinstance(name, tuple):
            return cls(*name)
        elif isinstance(name, str):
            return cls.from_string(name)
        else:  # pragma: no cover
            raise TypeError(f"Cannot instantiate Name from {type(name)}")

    def to_xml(self, tag: str = "variant") -> etree._Element:
        """
        Arguments:
            tag: Name of outer tag in which the name should be wrapped.

        Returns:
            A serialization of this name in Anthology XML format.
        """
        elem = etree.Element(tag)
        elem.extend(
            (
                E.first(self.first) if self.first else E.first(),
                E.last(self.last),
            )
        )
        if self.script is not None:
            elem.set("script", self.script)
        return elem


ConvertableIntoName: TypeAlias = Name | str | tuple[Optional[str], str] | dict[str, str]
"""A type that can be converted into a Name instance."""


def _Name_from(value: Any) -> Name:
    return Name.from_(value)


@define(
    on_setattr=[setters.convert, setters.validate, track_namespec_modifications],
)
class NameSpecification:
    """A name specification on a paper etc., containing additional data fields for information or disambiguation besides just the name.

    Attributes:
        parent: The Anthology item that this name specification belongs to.
        orcid: An ORCID that was supplied together with this name.
        affiliation: Professional affiliation.
        variants: Variant spellings of this name in different scripts.

    Note:
        The `variants` attribute is only intended for name variants stored via the
        `<variant>` tag in the XML, i.e., for a name that has a variant in a different
        script.  It is _not_ used when an author has published under different names
        (for this functionality, see [Person][acl_anthology.people.person.Person]).
    """

    _name: Name = field(converter=_Name_from)
    _id: Optional[str] = field(
        default=None,
        validator=v.optional([v.instance_of(str), v.matches_re(RE_VERIFIED_PERSON_ID)]),
    )
    parent: Optional[Paper | Volume | Talk] = field(default=None, repr=False, eq=False)
    orcid: Optional[str] = field(default=None, validator=v.optional(v.instance_of(str)))
    affiliation: Optional[str] = field(
        default=None, validator=v.optional(v.instance_of(str))
    )
    variants: list[Name] = field(
        factory=list,
        validator=v.deep_iterable(
            member_validator=v.instance_of(Name),
            iterable_validator=v.instance_of(list),
        ),
    )

    def __hash__(self) -> int:
        return hash((self.name, self.id, self.affiliation, tuple(self.variants)))

    @property
    def name(self) -> Name:
        """The person's name."""
        return self._name

    @name.setter
    def name(self, value: Any) -> None:
        # TODO: hasattr check pending the CollectionItem refactoring
        if (
            self.id is None
            and self.parent is not None
            and hasattr(self.parent, "full_id_tuple")
            and self.root.people.is_data_loaded
        ):
            person_before = self.resolve()
            self._name = _Name_from(value)
            person_after = self.root.people._resolve_namespec(self, allow_creation=True)
            if person_before != person_after:
                person_before.item_ids.remove(self.parent.full_id_tuple)
                person_after.item_ids.append(self.parent.full_id_tuple)
        else:
            self._name = _Name_from(value)

    @property
    def id(self) -> Optional[str]:
        """Unique ID for the person that this NameSpecification refers to."""
        return self._id

    @id.setter
    def id(self, value: Optional[str]) -> None:
        # TODO: duplicates code from above, should probably be refactored
        if (
            self.parent is not None
            and hasattr(self.parent, "full_id_tuple")
            and self.root.people.is_data_loaded
        ):
            person_before = self.resolve()
            self._id = value
            person_after = self.root.people._resolve_namespec(self, allow_creation=True)
            if person_before != person_after:
                person_before.item_ids.remove(self.parent.full_id_tuple)
                person_after.item_ids.append(self.parent.full_id_tuple)
        else:
            self._id = value

    @property
    def first(self) -> Optional[str]:
        """The first name component."""
        return self.name.first

    @property
    def last(self) -> str:
        """The last name component."""
        return self.name.last

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        if self.parent is None:  # pragma: no cover
            raise AnthologyException(
                "NameSpecification is not attached to an Anthology item."
            )
        return self.parent.root

    @cached_property
    def citeproc_dict(self) -> dict[str, str]:
        """A citation object corresponding to this name for use with CiteProcJSON."""
        if not self.name.first:
            return {"family": self.name.last}
        return {"family": self.name.last, "given": self.name.first}

    def case_normalize(self, force: bool = False) -> Self:
        """Try to heuristically normalize the casing of the name.

        By default, this *only* changes the name if it is currently all-lowercased or all-uppercased.

        Arguments:
            force: Always case-normalize, without checking the current casing.

        Raises:
            ValueError: If the name's script attribute is set, indicating a non-Latin script name.
        """
        if self.name.script is not None:
            # Non-Latin script variants are left unchanged;
            # should never trigger, but just in case...
            return self  # pragma: no cover

        first, last = self.name.first, self.name.last
        firstlast = self.name.as_first_last()

        if not (force or firstlast.islower() or firstlast.isupper()):
            return self

        if first is not None:
            first = first.title()
        last = last.title()
        # Prefixes
        if (m := _LAST_NAME_LOWERCASE_REGEX.match(last)) is not None:
            print(m)
            last = m.group(0).lower() + last[m.end() :]
        # Other normalization rules
        for pattern, substitute in LAST_NAME_CAPITALIZATION_RULES:
            last = re.sub(pattern, substitute, last)

        self.name = Name(first, last)
        return self

    def resolve(self) -> Person:
        """Resolve this name specification to a natural person.

        Returns:
            The Person object that this name specification resolves to.

        Raises:
            AnthologyException: If this name specification is not attached to an Anthology item (i.e., `parent` is not set).
        """
        if self.parent is None:
            raise AnthologyException(
                "Cannot resolve NameSpecification that is not attached to a paper."
            )
        return self.parent.root.people.get_by_namespec(self)

    @classmethod
    def from_xml(cls, person: etree._Element) -> NameSpecification:
        """
        Parameters:
            person: An XML element of an `<author>` or `<editor>` block.

        Returns:
            A corresponding NameSpecification object.
        """
        first: Optional[str] = None
        last: Optional[str] = None
        affiliation: Optional[str] = None
        variants = []

        for element in person:
            if element.tag == "first":
                first = element.text
            elif element.tag == "last":
                last = element.text
            elif element.tag == "affiliation":
                affiliation = element.text
            elif element.tag == "variant":
                variants.append(Name.from_xml(element))

        return cls(
            Name(first, cast(str, last)),
            id=person.get("id"),
            orcid=person.get("orcid"),
            affiliation=affiliation,
            variants=variants,
        )

    def to_xml(self, tag: str = "author") -> etree._Element:
        """
        Arguments:
            tag: Name of outer tag in which the name should be wrapped.

        Returns:
            A serialization of this name in Anthology XML format.
        """
        elem = etree.Element(tag)
        if self.id is not None:
            elem.set("id", self.id)
        if self.orcid is not None:
            elem.set("orcid", self.orcid)
        elem.extend(
            (
                E.first(self.first) if self.first else E.first(),
                E.last(self.last),
            )
        )
        if self.affiliation is not None:
            elem.append(E.affiliation(self.affiliation))
        for variant in self.variants:
            elem.append(variant.to_xml())
        return elem


class _YAMLName(yaml.YAMLObject):
    """YAMLObject representing names.

    This exists to serialize names in "flow" style (i.e. one-liner `{first: ..., last: ...}`) without having to force flow style on the entire YAML document.
    """

    yaml_dumper = Dumper
    yaml_tag = "tag:yaml.org,2002:map"  # serialize like a dictionary
    yaml_flow_style = True  # force flow style

    def __init__(self, name: Name) -> None:
        if name.first is not None:
            self.first = name.first
        self.last = name.last
        if name.script is not None:
            self.script = name.script
