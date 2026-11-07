# Copyright 2026 ACL Anthology
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

from abc import ABC, abstractmethod
import datetime
from typing import Any, ClassVar, TYPE_CHECKING

import attrs
from lxml import etree

from ..files import PDFReference
from ..utils.ids import AnthologyIDTuple, build_id_from_tuple

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..people import NameSpecification, Person
    from ..text import MarkupText
    from .collection import Collection


class CollectionItem(ABC):
    """Common interface for identified, contributor-linked collection items.

    Volumes, papers, frontmatter, and media share this interface without being
    represented as the same publication type.
    """

    __slots__ = ()
    id: str
    _namespec_fields: ClassVar[tuple[str, ...]] = ()

    @property
    @abstractmethod
    def collection(self) -> Collection:
        """The collection containing this item."""

    @property
    @abstractmethod
    def root(self) -> Anthology:
        """The owning Anthology."""

    @property
    @abstractmethod
    def title(self) -> MarkupText:
        """The item's title."""

    @property
    @abstractmethod
    def full_id_tuple(self) -> AnthologyIDTuple:
        """The item's persistent identifier."""

    @property
    def full_id(self) -> str:
        return build_id_from_tuple(self.full_id_tuple)

    @property
    def collection_id(self) -> str:
        return self.collection.id

    @property
    @abstractmethod
    def web_url(self) -> str:
        """The item's landing page."""

    @property
    @abstractmethod
    def ingest_date(self) -> datetime.date:
        """The date this item was added to the Anthology."""

    @property
    def namespecs(self) -> tuple[NameSpecification, ...]:
        """Name specifications explicitly attached to this item."""
        return tuple(
            spec for name in self._namespec_fields for spec in getattr(self, name)
        )

    @property
    def name_spec_item_ids(self) -> tuple[AnthologyIDTuple, ...]:
        """Items whose contributor links depend on this item's name specifications."""
        return (self.full_id_tuple,)

    @property
    def is_media(self) -> bool:
        return False

    @property
    def is_frontmatter(self) -> bool:
        return False

    def get_namespec_for(self, person: Person) -> NameSpecification:
        for spec in self.namespecs:
            if spec.resolve() is person:
                return spec
        raise ValueError(f"No NameSpecification on {self.full_id} resolves to {person}")

    @abstractmethod
    def to_xml(self) -> etree._Element:
        """Serialize this item using its own XML element."""


def update_person_itemids(
    item: CollectionItem,
    attribute: attrs.Attribute[Any],
    value: tuple[NameSpecification, ...],
) -> tuple[NameSpecification, ...]:
    """Update contributor links when any item's author/editor fields change."""
    index = item.root.people
    if not index.is_data_loaded:
        return value
    previous = {spec.resolve() for spec in item.namespecs}
    proposed = {
        index._resolve_namespec(spec, allow_creation=True)
        for name in item._namespec_fields
        for spec in (value if name == attribute.name else getattr(item, name))
    }
    for person in previous - proposed:
        person.item_ids.difference_update(item.name_spec_item_ids)
    for person in proposed - previous:
        person.item_ids.update(item.name_spec_item_ids)
    return value


def validate_pdf(item: CollectionItem, _: attrs.Attribute[Any], value: object) -> None:
    if value is None:
        return
    if not isinstance(value, PDFReference):
        raise TypeError(f"'pdf' must be Optional[PDFReference] (got {value!r})")
    if not value.is_local:
        raise ValueError(f"'pdf' must be a local file reference (got {value!r})")
    if value.name and value.name != item.full_id:
        raise ValueError(
            f"PDF reference name {value.name!r} does not match this item's full_id {item.full_id!r}"
        )
