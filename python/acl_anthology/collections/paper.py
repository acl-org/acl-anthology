# Copyright 2023-2025 Marcel Bollmann <marcel@bollmann.me>
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
from attrs import define, field, validators as v
import datetime
from functools import cached_property
import langcodes
from lxml import etree
from lxml.builder import E
from typing import cast, Any, Optional, TYPE_CHECKING

from .. import constants
from ..config import config
from ..exceptions import AnthologyInvalidIDError, AnthologyXMLError
from ..files import (
    AttachmentReference,
    PapersWithCodeReference,
    PDFReference,
    PDFThumbnailReference,
    VideoReference,
)
from ..people import NameSpecification
from ..text import MarkupText
from ..utils.attrs import auto_validate_types, date_to_str, int_to_str
from ..utils.citation import citeproc_render_html, render_acl_citation
from ..utils.ids import build_id, is_valid_item_id, AnthologyIDTuple
from ..utils.latex import make_bibtex_entry
from ..utils.logging import get_logger
from .types import PaperDeletionType, PaperType, VolumeType

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..utils.latex import SerializableAsBibTeX
    from . import Event, Volume

log = get_logger()


@define(field_transformer=auto_validate_types)
class PaperErratum:
    """An erratum for a paper."""

    id: str = field(converter=int_to_str, validator=v.matches_re(r"^[1-9][0-9]?$"))
    """An ID for this erratum.  Must be numeric."""

    pdf: PDFReference = field()
    """A reference to the erratum's PDF."""

    date: Optional[str] = field(
        default=None,
        converter=date_to_str,
        validator=v.optional(v.matches_re(constants.RE_ISO_DATE)),
    )
    """The date where this erratum was added."""

    @pdf.validator
    def _check_pdf(self, _: Any, value: Any) -> None:
        # The PDFReference for an erratum must be a local filename according to the schema
        if not isinstance(value, PDFReference):
            raise TypeError(
                f"'pdf' must be {PDFReference!r} (got '{value!r}' that is a {type(value)!r})"
            )
        if not value.is_local:
            raise ValueError(
                f"'pdf' of a PaperErratum must be a local file reference (got '{value}')"
            )

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


@define(field_transformer=auto_validate_types)
class PaperRevision:
    """A revised version of a paper."""

    id: str = field(converter=int_to_str, validator=v.matches_re(r"^[1-9][0-9]?$"))
    """An ID for this revision.  Must be numeric."""

    note: Optional[str] = field()
    """A note explaining the reason for the revision."""

    pdf: PDFReference = field()
    """A reference to the revision's PDF."""

    date: Optional[str] = field(
        default=None,
        converter=date_to_str,
        validator=v.optional(v.matches_re(constants.RE_ISO_DATE)),
    )
    """The date where this revision was added."""

    @pdf.validator
    def _check_pdf(self, _: Any, value: Any) -> None:
        # The PDFReference for a revision must be a local filename according to the schema
        if not isinstance(value, PDFReference):
            raise TypeError(
                f"'pdf' must be {PDFReference!r} (got '{value!r}' that is a {type(value)!r})"
            )
        if not value.is_local:
            raise ValueError(
                f"'pdf' of a PaperRevision must be a local file reference (got '{value}')"
            )

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


@define(field_transformer=auto_validate_types)
class PaperDeletionNotice:
    """A notice about a paper's deletion (i.e., retraction or removal) from the Anthology."""

    type: PaperDeletionType = field(converter=PaperDeletionType)
    """Type indicating whether the paper was _retracted_ or _removed_."""

    note: Optional[str] = field()
    """A note explaining the retraction or removal."""

    date: str = field(
        default=None, converter=date_to_str, validator=v.matches_re(constants.RE_ISO_DATE)
    )
    """The date on which the paper was retracted or removed."""

    @classmethod
    def from_xml(cls, element: etree._Element) -> PaperDeletionNotice:
        """Instantiates a deletion notice from its `<removed>` or `<retracted>` block in the XML."""
        return cls(
            type=PaperDeletionType(str(element.tag)),
            note=str(element.text) if element.text else None,
            date=str(element.get("date")),
        )

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this deletion notice in Anthology XML format.
        """
        return cast(
            etree._Element,
            getattr(E, self.type.value)(self.note if self.note else "", date=self.date),
        )


def _attachment_validator(instance: Paper, _: Any, value: Any) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not isinstance(value[0], str)
        or not isinstance(value[1], AttachmentReference)
    ):
        raise TypeError(
            f"'attachments' needs to contain tuples of (str, AttachmentReference) (got: {value!r})"
        )


def _update_bibkey_index(paper: Paper, attr: attrs.Attribute[Any], value: str) -> str:
    """Update the bibkey in [BibkeyIndex][acl_anthology.collections.bibkeys.BibkeyIndex].

    Intended to be called from `on_setattr` of an [attrs.field][].
    """
    bibkey_index = paper.root.collections.bibkeys
    value = bibkey_index._index_paper(value, paper)
    return value


@define(field_transformer=auto_validate_types)
class Paper:
    """A paper entry.

    Info:
        To create a new paper, use [`Volume.create_paper()`][acl_anthology.collections.volume.Volume.create_paper].

    Attributes: Required Attributes:
        id: The ID of this paper (e.g. "1" or "42").
        parent: The Volume object that this paper belongs to.
        bibkey: Bibliography key, e.g. for BibTeX.  Must be unique across all papers in the Anthology.
        title: The title of the paper.

    Attributes: List Attributes:
        attachments: File attachments of this paper, as tuples of the format `(type_of_attachment, attachment_file)`; can be empty.
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
        issue: The journal issue for this paper.  Should normally be set at the volume level; you probably want to use `get_issue()` instead.
        journal: The journal name for this paper.   Should normally be set at the volume level; you probably want to use `get_journal_title()` instead.
        language: The language this paper is (mainly) written in.  When given, this should be a ISO 639-2 code (e.g. "eng"), though occasionally IETF is used (e.g. "pt-BR").
        note: A note attached to this paper.  Used very sparingly.
        pages: Page numbers of this paper within its volume.
        paperswithcode: Links to code implementations and datasets as provided by [Papers with Code](https://paperswithcode.com/).
        pdf: A reference to the paper's PDF.
        type: The paper's type, currently used to mark frontmatter and backmatter.
    """

    id: str = field(converter=int_to_str)
    parent: Volume = field(repr=False, eq=False)
    bibkey: str = field(
        on_setattr=attrs.setters.pipe(attrs.setters.validate, _update_bibkey_index),
    )
    title: MarkupText = field()

    attachments: list[tuple[str, AttachmentReference]] = field(
        factory=list,
        repr=False,
        validator=v.deep_iterable(
            member_validator=_attachment_validator,
            iterable_validator=v.instance_of(list),
        ),
    )
    authors: list[NameSpecification] = field(factory=list)
    awards: list[str] = field(factory=list, repr=False)
    # TODO: why can a Paper ever have "editors"? it's allowed by the schema
    editors: list[NameSpecification] = field(factory=list, repr=False)
    errata: list[PaperErratum] = field(
        factory=list,
        repr=False,
        validator=v.deep_iterable(
            member_validator=v.instance_of(PaperErratum),
            iterable_validator=v.instance_of(list),
        ),
    )
    revisions: list[PaperRevision] = field(
        factory=list,
        repr=False,
        validator=v.deep_iterable(
            member_validator=v.instance_of(PaperRevision),
            iterable_validator=v.instance_of(list),
        ),
    )
    videos: list[VideoReference] = field(factory=list, repr=False)

    abstract: Optional[MarkupText] = field(default=None)
    deletion: Optional[PaperDeletionNotice] = field(
        default=None, repr=False, validator=v.optional(v.instance_of(PaperDeletionNotice))
    )
    doi: Optional[str] = field(default=None, repr=False)
    ingest_date: Optional[str] = field(default=None, repr=False)
    issue: Optional[str] = field(default=None, repr=False)
    journal: Optional[str] = field(default=None, repr=False)
    language: Optional[str] = field(default=None, repr=False)
    note: Optional[str] = field(default=None, repr=False)
    pages: Optional[str] = field(default=None, repr=False)
    paperswithcode: Optional[PapersWithCodeReference] = field(
        default=None, on_setattr=attrs.setters.frozen, repr=False
    )
    pdf: Optional[PDFReference] = field(default=None, repr=False)
    type: PaperType = field(default=PaperType.PAPER, repr=False, converter=PaperType)

    @id.validator
    def _check_id(self, _: Any, value: str) -> None:
        if not is_valid_item_id(value):
            raise AnthologyInvalidIDError(value, "not a valid paper ID")

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
        return self.type == PaperType.FRONTMATTER

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
    def csltype(self) -> str:
        """The [CSL type](https://docs.citationstyles.org/en/stable/specification.html#appendix-iii-types) for this paper."""
        if self.is_frontmatter:
            return "book"
        if self.parent.type == VolumeType.JOURNAL:
            return "article-journal"
        # else:
        return "paper-conference"

    @cached_property
    def citeproc_dict(self) -> dict[str, Any]:
        """The citation object corresponding to this paper for use with CiteProcJSON."""
        data: dict[str, Any] = {
            "id": self.bibkey,
            "title": self.title.as_text(),
            "type": self.csltype,
            "author": [namespec.citeproc_dict for namespec in self.authors],
            "editor": [namespec.citeproc_dict for namespec in self.get_editors()],
            "publisher": self.publisher,
            "publisher-place": self.address,
            # TODO: month currently not included
            "issued": {"date-parts": [[self.year]]},
            "URL": self.web_url,
            "DOI": self.doi,
            "ISBN": self.parent.isbn,
            "page": self.pages,
        }
        if self.is_frontmatter:
            data["author"] = data["editor"]
        match self.parent.type:
            case VolumeType.JOURNAL:
                data["container-title"] = self.get_journal_title()
                data["volume"] = self.parent.journal_volume
                data["issue"] = self.get_issue()
            case VolumeType.PROCEEDINGS:
                data["container-title"] = self.parent.title.as_text()
        return {k: v for k, v in data.items() if v is not None}

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
    def thumbnail(self) -> Optional[PDFThumbnailReference]:
        """A reference to a thumbnail image of the paper's PDF."""
        if self.pdf is not None:
            return PDFThumbnailReference(self.full_id)
        return None

    @property
    def language_name(self) -> Optional[str]:
        """The name of the language this paper is written in, if specified."""
        if self.language is None:
            return None
        return langcodes.Language.get(self.language).display_name()

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

    def get_issue(self) -> Optional[str]:
        """
        Returns:
            The issue number of this paper. Inherits from its parent volume unless explicitly set for the paper.
        """
        if self.issue is None:
            return self.parent.journal_issue
        return self.issue

    def get_journal_title(self) -> str:
        """
        Returns:
            The journal title for this paper.  Inherits from its parent volume unless explicitly set for the paper.
        """
        if self.journal is None:
            return self.parent.get_journal_title()
        return self.journal

    def refresh_bibkey(self) -> str:
        """Replace this paper's bibkey with a unique, automatically-generated one.

        Can be used to re-generate a bibkey after the title or author information has been modified.

        Returns:
            The new bibkey.  (May be identical to the current one.)
        """
        # Triggers the re-creation of the bibkey via on_setattr mechanism
        self.bibkey = constants.NO_BIBKEY
        return self.bibkey

    def to_bibtex(self, with_abstract: bool = False) -> str:
        """Generate a BibTeX entry for this paper.

        Arguments:
            with_abstract: If True, includes the abstract in the BibTeX entry.

        Returns:
            The BibTeX entry for this paper as a formatted string.

        Raises:
            ValueError: If 'bibkey' is set to [`constants.NO_BIBKEY`][acl_anthology.constants.NO_BIBKEY].
        """
        if self.bibkey == constants.NO_BIBKEY:  # pragma: no cover
            raise ValueError("Cannot generate BibTeX entry without bibkey")
        # Note: Fields are added in the order in which they will appear in the
        # BibTeX entry, for reproducibility
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
                            ("journal", self.get_journal_title()),
                            ("volume", self.parent.journal_volume),
                            ("number", self.get_issue()),
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

    def to_citation(self, style: Optional[str] = None) -> str:
        """Generate a citation (reference) for this paper.

        Arguments:
            style: A path to a CSL file.  If None (default), uses the built-in ACL citation style.

        Returns:
            The generated citation reference as a single string with HTML markup.  See [`citeproc_render_html()`][acl_anthology.utils.citation.citeproc_render_html] for the rationale behind returning a single string here.
        """
        if style is None:
            return render_acl_citation(self)
        return citeproc_render_html(self.citeproc_dict, style)

    def to_markdown_citation(self) -> str:
        """Generate a brief citation (reference) in Markdown for this paper.

        Returns:
            The generated citation reference as a single string with Markdown markup.
        """
        namespecs = self.authors if not self.is_frontmatter else self.get_editors()
        if len(namespecs) == 0:
            name = ""
        elif len(namespecs) == 1:
            name = namespecs[0].last
        elif len(namespecs) == 2:
            name = f"{namespecs[0].last} & {namespecs[1].last}"
        else:
            name = f"{namespecs[0].last} et al."

        venue_year = (
            f"{self.year}"
            if self.parent.venue_acronym == "WS"
            else f"{self.parent.venue_acronym} {self.year}"
        )
        if name:
            return f"[{self.title.as_text()}]({self.web_url}) ({name}, {venue_year})"
        else:
            return f"[{self.title.as_text()}]({self.web_url}) ({venue_year})"

    @classmethod
    def from_frontmatter_xml(cls, parent: Volume, paper: etree._Element) -> Paper:
        """Instantiates a new paper from a `<frontmatter>` block in the XML."""
        kwargs: dict[str, Any] = {
            "id": constants.FRONTMATTER_ID,
            "type": PaperType.FRONTMATTER,
            "parent": parent,
            # A frontmatter's title is the parent volume's title
            "title": parent.title,
            "attachments": [],
        }
        # Frontmatter only supports a small subset of regular paper attributes,
        # so we duplicate these here -- but maybe suboptimal?
        for element in paper:
            if element.tag in ("bibkey", "doi", "pages"):
                kwargs[element.tag] = element.text
            elif element.tag == "attachment":
                type_ = str(element.get("type", ""))
                kwargs["attachments"].append(
                    (type_, AttachmentReference.from_xml(element))
                )
            elif element.tag == "revision":
                if "revisions" not in kwargs:
                    kwargs["revisions"] = []
                kwargs["revisions"].append(PaperRevision.from_xml(element))
            elif element.tag == "url":
                kwargs["pdf"] = PDFReference.from_xml(element)
            else:
                raise AnthologyXMLError(
                    parent.full_id_tuple,
                    element.tag,
                    "unsupported element for <frontmatter>",
                )
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
            "type": PaperType(paper.get("type", "paper")),
            "parent": parent,
            "authors": [],
            "editors": [],
            "attachments": [],
        }
        if (ingest_date := paper.get("ingest-date")) is not None:
            kwargs["ingest_date"] = str(ingest_date)
        for element in paper:
            if element.tag in (
                "bibkey",
                "doi",
                "issue",
                "journal",
                "language",
                "note",
                "pages",
            ):
                kwargs[element.tag] = element.text
            elif element.tag in ("author", "editor"):
                kwargs[f"{element.tag}s"].append(NameSpecification.from_xml(element))
            elif element.tag in ("abstract", "title"):
                kwargs[element.tag] = MarkupText.from_xml(element)
            elif element.tag == "attachment":
                type_ = str(element.get("type", ""))
                kwargs["attachments"].append(
                    (type_, AttachmentReference.from_xml(element))
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
            elif element.tag == ("mrf"):
                # consider an attachment of type "mrf"
                kwargs["attachments"].append(
                    ("mrf", AttachmentReference.from_xml(element))
                )
            else:
                raise AnthologyXMLError(
                    parent.full_id_tuple, element.tag, "unsupported element for <paper>"
                )
        return cls(**kwargs)

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this paper as a `<paper>` or `<frontmatter>` block in the Anthology XML format.

        Raises:
            ValueError: If 'bibkey' is set to [`constants.NO_BIBKEY`][acl_anthology.constants.NO_BIBKEY].
        """
        if self.bibkey == constants.NO_BIBKEY:  # pragma: no cover
            raise ValueError("Cannot serialize a Paper without bibkey")
        if self.is_frontmatter:
            paper = etree.Element("frontmatter")
        else:
            paper = etree.Element("paper", attrib={"id": self.id})
        if self.ingest_date is not None:
            paper.set("ingest-date", self.ingest_date)
        if self.type == PaperType.BACKMATTER:
            paper.set("type", "backmatter")
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
        for tag in ("doi", "issue", "journal", "language", "note"):
            if (value := getattr(self, tag)) is not None:
                paper.append(getattr(E, tag)(value))
        for type_, attachment in self.attachments:
            if type_ == "mrf":  # rarely used <mrf> tag
                elem = attachment.to_xml("mrf")
                elem.set("src", "latexml")
            else:
                elem = attachment.to_xml("attachment")
                if type_:
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
