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
from typing import Any, Optional, TYPE_CHECKING

from ..files import (
    AttachmentReference,
    PapersWithCodeReference,
    PDFReference,
    VideoReference,
)
from ..people import NameSpecification
from ..text import MarkupText
from ..utils.ids import build_id, AnthologyID
from ..utils.xml import xsd_boolean

if TYPE_CHECKING:
    from . import Volume


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
    def full_id_tuple(self) -> AnthologyID:
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
                checksum = element.attrib.get("hash")
                type_ = str(element.attrib.get("type", "attachment"))
                kwargs["attachments"][type_] = AttachmentReference(
                    str(element.text), str(checksum)
                )
            elif element.tag == "revision":
                if "revisions" not in kwargs:
                    kwargs["revisions"] = []
                kwargs["revisions"].append(PaperRevision.from_xml(element))
            elif element.tag == "url":
                checksum = element.attrib.get("hash")
                kwargs["pdf"] = PDFReference(
                    str(element.text), str(checksum) if checksum else None
                )
            else:
                raise ValueError(f"Unsupported element for Frontmatter: <{element.tag}>")
        return cls(**kwargs)

    @classmethod
    def from_xml(cls, parent: Volume, paper: etree._Element) -> Paper:
        """Instantiates a new paper from its `<paper>` block in the XML."""
        kwargs: dict[str, Any] = {
            "id": str(paper.attrib["id"]),
            "parent": parent,
            "authors": [],
            "editors": [],
            "attachments": {},
        }
        if (ingest_date := paper.attrib.get("ingest-date")) is not None:
            kwargs["ingest_date"] = str(ingest_date)
        # TODO: this is currently ignored
        # if (paper_type := paper.attrib.get("type")) is not None:
        #    kwargs["type"] = str(paper_type)
        for element in paper:
            if element.tag in ("bibkey", "doi", "language", "note", "pages"):
                kwargs[element.tag] = element.text
            elif element.tag in ("author", "editor"):
                kwargs[f"{element.tag}s"].append(NameSpecification.from_xml(element))
            elif element.tag in ("abstract", "title"):
                kwargs[element.tag] = MarkupText.from_xml(element)
            elif element.tag == "attachment":
                checksum = element.attrib.get("hash")
                type_ = str(element.attrib.get("type", "attachment"))
                kwargs["attachments"][type_] = AttachmentReference(
                    str(element.text), str(checksum)
                )
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
                pwc_tuple = (str(element.text), str(element.attrib["url"]))
                if element.tag == "pwccode":
                    kwargs["paperswithcode"].community_code = xsd_boolean(
                        str(element.attrib["additional"])
                    )
                    if pwc_tuple[1]:
                        kwargs["paperswithcode"].code = pwc_tuple
                else:  # element.tag == "pwcdataset"
                    kwargs["paperswithcode"].datasets.append(pwc_tuple)
            elif element.tag in ("removed", "retracted"):
                kwargs["deletion"] = PaperDeletionNotice.from_xml(element)
            elif element.tag == "revision":
                if "revisions" not in kwargs:
                    kwargs["revisions"] = []
                kwargs["revisions"].append(PaperRevision.from_xml(element))
            elif element.tag == "url":
                checksum = element.attrib.get("hash")
                kwargs["pdf"] = PDFReference(
                    str(element.text), str(checksum) if checksum else None
                )
            elif element.tag == "video":
                if "videos" not in kwargs:
                    kwargs["videos"] = []
                permission = True
                if (value := element.attrib.get("permission")) is not None:
                    permission = xsd_boolean(str(value))
                kwargs["videos"].append(
                    VideoReference(
                        name=str(element.attrib.get("href")), permission=permission
                    )
                )
            elif element.tag in ("issue", "journal", "mrf"):
                # TODO: these fields are currently ignored
                pass
            else:
                raise ValueError(f"Unsupported element for Paper: <{element.tag}>")
        return cls(**kwargs)


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
            pdf=PDFReference(str(element.text), str(element.attrib["hash"])),
            date=(str(element.attrib["date"]) if "date" in element.attrib else None),
        )


@define
class PaperRevision:
    """A revised version of a paper."""

    id: str
    """An ID for this revision."""

    note: str
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
            note=str(element.text),
            pdf=PDFReference(str(element.attrib["href"]), str(element.attrib["hash"])),
            date=(str(element.attrib["date"]) if "date" in element.attrib else None),
        )
