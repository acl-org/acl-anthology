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

from attrs import define, field
from lxml import etree
from pathlib import Path
from typing import Iterator, cast, TYPE_CHECKING

from ..containers import SlottedDict
from ..utils.logging import get_logger
from .volume import Volume
from .paper import Paper

if TYPE_CHECKING:
    from ..anthology import Anthology
    from .index import CollectionIndex


log = get_logger()


@define
class Collection(SlottedDict[Volume]):
    """A collection of volumes and events, corresponding to an XML file in the `data/xml/` directory of the Anthology repo.

    Provides dictionary-like functionality mapping volume IDs to [Volume][acl_anthology.collections.volume.Volume] objects in the collection.

    Attributes: Required Attributes:
        id: The ID of this collection (e.g. "L06" or "2022.emnlp").
        parent: The parent CollectionIndex instance to which this collection belongs.
        path: The path of the XML file representing this collection.

    Attributes: Non-Init Attributes:
        is_data_loaded: A flag indicating whether the XML file has already been loaded.
    """

    id: str
    parent: CollectionIndex = field(repr=False, eq=False)
    path: Path
    is_data_loaded: bool = field(init=False, repr=False, default=False)

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

    def _add_volume_from_xml(self, meta: etree._Element) -> Volume:
        """Creates a new volume belonging to this collection.

        Parameters:
            meta: The `<meta>` element for the volume.

        Returns:
            The created volume.
        """
        volume = Volume.from_xml(self, meta)
        if volume.id in self.data:
            raise ValueError(f"Volume {volume.id} already exists in collection {self.id}")
        self.data[volume.id] = volume
        return volume

    def load(self) -> None:
        """Loads the XML file belonging to this collection."""
        log.debug(f"Parsing XML data file: {self.path}")
        current_volume = cast(Volume, None)  # noqa: F841
        for event, element in etree.iterparse(self.path, events=("start", "end")):
            match (event, element.tag):
                case ("end", "meta"):
                    # Seeing a volume's <meta> block instantiates a new volume
                    if element.getparent().tag == "event":
                        # Event metadata handled separately
                        continue
                    current_volume = self._add_volume_from_xml(element)  # noqa: F841
                    element.clear()
                case ("end", "frontmatter"):
                    current_volume._add_frontmatter_from_xml(element)
                case ("end", "paper"):
                    current_volume._add_paper_from_xml(element)
                case ("end", "event"):
                    # TODO: parse and attach event
                    pass

        self.is_data_loaded = True
