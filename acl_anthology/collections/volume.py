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
from typing import Any, Iterator, Optional, cast, TYPE_CHECKING

from .. import constants
from ..files import PDFReference
from ..people import NameSpecification
from ..text import MarkupText
from ..utils.ids import build_id, AnthologyID
from .paper import Paper

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

    Attributes: Required Attributes:
        id: The ID of this volume (e.g. "1" or "main").
        parent: The collection this volume belongs to.
        type: Value indicating the type of publication, e.g., journal or conference proceedings.
        title: The title of the volume. (Aliased to `booktitle` for initialization.)
        year: The year of publication.

    Attributes: List Attributes:
        editors: Names of editors associated with this volume.
        venues: List of venues associated with this volume.

    Attributes: Optional Attributes:
        address: The publisher's address for this volume.
        doi: The DOI for the volume.
        ingest_date: The date of ingestion.
        isbn: The ISBN for the volume.
        journal_issue: The journal's issue number, if this volume belongs to a journal.
        journal_volume: The journal's volume number, if this volume belongs to a journal.
        journal_title: The journal's title (without volume/issue/subtitle), if this volume belongs to a journal.
        month: The month of publication.
        pdf: A reference to the volume's PDF.
        publisher: The volume's publisher.
        shorttitle: A shortened form of the title. (Aliased to `shortbooktitle` for initialization.)

    Attributes: Non-Init Attributes:
        papers: A mapping of paper IDs in this volume to their Paper objects.
    """

    id: str
    parent: Collection = field(repr=False, eq=False)
    type: VolumeType
    title: MarkupText = field(alias="booktitle")
    year: str

    papers: dict[str, Paper] = field(init=False, repr=False, factory=dict)
    editors: list[NameSpecification] = Factory(list)
    venues: list[str] = field(factory=list)

    address: Optional[str] = field(default=None)
    doi: Optional[str] = field(default=None)
    ingest_date: Optional[str] = field(default=None)
    isbn: Optional[str] = field(default=None)
    journal_issue: Optional[str] = field(default=None)
    journal_volume: Optional[str] = field(default=None)
    journal_title: Optional[str] = field(default=None)
    month: Optional[str] = field(default=None)
    pdf: Optional[PDFReference] = field(default=None)
    publisher: Optional[str] = field(default=None)
    shorttitle: Optional[MarkupText] = field(default=None, alias="shortbooktitle")

    # def __repr__(self) -> str:
    #    return f"Volume({self._parent_id!r}, {self._id!r})"

    @property
    def frontmatter(self) -> Paper | None:
        """Returns the volume's frontmatter, if any."""
        return self.papers.get("0")

    @property
    def collection_id(self) -> str:
        """The collection ID this volume belongs to."""
        return self.parent.id

    @property
    def full_id(self) -> str:
        """The full anthology ID of this volume (e.g. "L06-1" or "2022.emnlp-main")."""
        return build_id(self.parent.id, self.id)

    @property
    def full_id_tuple(self) -> AnthologyID:
        """The full anthology ID of this volume, as a tuple (e.g. `("L06", "1", None)`)."""
        return (self.parent.id, self.id, None)

    @property
    def has_frontmatter(self) -> bool:
        """Returns True if this volume has frontmatter."""
        return "0" in self.papers

    def __iter__(self) -> Iterator[Paper]:
        """Returns an iterator over all associated papers."""
        return iter(self.papers.values())

    def get(self, paper_id: str) -> Paper | None:
        """Access a paper in this volume by its ID.

        Parameters:
            paper_id: A paper ID.

        Returns:
            The paper associated with the given ID, if it exists in this volume.
        """
        return self.papers.get(paper_id)

    def get_ingest_date(self) -> datetime.date:
        """
        Returns:
            The date when this volume was added to the Anthology. If not set, will return [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE] instead.
        """
        if self.ingest_date is None:
            return constants.UNKNOWN_INGEST_DATE
        return datetime.date.fromisoformat(self.ingest_date)

    def _add_frontmatter_from_xml(self, element: etree._Element) -> None:
        """Sets this volume's frontmatter.

        Parameters:
            element: The `<frontmatter>` element.
        """
        paper = Paper.from_frontmatter_xml(self, element)
        self.papers[paper.id] = paper

    def _add_paper_from_xml(self, element: etree._Element) -> None:
        """Creates a new paper belonging to this volume.

        Parameters:
            element: The `<paper>` element.
        """
        paper = Paper.from_xml(self, element)
        self.papers[paper.id] = paper

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
                kwargs["editors"].append(NameSpecification.from_xml(element))
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
