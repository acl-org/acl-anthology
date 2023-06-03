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
from ..utils import build_anthology_id, deconstruct_anthology_id
from .. import constants


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
            (collection_id, volume_id) = full_id
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


VOLUME_META_TEXT_ELEMENTS = (
    "publisher",
    "address",
    "month",
    "year",
    "volume",
    "isbn",
    "ISBN",
    "doi",
)


class Volume:
    def __init__(self, parent_id, volume_id, ingest_date=None):
        self._parent_id = parent_id
        self._id = volume_id
        self._ingest_date = ingest_date
        self._meta_attrib = {}
        self._meta_venues = []
        self._meta_url = None
        self._meta_url_checksum = None

    def __str__(self):
        return f"Volume '{build_anthology_id(self._parent_id, self._id)}'"

    @property
    def id(self):
        return self._id

    @property
    def ingest_date(self):
        if self._ingest_date is None:
            return constants.UNKNOWN_INGEST_DATE
        return self._ingest_date

    @property
    def address(self):
        return self._meta_attrib.get("address")

    @address.setter
    def address(self, value):
        self._meta_attrib["address"] = value

    @property
    def doi(self):
        return self._meta_attrib.get("doi")

    @doi.setter
    def doi(self, value):
        # TODO: validate?
        self._meta_attrib["doi"] = value

    @property
    def isbn(self):
        return self._meta_attrib.get("isbn", self._meta_attrib.get("ISBN"))

    @isbn.setter
    def isbn(self, value):
        # TODO: validate?
        self._meta_attrib["isbn"] = value
        if "ISBN" in self._meta_attrib:
            del self._meta_attrib["ISBN"]

    @property
    def month(self):
        return self._meta_attrib.get("month")

    @month.setter
    def month(self, value):
        # TODO: validate?
        self._meta_attrib["month"] = value

    @property
    def publisher(self):
        return self._meta_attrib.get("publisher")

    @publisher.setter
    def publisher(self, value):
        self._meta_attrib["publisher"] = value

    @property
    def url(self):
        return self._meta_url

    @property
    def url_checksum(self):
        return self._meta_url_checksum

    @property
    def venues(self):
        return self._meta_venues

    @property
    def volume_number(self):
        return self._meta_attrib.get("volume")

    @volume_number.setter
    def volume_number(self, value):
        self._meta_attrib["volume"] = str(int(value))

    @property
    def year(self):
        return self._meta_attrib.get("year")

    @year.setter
    def year(self, value):
        # TODO: validate
        self._meta_attrib["year"] = value

    def parse_xml_meta(self, meta):
        for element in meta:
            if element.tag in VOLUME_META_TEXT_ELEMENTS:
                self._meta_attrib[element.tag] = element.text
            elif element.tag == "venue":
                self._meta_venues.append(element.text)
            elif element.tag == "url":
                self._meta_url = element.text
                self._meta_url_checksum = element.attrib.get("hash")
            elif element.tag in ("booktitle", "shortbooktitle"):
                pass  # TODO: Parse MarkupText
            elif element.tag == "editor":
                pass  # TODO: Parse Person
