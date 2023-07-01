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

import lxml
from attr import define, field, Factory
from typing import Any, Optional, cast

from .. import constants
from ..people import Name
from ..text import MarkupText
from ..utils.ids import build_id


@define
class Volume:
    """A publication volume.

    Attributes:
        id (str): The ID of this volume (e.g. "1" or "main").
        parent_id (str): The ID of the collection this volume belongs to (e.g. "L06" or "2022.emnlp").
        title (MarkupText): The title of the volume. (Aliased to `booktitle` for initialization.)
        year (str): The year of publication.

        address (Optional[str]): The publisher's address for this volume.
        doi (Optional[str]): The DOI for the volume.
        editors (list[Name]): Names of editors associated with this volume.
        ingest_date (str): The date of ingestion; defaults to [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE].
        isbn (Optional[str]): The ISBN for the volume.
        month (Optional[str]): The month of publication.
        number (Optional[str]): The volume's issue number, if it belongs to a journal.
        publisher (Optional[str]): The volume's publisher.
        shorttitle (Optional[MarkupText]): A shortened form of the title. (Aliased to `shortbooktitle` for initialization.)
        url (Optional[str]): The URL for the volume's PDF. This can be an internal filename or an external URL.
        url_checksum (Optional[str]): The CRC32 checksum of the volume's PDF. Only set if `self.url` is an internal filename.
        venues (list[str]): List of venues associated with this volume.
    """

    id: str
    parent_id: str
    title: MarkupText = field(alias="booktitle")
    year: str

    address: Optional[str] = field(default=None)
    doi: Optional[str] = field(default=None)
    editors: list[Name] = Factory(list)
    ingest_date: str = field(default=constants.UNKNOWN_INGEST_DATE)
    isbn: Optional[str] = field(default=None)
    month: Optional[str] = field(default=None)
    number: Optional[str] = field(default=None)
    publisher: Optional[str] = field(default=None)
    shorttitle: Optional[MarkupText] = field(default=None, alias="shortbooktitle")
    url: Optional[str] = field(default=None)
    url_checksum: Optional[str] = field(default=None)
    venues: list[str] = field(factory=list)

    # def __repr__(self) -> str:
    #    return f"Volume({self._parent_id!r}, {self._id!r})"

    @property
    def full_id(self) -> str:
        """The full anthology ID of this volume (e.g. "L06-1" or "2022.emnlp-main")."""
        return build_id(self.parent_id, self.id)

    @classmethod
    def from_xml(cls, parent_id: str, meta: lxml.etree._Element) -> Volume:
        """Instantiates a new volume from its <meta> block in the XML."""
        volume = cast(lxml.etree._Element, meta.getparent())
        # type-checking kwargs is a headache
        kwargs: dict[str, Any] = {
            "id": str(volume.attrib["id"]),
            "parent_id": parent_id,
            "editors": [],
            "venues": [],
        }
        if (ingest_date := volume.attrib.get("ingest-date")) is not None:
            kwargs["ingest_date"] = str(ingest_date)
        for element in meta:
            if element.tag in (
                "address",
                "doi",
                "isbn",
                "month",
                "publisher",
                "year",
            ):
                kwargs[element.tag] = element.text
            elif element.tag in ("booktitle", "shortbooktitle"):
                kwargs[element.tag] = MarkupText.from_xml(element)
            elif element.tag == "editor":
                kwargs["editors"].append(Name.from_xml(element))
            elif element.tag == "url":
                kwargs["url"] = element.text
                kwargs["url_checksum"] = element.attrib.get("hash")
            elif element.tag == "venue":
                kwargs["venues"].append(str(element.text))
            elif element.tag == "volume":
                kwargs["number"] = element.text
            else:
                raise ValueError(f"Unsupported element for Volume: <{element.tag}>")
        return cls(**kwargs)
