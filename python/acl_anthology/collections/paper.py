# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
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

from ..config import config
from ..files import (
    AttachmentReference,
    PapersWithCodeReference,
    PDFReference,
    VideoReference,
)
from ..people import NameSpecification
from ..text import MarkupText
from ..utils.ids import build_id, AnthologyIDTuple
from ..utils.latex import make_bibtex_entry
from ..utils.logging import get_logger
from .types import VolumeType

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..utils.latex import SerializableAsBibTeX
    from . import Event, Volume

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
    bibkey: str = field()
    title: MarkupText = field()

    attachments: dict[str, AttachmentReference] = field(factory=dict, repr=False)
    authors: list[NameSpecification] = Factory(list)
    awards: list[str] = field(factory=list, repr=False)
    # TODO: why can a Paper ever have "editors"? it's allowed by the schema
    editors: list[NameSpecification] = field(factory=list, repr=False)
    errata: list[PaperErratum] = field(factory=list, repr=False)
    revisions: list[PaperRevision] = field(factory=list, repr=False)
    videos: list[VideoReference] = field(factory=list, repr=False)

    abstract: Optional[MarkupText] = field(default=None)
    deletion: Optional[PaperDeletionNotice] = field(default=None, repr=False)
    doi: Optional[str] = field(default=None, repr=False)
    ingest_date: Optional[str] = field(default=None, repr=False)
    language: Optional[str] = field(default=None, repr=False)
    note: Optional[str] = field(default=None, repr=False)
    pages: Optional[str] = field(default=None, repr=False)
    paperswithcode: Optional[PapersWithCodeReference] = field(
        default=None, on_setattr=attrs.setters.frozen, repr=False
    )
    pdf: Optional[PDFReference] = field(default=None, repr=False)

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

    @property
    def bibtype(self) -> str:
        """The BibTeX entry type for this paper."""
        match self.is_frontmatter, self.parent.type:
            case (True, VolumeType.JOURNAL):
                return "book"
            case (False, VolumeType.JOURNAL):
                return "article"
            case (True, VolumeType.PROCEEDINGS):
                return "proceedings"
            case (False, VolumeType.PROCEEDINGS):
                return "inproceedings"
            case _:  # pragma: no cover
                raise ValueError(f"Unknown volume type: {self.parent.type}")

    @property
    def address(self) -> Optional[str]:
        """The publisher's address for this paper. Inherited from the parent Volume."""
        return self.parent.address

    @property
    def month(self) -> Optional[str]:
        """The month of publication. Inherited from the parent Volume."""
        return self.parent.month

    @property
    def publisher(self) -> Optional[str]:
        """The paper's publisher. Inherited from the parent Volume."""
        return self.parent.publisher

    @property
    def venue_ids(self) -> list[str]:
        """List of venue IDs associated with this paper. Inherited from the parent Volume."""
        return self.parent.venue_ids

    @property
    def year(self) -> str:
        """The year of publication. Inherited from the parent Volume."""
        return self.parent.year

    @property
    def web_url(self) -> str:
        """The URL of this paper's landing page on the ACL Anthology website."""
        return cast(str, config["paper_page_template"]).format(self.full_id)

    def get_editors(self) -> list[NameSpecification]:
        """
        Returns:
            `self.editors`, if not empty; the parent volume's editors otherwise.
        """
        if self.editors:
            return self.editors
        return self.parent.editors

    def get_events(self) -> list[Event]:
        """
        Returns:
            A list of events associated with this paper.
        """
        return self.root.events.by_volume(self.parent.full_id_tuple)

    def get_ingest_date(self) -> datetime.date:
        """
        Returns:
            The date when this paper was added to the Anthology. Inherits from its parent volume. If not set, will return [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE] instead.
        """
        if self.ingest_date is None:
            return self.parent.get_ingest_date()
        return datetime.date.fromisoformat(self.ingest_date)

    def to_bibtex(self, with_abstract: bool = False) -> str:
        """Generate a BibTeX entry for this paper.

        Arguments:
            with_abstract: If True, includes the abstract in the BibTeX entry.

        Returns:
            The BibTeX entry for this paper as a formatted string.
        """
        bibtex_fields: list[tuple[str, SerializableAsBibTeX]] = [
            ("title", self.title),
            ("author", self.authors),
            ("editor", self.get_editors()),
        ]
        if not self.is_frontmatter:
            match self.parent.type:
                case VolumeType.JOURNAL:
                    bibtex_fields.extend(
                        [
                            ("journal", self.parent.get_journal_title()),
                            ("volume", self.parent.journal_volume),
                            ("number", self.parent.journal_issue),
                        ]
                    )
                case VolumeType.PROCEEDINGS:
                    bibtex_fields.append(("booktitle", self.parent.title))
        bibtex_fields.extend(
            [
                ("month", self.month),
                ("year", self.year),
                ("address", self.address),
                ("publisher", self.publisher),
                ("note", self.note),
                ("url", self.web_url),
                ("doi", self.doi),
                ("pages", self.pages),
                ("language", self.language),
                ("ISBN", self.parent.isbn),
            ]
        )
        if with_abstract and self.abstract is not None:
            bibtex_fields.append(("abstract", self.abstract))
        return make_bibtex_entry(self.bibtype, self.bibkey, bibtex_fields)

    @classmethod
    def from_frontmatter_xml(cls, parent: Volume, paper: etree._Element) -> Paper:
        """Instantiates a new paper from a `<frontmatter>` block in the XML."""
        kwargs: dict[str, Any] = {
            "id": "0",
            "parent": parent,
            # A frontmatter's title is the parent volume's title
            "title": parent.title,
            "attachments": {},
        }
        # Frontmatter only supports a small subset of regular paper attributes,
        # so we duplicate these here -- but maybe suboptimal?
        for element in paper:
            if element.tag in ("bibkey", "doi", "pages"):
                kwargs[element.tag] = element.text
            elif element.tag == "attachment":
                type_ = str(element.get("type", "attachment"))
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
            "id": str(paper.get("id")),
            "parent": parent,
            "authors": [],
            "editors": [],
            "attachments": {},
        }
        if (ingest_date := paper.get("ingest-date")) is not None:
            kwargs["ingest_date"] = str(ingest_date)
        if paper.get("type") is not None:
            # TODO: this is currently ignored
            log.debug(f"Paper {paper.get('id')!r}: Type attribute is currently ignored")
            # kwargs["type"] = str(paper_type)
        for element in paper:
            if element.tag in ("bibkey", "doi", "language", "note", "pages"):
                kwargs[element.tag] = element.text
            elif element.tag in ("author", "editor"):
                kwargs[f"{element.tag}s"].append(NameSpecification.from_xml(element))
            elif element.tag in ("abstract", "title"):
                kwargs[element.tag] = MarkupText.from_xml(element)
            elif element.tag == "attachment":
                type_ = str(element.get("type", "attachment"))
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
                    f"Paper {paper.get('id')!r}: Tag '{element.tag}' is currently ignored"
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
            paper.set("ingest-date", self.ingest_date)
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
            elem.set("type", type_)
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
            date=str(element.get("date")),
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
            id=str(element.get("id")),
            pdf=PDFReference.from_xml(element),
            date=element.get("date"),
        )

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this erratum in Anthology XML format.
        """
        elem = E.erratum(self.pdf.name, id=self.id, hash=str(self.pdf.checksum))
        if self.date is not None:
            elem.set("date", self.date)
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
            id=str(element.get("id")),
            note=str(element.text) if element.text else None,
            pdf=PDFReference(str(element.get("href")), str(element.get("hash"))),
            date=element.get("date"),
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
            elem.set("date", self.date)
        return elem
