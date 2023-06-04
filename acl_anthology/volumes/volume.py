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

import lxml
from typing import Optional

from .. import constants
from ..utils.ids import build_id


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
    """A publication volume.

    Parameters:
        parent_id (str): The collection ID that this volume belongs to.
        volume_id (str): The volume ID.
        ingest_date (Optional[str]): The ingestion date of this volume.
    """

    def __init__(
        self, parent_id: str, volume_id: str, ingest_date: Optional[str] = None
    ) -> None:
        self._parent_id = parent_id
        self._id = volume_id
        self._ingest_date = ingest_date
        self._meta_attrib: dict[str, Optional[str]] = {}
        self._meta_venues: list[str] = []
        self._meta_url: Optional[str] = None
        self._meta_url_checksum: Optional[str] = None

    def __repr__(self) -> str:
        return f"Volume({self._parent_id!r}, {self._id!r})"

    @property
    def id(self) -> str:
        """The ID of this volume (e.g. "1" or "main")."""
        return self._id

    @property
    def parent_id(self) -> str:
        """The ID of the collection this volume belongs to (e.g. "L06" or "2022.emnlp")."""
        return self._parent_id

    @property
    def full_id(self) -> str:
        """The full anthology ID of this volume (e.g. "L06-1" or "2022.emnlp-main")."""
        return build_id(self._parent_id, self._id)

    @property
    def ingest_date(self) -> str:
        """The date of ingestion.  Returns
        [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE]
        if not set."""
        if self._ingest_date is None:
            return constants.UNKNOWN_INGEST_DATE
        return self._ingest_date

    @property
    def address(self) -> Optional[str]:
        """The publisher's address for this volume."""
        return self._meta_attrib.get("address")

    @address.setter
    def address(self, value: Optional[str]) -> None:
        self._meta_attrib["address"] = value

    @property
    def doi(self) -> Optional[str]:
        """The DOI for the volume."""
        return self._meta_attrib.get("doi")

    @doi.setter
    def doi(self, value: Optional[str]) -> None:
        # TODO: validate?
        self._meta_attrib["doi"] = value

    @property
    def isbn(self) -> Optional[str]:
        """The ISBN for the volume."""
        return self._meta_attrib.get("isbn", self._meta_attrib.get("ISBN"))

    @isbn.setter
    def isbn(self, value: Optional[str]) -> None:
        # TODO: validate?
        self._meta_attrib["isbn"] = value
        if "ISBN" in self._meta_attrib:
            del self._meta_attrib["ISBN"]

    @property
    def month(self) -> Optional[str]:
        """The month of publication."""
        return self._meta_attrib.get("month")

    @month.setter
    def month(self, value: Optional[str]) -> None:
        # TODO: validate?
        self._meta_attrib["month"] = value

    @property
    def publisher(self) -> Optional[str]:
        """The volume's publisher."""
        return self._meta_attrib.get("publisher")

    @publisher.setter
    def publisher(self, value: Optional[str]) -> None:
        self._meta_attrib["publisher"] = value

    @property
    def url(self) -> Optional[str]:
        """The URL for the volume's PDF.

        This can be an internal filename or an external URL.
        """
        return self._meta_url

    @property
    def url_checksum(self) -> Optional[str]:
        """The CRC32 checksum of the volume's PDF.

        Only set if [`self.url`][acl_anthology.volumes.volume.Volume.url] is an internal filename.
        """
        return self._meta_url_checksum

    @property
    def venues(self) -> list[str]:
        """List of venues associated with this volume."""
        return self._meta_venues

    @property
    def volume_number(self) -> Optional[str]:
        """The volume's issue number, if it belongs to a journal."""
        return self._meta_attrib.get("volume")

    @volume_number.setter
    def volume_number(self, value: Optional[str]) -> None:
        self._meta_attrib["volume"] = value

    @property
    def year(self) -> Optional[str]:
        """The year of publication."""
        return self._meta_attrib.get("year")

    @year.setter
    def year(self, value: str) -> None:
        # TODO: validate
        self._meta_attrib["year"] = value

    def parse_xml_meta(self, meta: lxml.etree._Element) -> None:
        for element in meta:
            if element.tag in VOLUME_META_TEXT_ELEMENTS:
                self._meta_attrib[element.tag] = element.text
            elif element.tag == "venue":
                self._meta_venues.append(str(element.text))
            elif element.tag == "url":
                self._meta_url = str(element.text)
                self._meta_url_checksum = str(element.attrib.get("hash"))
            elif element.tag in ("booktitle", "shortbooktitle"):
                pass  # TODO: Parse MarkupText
            elif element.tag == "editor":
                pass  # TODO: Parse Person
