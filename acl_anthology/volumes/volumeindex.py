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

from ..logging import log
from ..utils import deconstruct_anthology_id
from .volume import Volume


class VolumeIndex:
    def __init__(self, anthology):
        self._anthology = anthology
        self.collections = {}

        self._find_collections()

    def get(self, full_id):
        if isinstance(full_id, (tuple, list)):
            (collection_id, volume_id, paper_id) = full_id
        else:
            (collection_id, volume_id, paper_id) = deconstruct_anthology_id(full_id)

        volume = self.get_volume((collection_id, volume_id))
        if paper_id is not None:
            pass  # TODO: fetch and return individual paper
        return volume

    def get_volume(self, full_id):
        if isinstance(full_id, (tuple, list)):
            (collection_id, volume_id, *_) = full_id
        else:
            (collection_id, volume_id, _) = deconstruct_anthology_id(full_id)

        collection = self.collections[collection_id]
        # Load XML file, if necessary
        if not collection["volumes"]:
            self._parse_xml(collection)
        return collection["volumes"].get(volume_id)

    def _find_collections(self):
        """Finds all XML data files and indexes them by their collection ID."""
        for xmlpath in Path(self._anthology.datadir).glob("xml/*.xml"):
            collection_id = xmlpath.name[:-4]
            self.collections[collection_id] = {
                "id": collection_id,
                "path": xmlpath,
                "volumes": {},
            }

    def _parse_xml(self, collection):
        filename = collection["path"]
        log.debug(f"Parsing XML data file: {filename}")
        current_volume = None
        for event, element in etree.iterparse(filename, events=("start", "end")):
            match (event, element.tag):
                case ("start", "volume"):
                    # Initialize a new volume
                    current_volume = Volume(
                        collection["id"],
                        element.attrib["id"],
                        ingest_date=element.attrib.get(
                            "ingest-date"
                        ),  # optional attribute
                    )
                    collection["volumes"][element.attrib["id"]] = current_volume
                case ("end", "meta"):
                    # Set volume metadata (event metadata is handled elsewhere)
                    if element.getparent().tag == "event":
                        continue
                    current_volume.parse_xml_meta(element)
                    element.clear()

        # TODO:
