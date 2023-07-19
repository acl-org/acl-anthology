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

from ..files import PDFReference
from ..people import Name
from ..text import MarkupText
from ..utils.ids import build_id

if TYPE_CHECKING:
    from . import Volume


@define
class Paper:
    """A paper entry.

    Attributes:
        id (str): The ID of this paper (e.g. "1" or "42").
        parent (Volume): The Volume object that this paper belongs to.
        bibkey (str): Bibliography key, e.g. for BibTeX.  Must be unique across all papers in the Anthology.
        title (MarkupText): The title of the paper.

        authors (list[Name]): Names of authors associated with this paper; can be empty.
        awards (list[str]): Names of awards this has paper has received; can be empty.
        editors (list[Name]): Names of editors associated with this paper; can be empty.

        abstract (Optional[MarkupText]): The full abstract.
        deletion (Optional[PaperDeletionNotice]): A notice of the paper's retraction or removal, if applicable.
        doi (Optional[str]): The DOI for the paper.
        ingest_date (Optional[str]): The date of ingestion.
        language (Optional[str]): The language this paper is (mainly) written in.  When given, this should be a ISO 639-2 code (e.g. "eng"), though occasionally IETF is used (e.g. "pt-BR").
        note (Optional[str]): A note attached to this paper.  Used very sparingly.
        pages (Optional[str]): Page numbers of this paper within its volume.
        pdf (Optional[PDFReference]): A reference to the paper's PDF.
    """

    id: str
    parent: Volume = field(repr=False, eq=False)
    bibkey: str
    title: MarkupText = field()

    authors: list[Name] = Factory(list)
    awards: list[str] = Factory(list)
    editors: list[Name] = Factory(list)

    abstract: Optional[MarkupText] = field(default=None)
    # TODO attachment + video
    deletion: Optional[PaperDeletionNotice] = field(default=None)
    doi: Optional[str] = field(default=None)
    ingest_date: Optional[str] = field(default=None)
    # TODO revision + erratum
    language: Optional[str] = field(default=None)
    note: Optional[str] = field(default=None)
    pages: Optional[str] = field(default=None)
    pdf: Optional[PDFReference] = field(default=None)
    # TODO: pwcdataset + pwccode; field(on_setattr=attrs.setters.frozen)

    # TODO: fields that are currently ignored: issue, journal, mrf

    # TODO: properties we obtain from the parent volume?

    @property
    def full_id(self) -> str:
        """The full anthology ID of this paper (e.g. "L06-1042" or "2022.emnlp-main.1")."""
        return build_id(self.parent.parent.id, self.parent.id, self.id)

    @property
    def is_deleted(self) -> bool:
        """Returns True if this paper was retracted or removed from the Anthology."""
        return self.deletion is not None

    def get_ingest_date(self) -> datetime.date:
        """
        Returns:
            The date when this paper was added to the Anthology. Inherits from its parent volume. If not set, will return [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE] instead.
        """
        if self.ingest_date is None:
            return self.parent.get_ingest_date()
        return datetime.date.fromisoformat(self.ingest_date)

    @classmethod
    def from_xml(cls, parent: Volume, meta: etree._Element) -> Paper:
        """Instantiates a new paper from its `<paper>` block in the XML."""
        paper = cast(etree._Element, meta.getparent())
        kwargs: dict[str, Any] = {
            "id": str(paper.attrib["id"]),
            "parent": parent,
            "authors": [],
            "awards": [],
            "editors": [],
        }
        if (ingest_date := paper.attrib.get("ingest-date")) is not None:
            kwargs["ingest_date"] = str(ingest_date)
        if (paper_type := paper.attrib.get("type")) is not None:
            kwargs["type"] = str(paper_type)
        for element in meta:
            if element.tag in ("doi", "language", "note", "pages"):
                kwargs[element.tag] = element.text
            elif element.tag in ("author", "editor"):
                kwargs[f"{element.tag}s"].append(Name.from_xml(element))
            elif element.tag in ("abstract", "title"):
                kwargs[element.tag] = MarkupText.from_xml(element)
            elif element.tag == "award":
                kwargs["awards"].append(element.text)
            elif element.tag == "url":
                checksum = element.attrib.get("hash")
                kwargs["pdf"] = PDFReference(
                    str(element.text), str(checksum) if checksum else None
                )
            elif element.tag in ("removed", "retracted"):
                kwargs["deletion"] = PaperDeletionNotice(
                    type=PaperDeletionType(str(element.tag)),
                    note=str(element.text),
                    date=str(element.attrib["date"]),
                )
            elif element.tag in ("issue", "journal", "mrf"):
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
