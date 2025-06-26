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

import sys
from attrs import define, field, validators as v
from lxml import etree
from pathlib import Path
from typing import Any, Iterator, Optional, cast, TYPE_CHECKING

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from ..containers import SlottedDict
from ..exceptions import AnthologyDuplicateIDError, AnthologyInvalidIDError
from ..text.markuptext import MarkupText
from ..utils.attrs import auto_validate_types, int_to_str
from ..utils.ids import infer_year, is_valid_collection_id
from ..utils.logging import get_logger
from ..utils import xml
from .event import Event
from .types import EventLinkingType, VolumeType
from .volume import Volume
from .paper import Paper

if TYPE_CHECKING:
    from _typeshed import StrPath
    from ..anthology import Anthology
    from .index import CollectionIndex


log = get_logger()


@define(field_transformer=auto_validate_types)
class Collection(SlottedDict[Volume]):
    """A collection of volumes and events, corresponding to an XML file in the `data/xml/` directory of the Anthology repo.

    Provides dictionary-like functionality mapping volume IDs to [Volume][acl_anthology.collections.volume.Volume] objects in the collection.

    Info:
        To create a new collection, use [`CollectionIndex.create()`][acl_anthology.collections.index.CollectionIndex.create].

    Attributes: Required Attributes:
        id: The ID of this collection (e.g. "L06" or "2022.emnlp").
        parent: The parent CollectionIndex instance to which this collection belongs.
        path: The path of the XML file representing this collection.

    Attributes: Non-Init Attributes:
        event: An event represented by this collection.
        is_data_loaded: A flag indicating whether the XML file has already been loaded.
    """

    id: str = field(converter=int_to_str)
    parent: CollectionIndex = field(repr=False, eq=False)
    path: Path = field(converter=Path)
    event: Optional[Event] = field(
        init=False,
        repr=False,
        default=None,
        validator=v.optional(v.instance_of(Event)),
    )
    is_data_loaded: bool = field(init=False, repr=True, default=False)

    @id.validator
    def _check_id(self, _: Any, value: str) -> None:
        if not is_valid_collection_id(value):
            raise AnthologyInvalidIDError(value, "Not a valid Collection ID")

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.parent.parent

    def volumes(self) -> Iterator[Volume]:
        """An iterator over all Volume objects in this collection."""
        if not self.is_data_loaded:
            self.load()
        yield from self.data.values()

    def papers(self) -> Iterator[Paper]:
        """An iterator over all Paper objects in all volumes in this collection."""
        for volume in self.volumes():
            yield from volume.papers()

    def get_event(self) -> Optional[Event]:
        """An Event explicitly defined in this collection, if any."""
        if not self.is_data_loaded:
            self.load()
        return self.event

    def _add_volume_from_xml(self, meta: etree._Element) -> Volume:
        """Creates a new volume belonging to this collection.

        Parameters:
            meta: The `<meta>` element for the volume.

        Returns:
            The created volume.

        Raises:
            AnthologyDuplicateIDError: If a volume with the given ID already exists.
        """
        volume = Volume.from_xml(self, meta)
        if volume.id in self.data:
            raise AnthologyDuplicateIDError(
                volume.id, "Volume already exists in collection {self.id}"
            )
        self.data[volume.id] = volume
        return volume

    def _set_event_from_xml(self, meta: etree._Element) -> None:
        """Creates and sets a new event belonging to this collection.

        Parameters:
            meta: The `<event>` element.

        Raises:
            ValueError: If an event had already been set; collections may only have a single event.
        """
        if self.event is not None:
            raise ValueError(f"Event already defined in collection {self.id}")
        self.event = Event.from_xml(self, meta)

    def validate_schema(self) -> Self:
        """Validates the XML file belonging to this collection against the RelaxNG schema.

        Raises:
            lxml.etree.DocumentInvalid: If the XML file does not validate against the schema.
        """
        self.root.relaxng.assertValid(etree.parse(self.path))
        return self

    def create_volume(
        self,
        id: str,
        title: MarkupText,
        year: Optional[str] = None,
        type: VolumeType = VolumeType.PROCEEDINGS,
        **kwargs: Any,
    ) -> Volume:
        """Create a new [Volume][acl_anthology.collections.volume.Volume] object in this collection.

        Parameters:
            id: The ID of the new volume.
            title: The title of the new volume.
            year: The year of the new volume (optional); if None, will infer the year from this collection's ID.
            type: Whether this is a journal or proceedings volume; defaults to [VolumeType.PROCEEDINGS][acl_anthology.collections.types.VolumeType].
            **kwargs: Any valid list or optional attribute of [Volume][acl_anthology.collections.volume.Volume].

        Returns:
            The created [Volume][acl_anthology.collections.volume.Volume] object.

        Raises:
            AnthologyDuplicateIDError: If a volume with the given ID already exists.
            ValueError: If this collection has an old-style ID.
        """
        if not self.is_data_loaded:
            self.load()
        if not self.id[0].isdigit():
            raise ValueError(
                f"Can't create volume in collection {self.id} with old-style ID"
            )
        if id in self.data:
            raise AnthologyDuplicateIDError(
                id, f"Volume already exists in collection {self.id}"
            )

        if year is None:
            year = infer_year(self.id)

        volume = Volume(
            id=id,
            parent=self,
            booktitle=title,
            year=year,
            type=type,
            **kwargs,
        )
        volume.is_data_loaded = True

        # For convenience, if editors were given, we add them to the index here
        if volume.editors:
            self.root.people._add_to_index(volume.editors, volume.full_id_tuple)

        self.data[id] = volume
        return volume

    def create_event(
        self,
        id: Optional[str] = None,
        **kwargs: Any,
    ) -> Event:
        """Create a new (explicit) [Event][acl_anthology.collections.event.Event] object in this collection.

        Parameters:
            id: The ID of the event; must follow [`RE_EVENT_ID`][acl_anthology.constants.RE_EVENT_ID].  If None (default), and this collection has a new-style ID, will generate an event ID based on this (e.g., collection "2022.emnlp" will generate event "emnlp-2022").
            **kwargs: Any valid list or optional attribute of [Event][acl_anthology.collections.event.Event].

        Returns:
            The created [Event][acl_anthology.collections.event.Event] object.

        Raises:
            ValueError: If an explicitly defined event already exists in this collection, or if `id` was None and this collection has an old-style ID.

        Danger:
            If the [event index][acl_anthology.collections.eventindex.EventIndex] is loaded _and_ an event with the given ID is already implicitly defined, the newly created event will replace that one, _but will inherit its co-located IDs_.  It is currently not possible to explicitly create an event without also explicitly linking all co-located item IDs to it, but for performance reasons (this linking needs to load the entire Anthology data), it _only happens when the event index is loaded._  This means that e.g. entirely new proceedings can be created without the performance impact of loading everything, but for adding new events to existing proceedings, the event index should probably be loaded first.
        """
        if not self.is_data_loaded:
            self.load()
        if self.event is not None:
            raise ValueError(
                f"Can't create event in collection {self.id}: already exists"
            )
        if id is None:
            if not self.id[0].isdigit():
                raise ValueError(
                    f"Can't create event in collection {self.id} without an explicitly given ID"
                )
            id = "-".join(self.id.split(".")[::-1])

        self.event = Event(
            id=id,
            parent=self,
            is_explicit=True,
            **kwargs,
        )
        self.root.events._add_to_index(self.event)
        return self.event

    def load(self) -> None:
        """Loads the XML file belonging to this collection."""
        if self.is_data_loaded:
            return

        log.debug(f"Parsing XML data file: {self.path}")
        current_volume = cast(Volume, None)  # noqa: F841
        for _, element in etree.iterparse(
            self.path,
            tag=("meta", "frontmatter", "paper", "volume", "event", "collection"),
        ):
            discard_element = True
            if (
                element.tag == "meta"
                and (parent := element.getparent()) is not None
                and parent.tag != "event"
            ):
                # Seeing a volume's <meta> block instantiates a new volume
                current_volume = self._add_volume_from_xml(element)  # noqa: F841
            elif element.tag in ("paper", "frontmatter"):
                current_volume._add_paper_from_xml(element)
            elif element.tag == "volume":
                current_volume = cast(Volume, None)  # noqa: F481
            elif element.tag == "event":
                self._set_event_from_xml(element)
                element.clear()
            elif element.tag == "collection":
                if element.get("id") != self.id:
                    raise AnthologyInvalidIDError(
                        element.get("id"),
                        f"File {self.path} does not contain Collection {self.id}",
                    )
            else:
                # Keep element around; should only apply to <event><meta> ...
                discard_element = False

            if discard_element:
                element.clear()

        if self.event is not None:
            # Events are implicitly linked to volumes defined in the same collection
            self.event.colocated_ids = [
                (volume.full_id_tuple, EventLinkingType.INFERRED)
                for volume in self.data.values()
                # Edge case: in case the <colocated> block lists a volume in
                # the same collection, don't add it twice
                if (volume.full_id_tuple, EventLinkingType.EXPLICIT)
                not in self.event.colocated_ids
            ] + self.event.colocated_ids

        self.is_data_loaded = True

    def save(self, path: Optional[StrPath] = None, minimal_diff: bool = True) -> None:
        """Saves this collection as an XML file.

        Arguments:
            path: The filename to save to. If None, defaults to `self.path`.
            minimal_diff: If True (default), will compare against an existing XML file in `self.path` to minimize the difference, i.e., to prevent noise from changes in the XML that make no semantic difference.  See [`utils.xml.ensure_minimal_diff`][acl_anthology.utils.xml.ensure_minimal_diff] for details.
        """
        if path is None:
            path = self.path
        collection = etree.Element("collection", {"id": self.id})
        for volume in self.volumes():
            collection.append(volume.to_xml(with_papers=True))
        if self.event is not None and self.event.is_explicit:
            collection.append(self.event.to_xml())
        if self.path.is_file() and minimal_diff:
            reference = etree.parse(self.path).getroot()
            xml.indent(collection)  # allows for better checking for equivalence
            xml.ensure_minimal_diff(collection, reference)
        xml.indent(collection)
        with open(path, "wb") as f:
            f.write(etree.tostring(collection, xml_declaration=True, encoding="UTF-8"))
