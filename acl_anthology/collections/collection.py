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

from attrs import define, field
from lxml import etree
from pathlib import Path
from typing import Optional, cast

from ..logging import log
from .volume import Volume


@define
class Collection:
    """A collection of volumes and events.

    A collection corresponds to an XML file in the `data/xml/` directory
    of the Anthology repo.

    Attributes:
        id (str): The ID of this collection (e.g. "L06" or "2022.emnlp").
        path (Path): The path of the XML file representing this collection.

        is_data_loaded (bool): Whether the associated XML file has already
                               been loaded.
    """

    id: str
    path: Path
    is_data_loaded: bool = field(init=False, default=False)
    volumes: dict[str, Volume] = field(init=False, factory=dict)

    def get(self, volume_id: str) -> Optional[Volume]:
        """Get an associated volume.

        Parameters:
            volume_id: The volume ID (e.g. "1").
        """
        return self.volumes.get(volume_id)

    def new_volume_from_xml(self, meta: etree._Element) -> Volume:
        """Creates a new volume belonging to this collection.

        Parameters:
            meta: The <meta> element for the volume.

        Returns:
            The created volume.
        """
        volume = Volume.from_xml(self.id, meta)
        if volume.id in self.volumes:
            raise ValueError(f"Volume {volume.id} already exists in collection {self.id}")
        self.volumes[volume.id] = volume
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
                    current_volume = self.new_volume_from_xml(element)  # noqa: F841
                    element.clear()
                case ("end", "frontmatter"):
                    # TODO: parse frontmatter
                    pass
                case ("end", "paper"):
                    # TODO: parse and attach paper
                    pass
                case ("end", "event"):
                    # TODO: parse and attach event
                    pass

        self.is_data_loaded = True