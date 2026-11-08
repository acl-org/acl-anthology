# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Provides the base classes for all items in a collection that have an Anthology ID, such as volumes and papers."""

from __future__ import annotations

from abc import ABC, abstractmethod
import attrs
from attrs import define, field, setters, validators
import datetime
from typing import Any, Generic, Optional, TypeVar, TYPE_CHECKING

from .. import constants
from ..containers import DictMixin, repr_data_dict
from ..exceptions import AnthologyInvalidIDError
from ..files import PDFReference, URLReference, validate_url_tuple
from ..people import NameSpecification
from ..text import MarkupText, to_markuptext
from ..utils.attrs import (
    auto_validate_types,
    date_to_str,
    int_to_str,
    track_modifications,
    ConvertableIntoDate,
)
from ..utils.ids import build_id, is_valid_item_id, AnthologyIDTuple

if TYPE_CHECKING:
    from ..anthology import Anthology
    from . import Collection, Volume

ParentT = TypeVar("ParentT", bound="Collection | Volume")
ChildT = TypeVar("ChildT")


def _update_person_itemids(
    item: CollectionItem[Any],
    attr: attrs.Attribute[Any],
    value: tuple[NameSpecification, ...],
) -> tuple[NameSpecification, ...]:
    """Update the `item_ids` of persons linked to or unlinked from a collection item.

    Intended to be called from `on_setattr` of an [attrs.field][].
    """
    person_index = item.root.people
    if person_index.is_data_loaded:
        old_value = getattr(item, attr.name)
        # Update item_ids for people who are no longer on this item
        for namespec in set(old_value) - set(value):
            person = namespec.resolve()
            person.item_ids.discard(item.full_id_tuple)
        # Update item_ids for people who are newly on this item
        for namespec in set(value) - set(old_value):
            person = person_index._resolve_namespec(namespec, allow_creation=True)
            person.item_ids.add(item.full_id_tuple)
    return value


@define(
    field_transformer=auto_validate_types,
    on_setattr=[setters.convert, setters.validate, track_modifications],
)
class CollectionItem(Generic[ParentT], ABC):
    """Abstract base class for all items in a collection that have an Anthology ID, such as volumes and papers.

    This class cannot be instantiated directly.  Subclasses must implement the abstract properties [collection][acl_anthology.collections.collectionitem.CollectionItem.collection], [full_id_tuple][acl_anthology.collections.collectionitem.CollectionItem.full_id_tuple], [web_url][acl_anthology.collections.collectionitem.CollectionItem.web_url], and [namespecs][acl_anthology.collections.collectionitem.CollectionItem.namespecs].

    Attributes: Required Attributes:
        id: The ID of this item, local to its parent (e.g. "main" for a volume, or "42" for a paper).
        parent: The object this item belongs to.
        title: The title of this item.  (Keyword-only argument.)

    Attributes: Tuple Attributes:
        urls: Links to external, non-locally-hosted resources associated with this item (e.g. supplementary materials), as tuples of `(type_of_link, reference)`; can be empty.

    Attributes: Optional Attributes:
        doi: The DOI for this item.
        pdf: A reference to this item's PDF.
    """

    id: str = field(converter=int_to_str)  # validator defined below
    parent: ParentT = field(repr=False, eq=False)

    # All fields below are keyword-only, so that subclasses can still define
    # positional fields without default values
    title: MarkupText = field(converter=to_markuptext, kw_only=True)
    urls: tuple[tuple[str, URLReference], ...] = field(
        default=(),
        converter=tuple,
        validator=validators.deep_iterable(
            member_validator=validate_url_tuple,
            iterable_validator=validators.instance_of(tuple),
        ),  # necessary because auto_validate_types cannot cover this
        kw_only=True,
    )
    doi: Optional[str] = field(default=None, kw_only=True)
    _ingest_date: Optional[str] = field(
        default=None,
        converter=date_to_str,
        validator=validators.optional(validators.matches_re(constants.RE_ISO_DATE)),
        kw_only=True,
    )
    _pdf: Optional[PDFReference] = field(default=None, kw_only=True)

    @id.validator
    def _check_id(self, _: Any, value: str) -> None:
        if not is_valid_item_id(value):
            raise AnthologyInvalidIDError(value, f"Not a valid {type(self).__name__} ID")

    @_pdf.validator
    def _check_pdf(self, _: Any, value: Any) -> None:
        # Adding this validator disables auto_validate_types for this field, so
        # we need to check the type explicitly here, too.
        if value is None:
            return
        if not isinstance(value, PDFReference):
            raise TypeError(
                f"'pdf' must be Optional[{PDFReference!r}] (got '{value!r}' that is a {type(value)!r})"
            )
        # <pdf> must be a local file reference according to the schema
        if not value.is_local:
            raise ValueError(
                f"'pdf' of a {type(self).__name__} must be a local file reference (got '{value}')"
            )
        # If a name is given, it must match what would be derived automatically
        # (an empty name, e.g. from PDFReference.from_xml(), is always fine)
        if value.name and value.name != self.full_id:
            raise ValueError(
                f"PDF reference name {value.name!r} does not match this {type(self).__name__.lower()}'s full_id {self.full_id!r}"
            )

    @property
    @abstractmethod
    def collection(self) -> Collection:
        """The collection this item belongs to."""

    @property
    def collection_id(self) -> str:
        """The collection ID this item belongs to."""
        return self.collection.id

    @property
    def full_id(self) -> str:
        """The full anthology ID of this item (e.g. "2022.emnlp-main" or "2022.emnlp-main.1")."""
        return build_id(*self.full_id_tuple)

    @property
    @abstractmethod
    def full_id_tuple(self) -> AnthologyIDTuple:
        """The full anthology ID of this item, as a tuple (e.g. `("2022.emnlp", "main", None)` or `("2022.emnlp", "main", "1")`)."""

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.collection.root

    @property
    @abstractmethod
    def web_url(self) -> str:
        """The URL of this item's landing page on the ACL Anthology website."""

    @property
    @abstractmethod
    def namespecs(self) -> tuple[NameSpecification, ...]:
        """All name specifications on this item."""

    @property
    def ingest_date(self) -> datetime.date:
        """The date when this item was added to the Anthology.  If not set explicitly, may be inherited from the parent, or will use [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE] instead."""
        if self._ingest_date is None:
            return self._default_ingest_date()
        return datetime.date.fromisoformat(self._ingest_date)

    @ingest_date.setter
    def ingest_date(self, value: ConvertableIntoDate) -> None:
        self._ingest_date = date_to_str(value)

    def _default_ingest_date(self) -> datetime.date:
        """The ingestion date to use if none is set explicitly on this item."""
        return constants.UNKNOWN_INGEST_DATE

    @property
    def pdf(self) -> Optional[PDFReference]:
        """A reference to this item's PDF.

        `<pdf>` always refers to a local file, so the reference's `name` is derived from this item's `full_id` rather than stored -- it is not present in the XML.
        """
        if self._pdf is None:
            return None
        return attrs.evolve(self._pdf, name=self.full_id)

    @pdf.setter
    def pdf(self, value: Optional[PDFReference]) -> None:
        self._pdf = value


@define(
    field_transformer=auto_validate_types,
    on_setattr=[setters.convert, setters.validate, track_modifications],
)
class ContainerItem(CollectionItem[ParentT], DictMixin[ChildT]):
    """Abstract base class for collection items that also act as dictionary-like containers of other items, such as volumes containing papers.

    This class cannot be instantiated directly.  See [CollectionItem][acl_anthology.collections.collectionitem.CollectionItem] for the attributes of all collection items, and [DictMixin][acl_anthology.containers.DictMixin] for the dictionary-like functionality.
    """

    data: dict[str, ChildT] = field(
        init=False,
        repr=repr_data_dict,
        factory=dict,
        metadata={"repr_omits_field_name": True},
    )
    is_data_loaded: bool = field(
        init=False, repr=True, default=True, metadata={"repr_omit_if": True}
    )
