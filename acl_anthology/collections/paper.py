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

import attrs
import datetime
from attrs import define, field, Factory
from enum import Enum
from lxml import etree
from lxml.builder import E
from typing import cast, Any, Optional, TYPE_CHECKING

from ..files import (
    AttachmentReference,
    PapersWithCodeReference,
    PDFReference,
    VideoReference,
)
from ..people import NameSpecification
from ..text import MarkupText
from ..utils.ids import build_id, AnthologyIDTuple
from ..utils.logging import get_logger

if TYPE_CHECKING:
    from ..anthology import Anthology
    from . import Volume

log = get_logger()


@define
class Paper:
    """A paper entry.

    Attributes: Required Attributes:
        id: The ID of this paper (e.g. "1" or "42").
        parent: The Volume object that this paper belongs to.
        bibkey: Bibliography key, e.g. for BibTeX.  Must be unique across all papers in the Anthology.
        title: The title of the paper.

    Attributes: List Attributes:
        attachments: File attachments of this paper. The dictionary key specifies the type of attachment (e.g., "software").
        authors: Names of authors associated with this paper; can be empty.
        awards: Names of awards this has paper has received; can be empty.
        editors: Names of editors associated with this paper; can be empty.
        errata: Errata for this paper; can be empty.
        revisions: Revisions for this paper; can be empty.
        videos: Zero or more references to video recordings belonging to this paper.

    Attributes: Optional Attributes:
        abstract: The full abstract.
        deletion: A notice of the paper's retraction or removal, if applicable.
        doi: The DOI for the paper.
        ingest_date: The date of ingestion.
        language: The language this paper is (mainly) written in.  When given, this should be a ISO 639-2 code (e.g. "eng"), though occasionally IETF is used (e.g. "pt-BR").
        note: A note attached to this paper.  Used very sparingly.
        pages: Page numbers of this paper within its volume.
        paperswithcode: Links to code implementations and datasets as provided by [Papers with Code](https://paperswithcode.com/).
        pdf: A reference to the paper's PDF.
    """

    id: str
    parent: Volume = field(repr=False, eq=False)
    bibkey: str
    title: MarkupText = field()

    attachments: dict[str, AttachmentReference] = Factory(dict)
    authors: list[NameSpecification] = Factory(list)
    awards: list[str] = Factory(list)
    # TODO: why can a Paper ever have "editors"? it's allowed by the schema
    editors: list[NameSpecification] = Factory(list)
    errata: list[PaperErratum] = Factory(list)
    revisions: list[PaperRevision] = Factory(list)
    videos: list[VideoReference] = Factory(list)

    abstract: Optional[MarkupText] = field(default=None)
    deletion: Optional[PaperDeletionNotice] = field(default=None)
    doi: Optional[str] = field(default=None)
    ingest_date: Optional[str] = field(default=None)
    language: Optional[str] = field(default=None)
    note: Optional[str] = field(default=None)
    pages: Optional[str] = field(default=None)
    paperswithcode: Optional[PapersWithCodeReference] = field(
        default=None, on_setattr=attrs.setters.frozen
    )
    pdf: Optional[PDFReference] = field(default=None)

    # TODO: properties we obtain from the parent volume?

    @property
    def collection_id(self) -> str:
        """The collection ID this paper belongs to."""
        return self.parent.collection_id

    @property
    def volume_id(self) -> str:
        """The volume ID this paper belongs to."""
        return self.parent.id

    @property
    def full_id(self) -> str:
        """The full anthology ID of this paper (e.g. "L06-1042" or "2022.emnlp-main.1")."""
        return build_id(self.parent.parent.id, self.parent.id, self.id)

    @property
    def full_id_tuple(self) -> AnthologyIDTuple:
        """The full anthology ID of this paper, as a tuple (e.g. `("L06", "1", "42")`)."""
        return (self.parent.parent.id, self.parent.id, self.id)

    @property
    def is_deleted(self) -> bool:
        """Returns True if this paper was retracted or removed from the Anthology."""
        return self.deletion is not None

    @property
    def is_frontmatter(self) -> bool:
        """Returns True if this paper represents a volume's frontmatter."""
        return self.id == "0"

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.parent.parent.parent.parent

    def get_ingest_date(self) -> datetime.date:
        """
        Returns:
            The date when this paper was added to the Anthology. Inherits from its parent volume. If not set, will return [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE] instead.
        """
        if self.ingest_date is None:
            return self.parent.get_ingest_date()
        return datetime.date.fromisoformat(self.ingest_date)

    @classmethod
    def from_frontmatter_xml(cls, parent: Volume, paper: etree._Element) -> Paper:
        """Instantiates a new paper from a `<frontmatter>` block in the XML."""
        kwargs: dict[str, Any] = {
            "id": "0",
            "parent": parent,
            # A frontmatter's title is the parent volume's title
            "title": parent.title,
            # A volume's editors are authors for the frontmatter
            "authors": parent.editors,
            "attachments": {},
        }
        # Frontmatter only supports a small subset of regular paper attributes,
        # so we duplicate these here -- but maybe suboptimal?
        for element in paper:
            if element.tag in ("bibkey", "doi", "pages"):
                kwargs[element.tag] = element.text
            elif element.tag == "attachment":
                type_ = str(element.attrib.get("type", "attachment"))
                kwargs["attachments"][type_] = AttachmentReference.from_xml(element)
            elif element.tag == "revision":
                if "revisions" not in kwargs:
                    kwargs["revisions"] = []
                kwargs["revisions"].append(PaperRevision.from_xml(element))
            elif element.tag == "url":
                kwargs["pdf"] = PDFReference.from_xml(element)
            else:
                raise ValueError(f"Unsupported element for Frontmatter: <{element.tag}>")
        return cls(**kwargs)

    @classmethod
    def from_xml(cls, parent: Volume, paper: etree._Element) -> Paper:
        """Instantiates a new paper from its `<paper>` block in the XML.

        This function can also be called with a `<frontmatter>` block, in which case it will just defer to [self.from_frontmatter_xml][acl_anthology.collections.paper.Paper.from_frontmatter_xml].
        """
        if paper.tag == "frontmatter":
            return Paper.from_frontmatter_xml(parent, paper)
        # Remainder of this function assumes paper.tag == "paper"
        kwargs: dict[str, Any] = {
            "id": str(paper.attrib["id"]),
            "parent": parent,
            "authors": [],
            "editors": [],
            "attachments": {},
        }
        if (ingest_date := paper.attrib.get("ingest-date")) is not None:
            kwargs["ingest_date"] = str(ingest_date)
        if paper.attrib.get("type") is not None:
            # TODO: this is currently ignored
            log.debug(
                f"Paper {paper.attrib['id']!r}: Type attribute is currently ignored"
            )
            # kwargs["type"] = str(paper_type)
        for element in paper:
            if element.tag in ("bibkey", "doi", "language", "note", "pages"):
                kwargs[element.tag] = element.text
            elif element.tag in ("author", "editor"):
                kwargs[f"{element.tag}s"].append(NameSpecification.from_xml(element))
            elif element.tag in ("abstract", "title"):
                kwargs[element.tag] = MarkupText.from_xml(element)
            elif element.tag == "attachment":
                type_ = str(element.attrib.get("type", "attachment"))
                kwargs["attachments"][type_] = AttachmentReference.from_xml(element)
            elif element.tag == "award":
                if "awards" not in kwargs:
                    kwargs["awards"] = []
                kwargs["awards"].append(element.text)
            elif element.tag == "erratum":
                if "errata" not in kwargs:
                    kwargs["errata"] = []
                kwargs["errata"].append(PaperErratum.from_xml(element))
            elif element.tag in ("pwccode", "pwcdataset"):
                if "paperswithcode" not in kwargs:
                    kwargs["paperswithcode"] = PapersWithCodeReference()
                kwargs["paperswithcode"].append_from_xml(element)
            elif element.tag in ("removed", "retracted"):
                kwargs["deletion"] = PaperDeletionNotice.from_xml(element)
            elif element.tag == "revision":
                if "revisions" not in kwargs:
                    kwargs["revisions"] = []
                kwargs["revisions"].append(PaperRevision.from_xml(element))
            elif element.tag == "url":
                kwargs["pdf"] = PDFReference.from_xml(element)
            elif element.tag == "video":
                if "videos" not in kwargs:
                    kwargs["videos"] = []
                kwargs["videos"].append(VideoReference.from_xml(element))
            elif element.tag in ("issue", "journal", "mrf"):
                # TODO: these fields are currently ignored
                log.debug(
                    f"Paper {paper.attrib['id']!r}: Tag '{element.tag}' is currently ignored"
                )
            else:
                raise ValueError(f"Unsupported element for Paper: <{element.tag}>")
        return cls(**kwargs)

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this paper as a `<paper>` or `<frontmatter>` block in the Anthology XML format.
        """
        if self.is_frontmatter:
            paper = etree.Element("frontmatter")
        else:
            paper = etree.Element("paper", attrib={"id": self.id})
        if self.ingest_date is not None:
            paper.attrib["ingest-date"] = self.ingest_date
        if not self.is_frontmatter:
            paper.append(self.title.to_xml("title"))
            for name_spec in self.authors:
                paper.append(name_spec.to_xml("author"))
            for name_spec in self.editors:
                paper.append(name_spec.to_xml("editor"))
        if self.pages is not None:
            paper.append(E.pages(self.pages))
        if self.abstract is not None:
            paper.append(self.abstract.to_xml("abstract"))
        if self.pdf is not None:
            paper.append(self.pdf.to_xml("url"))
        for erratum in self.errata:
            paper.append(erratum.to_xml())
        for revision in self.revisions:
            paper.append(revision.to_xml())
        for tag in ("doi", "language", "note"):
            if (value := getattr(self, tag)) is not None:
                paper.append(getattr(E, tag)(value))
        for type_, attachment in self.attachments.items():
            elem = attachment.to_xml("attachment")
            elem.attrib["type"] = type_
            paper.append(elem)
        for video in self.videos:
            paper.append(video.to_xml("video"))
        for award in self.awards:
            paper.append(E.award(award))
        if self.deletion is not None:
            paper.append(self.deletion.to_xml())
        paper.append(E.bibkey(self.bibkey))
        if self.paperswithcode is not None:
            paper.extend(self.paperswithcode.to_xml_list())
        return paper


class PaperDeletionType(Enum):
    """Type of deletion of a paper."""

    RETRACTED = "retracted"
    """Paper was retracted.  A retraction occurs when serious, unrecoverable errors are discovered, which drastically affect the findings of the original work."""

    REMOVED = "removed"
    """Paper was removed.  A removal occurs in rare circumstances where serious ethical or legal issues arise, such as plagiarism."""


@define
class PaperDeletionNotice:
    """A notice about a paper's deletion (i.e., retraction or removal) from the Anthology."""

    type: PaperDeletionType
    """Type indicating whether the paper was _retracted_ or _removed_."""

    note: str
    """A note explaining the retraction or removal."""

    date: str
    """The date on which the paper was retracted or removed."""

    @classmethod
    def from_xml(cls, element: etree._Element) -> PaperDeletionNotice:
        """Instantiates a deletion notice from its `<removed>` or `<retracted>` block in the XML."""
        return cls(
            type=PaperDeletionType(str(element.tag)),
            note=str(element.text),
            date=str(element.attrib["date"]),
        )

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this deletion notice in Anthology XML format.
        """
        return cast(
            etree._Element, getattr(E, self.type.value)(self.note, date=self.date)
        )


@define
class PaperErratum:
    """An erratum for a paper."""

    id: str
    """An ID for this erratum."""

    pdf: PDFReference
    """A reference to the erratum's PDF."""
    # Note: must be a local filename according to the schema

    date: Optional[str] = field(default=None)
    """The date where this erratum was added."""

    @classmethod
    def from_xml(cls, element: etree._Element) -> PaperErratum:
        """Instantiates an erratum from its `<erratum>` block in the XML."""
        return cls(
            id=str(element.attrib["id"]),
            pdf=PDFReference.from_xml(element),
            date=(str(element.attrib["date"]) if "date" in element.attrib else None),
        )

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this erratum in Anthology XML format.
        """
        elem = E.erratum(self.pdf.name, id=self.id, hash=str(self.pdf.checksum))
        if self.date is not None:
            elem.attrib["date"] = self.date
        return elem


@define
class PaperRevision:
    """A revised version of a paper."""

    id: str
    """An ID for this revision."""

    note: Optional[str]
    """A note explaining the reason for the revision."""

    pdf: PDFReference
    """A reference to the revision's PDF."""
    # Note: must be a local filename according to the schema

    date: Optional[str] = field(default=None)
    """The date where this revision was added."""

    @classmethod
    def from_xml(cls, element: etree._Element) -> PaperRevision:
        """Instantiates a revision from its `<revision>` block in the XML."""
        return cls(
            id=str(element.attrib["id"]),
            note=str(element.text) if element.text else None,
            pdf=PDFReference(str(element.attrib["href"]), str(element.attrib["hash"])),
            date=(str(element.attrib["date"]) if "date" in element.attrib else None),
        )

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this revision in Anthology XML format.
        """
        elem = E.revision(
            id=self.id,
            href=self.pdf.name,
            hash=str(self.pdf.checksum),
        )
        if self.note:
            elem.text = str(self.note)
        if self.date is not None:
            elem.attrib["date"] = self.date
        return elem