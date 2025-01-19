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
from os import PathLike
from pathlib import Path
from typing import Any, Iterator, Optional, cast, TYPE_CHECKING

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from ..containers import SlottedDict
from ..text.markuptext import MarkupText
from ..utils.attrs import auto_validate_types, int_to_str
from ..utils.ids import infer_year, is_valid_collection_id
from ..utils.logging import get_logger
from ..utils import xml
from .event import Event
from .types import VolumeType
from .volume import Volume
from .paper import Paper

if TYPE_CHECKING:
    from ..anthology import Anthology
    from .index import CollectionIndex


log = get_logger()


@define(field_transformer=auto_validate_types)
class Collection(SlottedDict[Volume]):
    """A collection of volumes and events, corresponding to an XML file in the `data/xml/` directory of the Anthology repo.

    Provides dictionary-like functionality mapping volume IDs to [Volume][acl_anthology.collections.volume.Volume] objects in the collection.

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
            raise ValueError(f"Not a valid Collection ID: {value}")

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
            ValueError: If a volume with the given ID already exists.
        """
        volume = Volume.from_xml(self, meta)
        if volume.id in self.data:
            raise ValueError(f"Volume {volume.id} already exists in collection {self.id}")
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
            ValueError: If a volume with the given ID already exists, or if this collection has an old-style ID.
        """
        if not self.is_data_loaded:
            self.load()
        if not self.id[0].isdigit():
            raise ValueError(
                f"Can't create volume in collection {self.id} with old-style ID"
            )
        if id in self.data:
            raise ValueError(f"Volume {id} already exists in collection {self.id}")

        kwargs["parent"] = self
        if year is None:
            year = infer_year(self.id)

        volume = Volume(
            id=id,
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

    def load(self) -> None:
        """Loads the XML file belonging to this collection."""
        if self.is_data_loaded:
            return

        log.debug(f"Parsing XML data file: {self.path}")
        current_volume = cast(Volume, None)  # noqa: F841
        for _, element in etree.iterparse(
            self.path, tag=("meta", "frontmatter", "paper", "volume", "event")
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
            else:
                # Keep element around; should only apply to <event><meta> ...
                discard_element = False

            if discard_element:
                element.clear()

        if self.event is not None:
            # Events are implicitly linked to volumes defined in the same collection
            self.event.colocated_ids = [
                volume.full_id_tuple
                for volume in self.data.values()
                # Edge case: in case the <colocated> block lists a volume in
                # the same collection, don't add it twice
                if volume.full_id_tuple not in self.event.colocated_ids
            ] + self.event.colocated_ids

        self.is_data_loaded = True

    def save(self, path: Optional[PathLike[str]] = None) -> None:
        """Saves this collection as an XML file.

        Arguments:
            path: The filename to save to. If None, defaults to `self.path`.
        """
        if path is None:
            path = self.path
        collection = etree.Element("collection", {"id": self.id})
        for volume in self.volumes():
            collection.append(volume.to_xml(with_papers=True))
        if self.event is not None and self.event.is_explicit:
            collection.append(self.event.to_xml())
        xml.indent(collection)
        with open(path, "wb") as f:
            f.write(etree.tostring(collection, xml_declaration=True, encoding="UTF-8"))
