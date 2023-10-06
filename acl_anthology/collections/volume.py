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
from lxml.builder import E
from typing import Any, Iterator, Optional, cast, TYPE_CHECKING
import sys

from .. import constants
from ..containers import SlottedDict
from ..files import PDFReference
from ..people import NameSpecification
from ..text import MarkupText
from ..venues import Venue
from ..utils.ids import build_id, AnthologyIDTuple
from .paper import Paper

if TYPE_CHECKING:
    from ..anthology import Anthology
    from . import Collection


class VolumeType(Enum):
    """Type of publication a volume represents."""

    JOURNAL = "journal"
    """A journal issue."""

    PROCEEDINGS = "proceedings"
    """A conference/workshop proceedings volume."""


@define
class Volume(SlottedDict[Paper]):
    """A publication volume.

    Provides dictionary-like functionality mapping paper IDs to [Paper][acl_anthology.collections.paper.Paper] objects in the volume.

    Attributes: Required Attributes:
        id: The ID of this volume (e.g. "1" or "main").
        parent: The collection this volume belongs to.
        type: Value indicating the type of publication, e.g., journal or conference proceedings.
        title: The title of the volume. (Aliased to `booktitle` for initialization.)
        year: The year of publication.

    Attributes: List Attributes:
        editors: Names of editors associated with this volume.
        venue_ids: List of venue IDs associated with this volume. See also [venues][acl_anthology.collections.volume.Volume.venues].

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
    """

    id: str
    parent: Collection = field(repr=False, eq=False)
    type: VolumeType
    title: MarkupText = field(alias="booktitle")
    year: str

    editors: list[NameSpecification] = Factory(list)
    venue_ids: list[str] = field(factory=list)

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
        return self.data.get("0")

    @property
    def collection_id(self) -> str:
        """The collection ID this volume belongs to."""
        return self.parent.id

    @property
    def full_id(self) -> str:
        """The full anthology ID of this volume (e.g. "L06-1" or "2022.emnlp-main")."""
        return build_id(self.parent.id, self.id)

    @property
    def full_id_tuple(self) -> AnthologyIDTuple:
        """The full anthology ID of this volume, as a tuple (e.g. `("L06", "1", None)`)."""
        return (self.parent.id, self.id, None)

    @property
    def has_frontmatter(self) -> bool:
        """True if this volume has frontmatter."""
        return "0" in self.data

    @property
    def is_workshop(self) -> bool:
        """True if this volume is a workshop proceedings."""
        # Venue "ws" is inconsistently marked, so we also look at the title
        return "ws" in self.venue_ids or "workshop" in str(self.title).lower()

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.parent.parent.parent

    def get_ingest_date(self) -> datetime.date:
        """
        Returns:
            The date when this volume was added to the Anthology. If not set, will return [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE] instead.
        """
        if self.ingest_date is None:
            return constants.UNKNOWN_INGEST_DATE
        return datetime.date.fromisoformat(self.ingest_date)

    def papers(self) -> Iterator[Paper]:
        """An iterator over all Paper objects in this volume."""
        yield from self.data.values()

    def venues(self) -> list[Venue]:
        """A list of venues associated with this volume."""
        try:
            return [self.root.venues[vid] for vid in self.venue_ids]
        except KeyError as exc:
            if sys.version_info >= (3, 11):
                exc.add_note(
                    f"Most likely, venue ID '{exc.args[0]}' is not defined in yaml/venues/*.yaml"
                )
            raise exc

    def _add_paper_from_xml(self, element: etree._Element) -> None:
        """Creates a new paper belonging to this volume.

        Parameters:
            element: The `<paper>` element.
        """
        paper = Paper.from_xml(self, element)
        self.data[paper.id] = paper

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
            "venue_ids": [],
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
                kwargs["pdf"] = PDFReference.from_xml(element)
            elif element.tag == "venue":
                kwargs["venue_ids"].append(str(element.text))
            else:
                raise ValueError(f"Unsupported element for Volume: <{element.tag}>")
        return cls(**kwargs)

    def to_xml(self, with_papers: bool = True) -> etree._Element:
        """Serialize this volume in the Anthology XML format.

        Arguments:
            with_papers: If False, the returned `<volume>` will only contain the volume's `<meta>` block, but no contained papers.  Defaults to True.

        Returns:
            A serialization of this volume as a `<volume>` block in the Anthology XML format.
        """
        volume = E.volume(id=self.id, type=self.type.value)
        if self.ingest_date is not None:
            volume.attrib["ingest-date"] = self.ingest_date
        meta = E.meta()
        meta.append(self.title.to_xml("booktitle"))
        if self.shorttitle is not None:
            meta.append(self.shorttitle.to_xml("shortbooktitle"))
        for name_spec in self.editors:
            meta.append(name_spec.to_xml("editor"))
        for tag in (
            "publisher",
            "address",
            "doi",
            "isbn",
            "month",
            "year",
        ):
            if (value := getattr(self, tag)) is not None:
                meta.append(getattr(E, tag)(value))
        if self.pdf is not None:
            meta.append(self.pdf.to_xml("url"))
        for venue in self.venue_ids:
            meta.append(E.venue(venue))
        for tag in (
            "journal_volume",
            "journal_issue",
            "journal_title",
        ):
            if (value := getattr(self, tag)) is not None:
                meta.append(getattr(E, tag.replace("_", "-"))(value))
        volume.append(meta)

        if with_papers:
            for paper in self.values():
                volume.append(paper.to_xml())

        return volume