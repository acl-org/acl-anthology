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

from lxml import etree
from pathlib import Path
from typing import Optional, cast

from ..logging import log
from .volume import Volume


class Collection:
    """A class representing a collection.

    Collections correspond to XML files in the `data/xml/` directory of
    the Anthology repo.  They can hold volumes and events.
    """

    def __init__(self, collection_id: str, xml_path: Path) -> None:
        self._id = collection_id
        self._path = xml_path
        self._loaded = False
        self.volumes: dict[str, Volume] = {}

    @property
    def id(self) -> str:
        """The collection ID."""
        return self._id

    @property
    def path(self) -> Path:
        """The path to the XML file belonging to this collection."""
        return self._path

    @property
    def is_data_loaded(self) -> bool:
        """Returns True if the associated XML file has already been loaded."""
        return self._loaded

    def get(self, volume_id: str) -> Optional[Volume]:
        """Get an associated volume.

        Parameters:
            volume_id: The volume ID (e.g. "1").
        """
        return self.volumes.get(volume_id)

    def new_volume(self, volume_id: str) -> Volume:
        """Creates a new volume belonging to this collection.

        Parameters:
            volume_id: The volume ID.

        Returns:
            The created volume.
        """
        if volume_id in self.volumes:
            raise ValueError(f"Volume {volume_id} already exists in collection {self.id}")
        volume = Volume(self.id, volume_id)
        self.volumes[volume_id] = volume
        return volume

    def load(self) -> None:
        """Loads the XML file belonging to this collection."""
        log.debug(f"Parsing XML data file: {self._path}")
        current_volume = cast(Volume, None)
        for event, element in etree.iterparse(self._path, events=("start", "end")):
            match (event, element.tag):
                case ("start", "volume"):
                    # Initialize a new volume
                    current_volume = self.new_volume(element.attrib["id"])
                    current_volume.ingest_date = element.attrib.get("ingest-date")
                case ("end", "meta"):
                    # Set volume metadata (event metadata is handled elsewhere)
                    if element.getparent().tag == "event":
                        continue
                    current_volume.parse_xml_meta(element)
                    element.clear()

        # TODO: incomplete
        self._loaded = True
