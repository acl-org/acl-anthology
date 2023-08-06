# Copyright 2023 Marcel Bollmann <marcel@bollmann.me>
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
from slugify import slugify
from typing import Optional, cast


@define
class Name:
    """A person's name.

    Attributes:
        first: First name part. Can be given as `None` for people who
            only have a single name, but cannot be omitted.
        last: Last name part.
        id: Unique ID for the person that this name refers to.
            Defaults to `None`.
        affiliation: Professional affiliation.  Defaults to `None`.
        variants: Variant spellings of this name in different scripts.

    Examples:
        >>> Name("Yang", "Liu")
        >>> Name(last="Liu", first="Yang")
        >>> Name(None, "Mausam")
    """

    first: Optional[str]
    last: str
    id: Optional[str] = field(default=None)
    affiliation: Optional[str] = field(default=None)
    variants: list[NameVariant] = Factory(list)

    def as_first_last(self) -> str:
        """
        Returns:
            The person's full name in the form '[First name] [Last name]'.
        """
        if self.first is None:
            return self.last
        return f"{self.first} {self.last}"

    def match(self, other: Name) -> bool:
        """
        Parameters:
            other: A name to check against `self`.

        Returns:
            True if the first/last name components of `other` match this name.
        """
        return (self.first == other.first) and (self.last == other.last)

    def slugify(self) -> str:
        """
        Returns:
            A [slugified string](https://github.com/un33k/python-slugify#how-to-use) of the full name.
        """
        slug = slugify(self.as_first_last())
        if not slug:
            slug = "none"
        return slug

    @classmethod
    def from_dict(cls, person: dict[str, str]) -> Name:
        """
        Parameters:
            person: A dictionary with "first" and "last" keys.

        Returns:
            A corresponding Name object.
        """
        return cls(
            person.get("first"),
            person["last"],
        )

    @classmethod
    def from_xml(cls, person: etree._Element) -> Name:
        """
        Parameters:
            person: An XML element of an `<author>` or `<editor>` block.

        Returns:
            A corresponding Name object.
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
                variants.append(NameVariant.from_xml(element))

        return cls(
            first,
            cast(str, last),
            id=person.get("id"),
            affiliation=affiliation,
            variants=variants,
        )


@define
class NameVariant:
    """A variant of a person's name in a different script.

    Note:
        This is only intended for name variants stored via the `<variant>` tag in
        the XML, i.e., for a name that has a variant in a different script.
        It is _not_ used when an author has published under different names (for
        this functionality, see [Person][acl_anthology.people.person.Person]).

    Attributes:
        first (Optional[str]): First name part. Can be given as `None` for people who
            only have a single name, but cannot be omitted.
        last (str): Last name part.
        script (str): Script in which this name variant is written.
    """

    first: Optional[str]
    last: str
    script: str

    @classmethod
    def from_xml(cls, variant: etree._Element) -> NameVariant:
        first: Optional[str] = None
        last: Optional[str] = None

        for element in variant:
            if element.tag == "first":
                first = element.text
            elif element.tag == "last":
                last = element.text

        return cls(first, cast(str, last), str(variant.attrib["script"]))
