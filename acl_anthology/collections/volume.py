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

import datetime
from attrs import define, field, Factory
from enum import Enum
from lxml import etree
from typing import Any, Optional, cast, TYPE_CHECKING

from .. import constants
from ..files import PDFReference
from ..people import Name
from ..text import MarkupText
from ..utils.ids import build_id

if TYPE_CHECKING:
    from . import Collection


class VolumeType(Enum):
    """Type of publication a volume represents."""

    JOURNAL = "journal"
    """A journal issue."""

    PROCEEDINGS = "proceedings"
    """A conference/workshop proceedings volume."""


@define
class Volume:
    """A publication volume.

    Attributes:
        id (str): The ID of this volume (e.g. "1" or "main").
        parent (Collection): The collection this volume belongs to.
        type (VolumeType): Value indicating the type of publication, e.g., journal or conference proceedings.
        title (MarkupText): The title of the volume. (Aliased to `booktitle` for initialization.)
        year (str): The year of publication.

        address (Optional[str]): The publisher's address for this volume.
        doi (Optional[str]): The DOI for the volume.
        editors (list[Name]): Names of editors associated with this volume.
        ingest_date (str): The date of ingestion; defaults to [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE].
        isbn (Optional[str]): The ISBN for the volume.
        journal_issue (Optional[str]): The journal's issue number, if this volume belongs to a journal.
        journal_volume (Optional[str]): The journal's volume number, if this volume belongs to a journal.
        journal_title (Optional[str]): The journal's title (without volume/issue/subtitle), if this volume belongs to a journal.
        month (Optional[str]): The month of publication.
        pdf (Optional[PDFReference]): A reference to the volume's PDF.
        publisher (Optional[str]): The volume's publisher.
        shorttitle (Optional[MarkupText]): A shortened form of the title. (Aliased to `shortbooktitle` for initialization.)
        venues (list[str]): List of venues associated with this volume.
    """

    id: str
    parent: Collection = field(repr=False, eq=False)
    type: VolumeType
    title: MarkupText = field(alias="booktitle")
    year: str

    address: Optional[str] = field(default=None)
    doi: Optional[str] = field(default=None)
    editors: list[Name] = Factory(list)
    ingest_date: str = field(default=constants.UNKNOWN_INGEST_DATE)
    isbn: Optional[str] = field(default=None)
    journal_issue: Optional[str] = field(default=None)
    journal_volume: Optional[str] = field(default=None)
    journal_title: Optional[str] = field(default=None)
    month: Optional[str] = field(default=None)
    pdf: Optional[PDFReference] = field(default=None)
    publisher: Optional[str] = field(default=None)
    shorttitle: Optional[MarkupText] = field(default=None, alias="shortbooktitle")
    venues: list[str] = field(factory=list)

    # def __repr__(self) -> str:
    #    return f"Volume({self._parent_id!r}, {self._id!r})"

    @property
    def full_id(self) -> str:
        """The full anthology ID of this volume (e.g. "L06-1" or "2022.emnlp-main")."""
        return build_id(self.parent.id, self.id)

    def get_ingest_date(self) -> datetime.date:
        """The date when this volume was added to the Anthology, if defined."""
        return datetime.date.fromisoformat(self.ingest_date)

    @classmethod
    def from_xml(cls, parent: Collection, meta: etree._Element) -> Volume:
        """Instantiates a new volume from its `<meta>` block in the XML."""
        volume = cast(etree._Element, meta.getparent())
        # type-checking kwargs is a headache
        kwargs: dict[str, Any] = {
            "id": str(volume.attrib["id"]),
            "type": VolumeType(volume.attrib["type"]),
            "parent": parent,
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
            elif element.tag in (
                "journal-issue",
                "journal-volume",
                "journal-title",
            ):
                kwargs[element.tag.replace("-", "_")] = element.text
            elif element.tag in ("booktitle", "shortbooktitle"):
                kwargs[element.tag] = MarkupText.from_xml(element)
            elif element.tag == "editor":
                kwargs["editors"].append(Name.from_xml(element))
            elif element.tag == "url":
                checksum = element.attrib.get("hash")
                kwargs["pdf"] = PDFReference(
                    str(element.text), str(checksum) if checksum else None
                )
            elif element.tag == "venue":
                kwargs["venues"].append(str(element.text))
            else:
                raise ValueError(f"Unsupported element for Volume: <{element.tag}>")
        return cls(**kwargs)