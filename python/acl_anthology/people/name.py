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

from attrs import define, field, Factory
from lxml import etree
from lxml.builder import E
import re
from slugify import slugify
from typing import Optional, cast

from ..utils.latex import latex_encode


@define(frozen=True)
class Name:
    """A person's name.

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

    first: Optional[str]
    last: str
    script: Optional[str] = field(default=None, repr=False, eq=False)

    def as_first_last(self) -> str:
        """
        Returns:
            The person's full name in the form '{first} {last}'.
        """
        if self.first is None:
            return self.last
        return f"{self.first} {self.last}"

    def as_last_first(self) -> str:
        """
        Returns:
            The person's full name in the form '{last}, {first}'.
        """
        if self.first is None:
            return self.last
        return f"{self.last}, {self.first}"

    def as_bibtex(self) -> str:
        """
        Returns:
            The person's full name as formatted in a BibTeX entry.
        """
        return latex_encode(self.as_last_first())

    def score(self) -> int:
        """
        Returns:
            A score for this name that is intended for comparing different names that generate the same ID.  Names that are more likely to be the correct canonical variant should return higher scores via this function.
        """
        name = self.as_first_last()
        # Prefer longer variants
        score = len(name)
        # Prefer variants with non-ASCII characters
        score += sum((ord(c) > 127) for c in name)
        # Penalize upper-case characters after word boundaries
        score -= sum(any(c.isupper() for c in w[1:]) for w in re.split(r"\W+", name))
        # Penalize lower-case characters at word boundaries
        score -= sum(w[0].islower() if w else 0 for w in re.split(r"\W+", name))
        if name[0].islower():  # extra penalty for first name
            score -= 1
        return score

    def slugify(self) -> str:
        """
        Returns:
            A [slugified string](https://github.com/un33k/python-slugify#how-to-use) of the full name.
        """
        if not (name := self.as_first_last()):
            # Only necessary because of <https://github.com/acl-org/acl-anthology/issues/2725>
            slug = "none"
        else:
            slug = slugify(name)
        return slug

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
        else:
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
                E.first(self.first) if self.first is not None else E.first(),
                E.last(self.last),
            )
        )
        if self.script is not None:
            elem.set("script", self.script)
        return elem


ConvertableIntoName = Name | str | tuple[Optional[str], str] | dict[str, str]
"""A type that can be converted into a Name instance."""


@define
class NameSpecification:
    """A name specification on a paper etc., containing additional data fields for information or disambiguation besides just the name.

    Attributes:
        name: The person's name.
        id: Unique ID for the person that this name refers to.  Defaults to `None`.
        affiliation: Professional affiliation.  Defaults to `None`.
        variants: Variant spellings of this name in different scripts.

    Note:
        The `variants` attribute is only intended for name variants stored via the
        `<variant>` tag in the XML, i.e., for a name that has a variant in a different
        script.  It is _not_ used when an author has published under different names
        (for this functionality, see [Person][acl_anthology.people.person.Person]).
    """

    name: Name
    id: Optional[str] = field(default=None)
    affiliation: Optional[str] = field(default=None)
    variants: list[Name] = Factory(list)

    @property
    def first(self) -> Optional[str]:
        """The first name component."""
        return self.name.first

    @property
    def last(self) -> str:
        """The last name component."""
        return self.name.last

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
        elem.extend(
            (
                E.first(self.first) if self.first is not None else E.first(),
                E.last(self.last),
            )
        )
        if self.affiliation is not None:
            elem.append(E.affiliation(self.affiliation))
        for variant in self.variants:
            elem.append(variant.to_xml())
        return elem
