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
from typing import Optional, cast


@define
class Name:
    """A person's name.

    Attributes:
        first (Optional[str]): First name part. Can be given as `None` for people who
            only have a single name, but cannot be omitted.
        last (str): Last name part.
        id (Optional[str]): Unique ID for the individual that this name refers to.
            Defaults to `None`.
        affiliation (Optional[str]): Professional affiliation.  Defaults to `None`.
    """

    first: Optional[str]
    last: str
    id: Optional[str] = field(default=None)
    affiliation: Optional[str] = field(default=None)
    variants: list[NameVariant] = Factory(list)

    @property
    def full(self) -> str:
        """The person's full name, usually '<First name> <Last name>'."""
        if self.first is None:
            return self.last
        return f"{self.first} {self.last}"

    @classmethod
    def from_xml(cls, person: etree._Element) -> Name:
        """Instantiates a new name from an <author> or <editor> block in the XML."""
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
