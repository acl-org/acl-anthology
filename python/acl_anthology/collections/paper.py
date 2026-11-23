# Copyright 2023-2026 Marcel Bollmann <marcel@bollmann.me>
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
from attrs import define, field, converters, setters, validators as v
import datetime
import itertools as it
from lxml import etree
from lxml.builder import E
import sys
from typing import Any, ClassVar, Iterable, Optional, TYPE_CHECKING

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

from .. import constants
from ..exceptions import AnthologyInvalidIDError, AnthologyXMLError
from ..files import (
    AttachmentReference,
    AudioReference,
    PDFReference,
    URLReference,
    VideoReference,
    validate_url_tuple,
)
from ..people import NameSpecification
from ..text import MarkupText, to_markuptext
from ..utils.attrs import (
    attach_custom_repr,
    attach_parent,
    auto_validate_types,
    date_to_str,
    int_to_str,
    into_namespec_tuple,
    track_modifications,
)
from ..utils.ids import is_valid_item_id
from ..utils.logging import get_logger
from .types import PaperType, VolumeType
from .types import PaperDeletionType as PaperDeletionType
from .item import update_person_itemids, validate_pdf
from .record import (
    DeletionNotice as PaperDeletionNotice,
    PDFRecord,
    update_bibkey,
    validate_attachment,
)

if TYPE_CHECKING:
    from ..utils.latex import SerializableAsBibTeX
    from . import Event, Frontmatter, Volume

log = get_logger()


@attach_custom_repr
@define(field_transformer=auto_validate_types, frozen=True, kw_only=True)
class Award:
    """An award received by a paper."""

    name: str = field()
    """The name of the award."""

    reasoning: Optional[str] = field(default=None)
    """The reason the paper received the award, if provided."""

    @classmethod
    def from_xml(cls, element: etree._Element) -> Award:
        """Instantiates an award from an ``<award>`` block."""
        name = element.get("name")
        if name is None:
            raise ValueError("An award must have a name")
        return cls(name=name, reasoning=element.text or None)

    def to_xml(self) -> etree._Element:
        """Returns an ``<award>`` block."""
        award = etree.Element("award", attrib={"name": self.name})
        if self.reasoning is not None:
            award.text = self.reasoning
        return award


@attach_custom_repr
@define(field_transformer=auto_validate_types, frozen=True)
class PaperErratum:
    """An erratum for a paper."""

    id: str = field(converter=int_to_str, validator=v.matches_re(r"^[1-9][0-9]?$"))
    """An ID for this erratum.  Must be numeric."""

    pdf: PDFReference = field()
    """A reference to the erratum's PDF.

    Note:
        The `name` on this reference is only correctly resolved when accessed via [`Paper.errata`][acl_anthology.collections.paper.Paper.errata]; it is derived from the parent paper's `full_id` and is not present in the XML.
    """

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
        elem = E.erratum(id=self.id, hash=str(self.pdf.checksum))
        if self.date is not None:
            elem.set("date", self.date)
        return elem


@attach_custom_repr
@define(field_transformer=auto_validate_types, frozen=True)
class PaperRevision:
    """A revised version of a paper."""

    id: str = field(converter=int_to_str, validator=v.matches_re(r"^[1-9][0-9]?$"))
    """An ID for this revision.  Must be numeric."""

    note: Optional[str] = field()
    """A note explaining the reason for the revision."""

    pdf: PDFReference = field()
    """A reference to the revision's PDF.

    Note:
        The `name` on this reference is only correctly resolved when accessed via [`PDFRecord.revisions`][acl_anthology.collections.record.PDFRecord.revisions]; it is derived from the parent record's `full_id` and is not present in the XML.
    """

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
            pdf=PDFReference(name="", checksum=str(element.get("hash"))),
            date=element.get("date"),
        )

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this revision in Anthology XML format.
        """
        elem = E.revision(
            id=self.id,
            hash=str(self.pdf.checksum),
        )
        if self.note:
            elem.text = str(self.note)
        if self.date is not None:
            elem.set("date", self.date)
        return elem


def _check_pdf_names(
    paper: PDFRecord, letter: str, value: Iterable[PaperErratum | PaperRevision]
) -> None:
    """Verify that each item's PDF reference name, if given, matches the name that would automatically be derived for it from `paper`'s `full_id` and the item's own `id` (see `Paper.errata`/`Paper.revisions`).

    Intended to be called from the validator of `Paper._errata`/`Paper._revisions`.
    """
    for item in value:
        expected = f"{paper.full_id}{letter}{item.id}"
        if item.pdf.name and item.pdf.name != expected:
            raise ValueError(
                f"PDF reference name {item.pdf.name!r} does not match the automatically derived name {expected!r}"
            )


def _check_errata_pdf_names(
    paper: Paper, _: Any, value: tuple[PaperErratum, ...]
) -> None:
    _check_pdf_names(paper, "e", value)


def _check_revisions_pdf_names(
    paper: PDFRecord, _: Any, value: tuple[PaperRevision, ...]
) -> None:
    _check_pdf_names(paper, "v", value)


def _into_award_tuple(value: Iterable[str | Award]) -> tuple[Award, ...]:
    if isinstance(value, str):
        raise TypeError(
            "Expected Iterable[str | Award], got str; this is most likely a mistake"
        )
    return tuple(
        Award(name=award) if isinstance(award, str) else award for award in value
    )


@attach_custom_repr
@define(
    field_transformer=auto_validate_types,
    on_setattr=[setters.convert, setters.validate, track_modifications],
)
class Paper(PDFRecord):
    """A printed paper, distinct from frontmatter and standalone media.

    Info:
        To create a new paper, use [`Volume.create_paper()`][acl_anthology.collections.volume.Volume.create_paper].

    Attributes: Required Attributes:
        id: The ID of this paper (e.g. "1" or "42").
        parent: The Volume object that this paper belongs to.
        bibkey: Bibliography key, e.g. for BibTeX.  Must be unique across all papers in the Anthology.
        title: The title of the paper.

    Attributes: Tuple Attributes:
        attachments: File attachments of this paper, as tuples of the format `(type_of_attachment, attachment_file)`; can be empty.
        authors: Names of authors associated with this paper; can be empty.
        awards: Awards this paper has received, represented by [`Award`][acl_anthology.collections.paper.Award] objects; can be empty.
        errata: Errata for this paper; can be empty.  Each erratum's PDF reference has its `name` derived from this paper's `full_id` and the erratum's own `id`.
        revisions: Revisions for this paper; can be empty.  Each revision's PDF reference has its `name` derived from this paper's `full_id` and the revision's own `id`.
        videos: Zero or more references to video recordings belonging to this paper.
        audios: Zero or more references to audio recordings.
        urls: Links to external, non-locally-hosted resources associated with this paper (e.g. supplementary materials), as tuples of `(type_of_link, reference)`; can be empty.

    Attributes: Optional Attributes:
        abstract: The full abstract.
        deletion: A notice of the paper's retraction or removal, if applicable.
        doi: The DOI for the paper.
        language: The language this paper is (mainly) written in.  When given, this should be a ISO 639-2 code (e.g. "eng"), though occasionally IETF is used (e.g. "pt-BR").
        month: The month of publication. If not set on the paper, this is inherited from the parent volume.
        note: A note attached to this paper.  Used very sparingly.
        pages: Page numbers of this paper within its volume.
        pdf: A reference to the paper's PDF.
        type: Whether this is a regular paper or backmatter.
    """

    _namespec_fields: ClassVar[tuple[str, ...]] = ("authors", "_editors")
    id: str = field(converter=int_to_str)  # validator defined below
    parent: Volume = field(repr=False, eq=False)
    bibkey: str = field(
        validator=v.matches_re(constants.RE_BIBKEY),
        on_setattr=[setters.validate, track_modifications, update_bibkey],
    )
    title: MarkupText = field(converter=to_markuptext)

    attachments: tuple[tuple[str, AttachmentReference], ...] = field(
        default=(),
        converter=tuple,
        validator=v.deep_iterable(
            member_validator=validate_attachment,
            iterable_validator=v.instance_of(tuple),
        ),
    )
    authors: tuple[NameSpecification, ...] = field(
        default=(),
        converter=into_namespec_tuple,
        on_setattr=[
            setters.convert,
            setters.validate,
            attach_parent,
            update_person_itemids,
            track_modifications,
        ],
    )
    awards: tuple[Award, ...] = field(default=(), converter=_into_award_tuple)
    _editors: tuple[NameSpecification, ...] = field(
        default=(),
        converter=into_namespec_tuple,
        on_setattr=[
            setters.convert,
            setters.validate,
            attach_parent,
            update_person_itemids,
            track_modifications,
        ],
    )
    _errata: tuple[PaperErratum, ...] = field(
        default=(),
        converter=tuple,
        validator=[
            v.deep_iterable(
                member_validator=v.instance_of(PaperErratum),
                iterable_validator=v.instance_of(tuple),
            ),  # necessary because auto_validate_types cannot cover this
            _check_errata_pdf_names,
        ],
    )
    _revisions: tuple[PaperRevision, ...] = field(
        default=(),
        converter=tuple,
        validator=[
            v.deep_iterable(
                member_validator=v.instance_of(PaperRevision),
                iterable_validator=v.instance_of(tuple),
            ),  # necessary because auto_validate_types cannot cover this
            _check_revisions_pdf_names,
        ],
    )
    videos: tuple[VideoReference, ...] = field(
        default=(), converter=tuple
    )  # auto_validate_types covers this, so no validator necessary
    audios: tuple[AudioReference, ...] = field(default=(), converter=tuple)
    urls: tuple[tuple[str, URLReference], ...] = field(
        default=(),
        converter=tuple,
        validator=v.deep_iterable(
            member_validator=validate_url_tuple,
            iterable_validator=v.instance_of(tuple),
        ),  # necessary because auto_validate_types cannot cover this
    )

    abstract: Optional[MarkupText] = field(
        default=None, converter=converters.optional(to_markuptext)
    )
    deletion: Optional[PaperDeletionNotice] = field(
        default=None, validator=v.optional(v.instance_of(PaperDeletionNotice))
    )
    doi: Optional[str] = field(default=None)
    _ingest_date: Optional[str] = field(
        default=None,
        converter=date_to_str,
        validator=v.optional(v.matches_re(constants.RE_ISO_DATE)),
    )
    _journal_issue: Optional[str] = field(default=None, alias="issue")
    _journal_title: Optional[str] = field(default=None, alias="journal")
    language: Optional[str] = field(default=None)
    _month: Optional[str] = field(default=None)
    note: Optional[str] = field(default=None)
    pages: Optional[str] = field(default=None)
    _pdf: Optional[PDFReference] = field(default=None)
    type: PaperType = field(default=PaperType.PAPER, converter=PaperType)

    def __attrs_post_init__(self) -> None:
        for namespec in it.chain(self.authors, self._editors):
            namespec.parent = self

    @type.validator
    def _check_type(self, _: Any, value: PaperType) -> None:
        if value == PaperType.FRONTMATTER:
            raise ValueError(
                "Frontmatter is a separate record; use Volume.create_frontmatter()"
            )

    @id.validator
    def _check_id(self, _: Any, value: str) -> None:
        if not is_valid_item_id(value):
            raise AnthologyInvalidIDError(value, "not a valid paper ID")

    @_pdf.validator
    def _check_pdf(self, _: Any, value: Any) -> None:
        validate_pdf(self, _, value)

    @property
    def bibtype(self) -> str:
        """The BibTeX entry type for this paper."""
        match self.parent.type:
            case VolumeType.JOURNAL:
                return "article"
            case VolumeType.PROCEEDINGS:
                return "inproceedings"
            case _:  # pragma: no cover
                raise ValueError(f"Unknown volume type: {self.parent.type}")

    @property
    def csltype(self) -> str:
        """The [CSL type](https://docs.citationstyles.org/en/stable/specification.html#appendix-iii-types) for this paper."""
        if self.parent.type == VolumeType.JOURNAL:
            return "article-journal"
        # else:
        return "paper-conference"

    @property
    def month(self) -> Optional[str]:
        """The month of publication. Uses the paper's own month if set, otherwise inherited from the parent Volume."""
        if self._month is None:
            return self.parent.month
        return self._month

    @month.setter
    def month(self, value: Optional[str]) -> None:
        self._month = value

    @property
    def editors(self) -> tuple[NameSpecification, ...]:
        """The editors for this paper. Uses the paper's own editor list if set, otherwise inherited from the parent Volume."""
        if self._editors:
            return self._editors
        return self.parent.editors

    @editors.setter
    def editors(self, value: Iterable[NameSpecification]) -> None:
        self._editors = into_namespec_tuple(value)

    @property
    def journal_issue(self) -> Optional[str]:
        """The issue number of this paper. Uses the paper's own issue number if set, otherwise inherited from the parent Volume."""
        if self._journal_issue is None:
            return self.parent.journal_issue
        return self._journal_issue

    @journal_issue.setter
    def journal_issue(self, value: Optional[str]) -> None:
        self._journal_issue = value

    @property
    def journal_title(self) -> Optional[str]:
        """The journal title of this paper. Uses the paper's own journal title if set, otherwise inherited from the parent Volume."""
        if self._journal_title is None:
            return self.parent.journal_title
        return self._journal_title

    @journal_title.setter
    def journal_title(self, value: Optional[str]) -> None:
        self._journal_title = value

    @property
    def errata(self) -> tuple[PaperErratum, ...]:
        """Errata for this paper; can be empty.

        Each erratum's PDF reference has its `name` derived from this paper's `full_id` and the erratum's own `id` -- it is not present in the XML.
        """
        return tuple(
            attrs.evolve(
                erratum,
                pdf=attrs.evolve(erratum.pdf, name=f"{self.full_id}e{erratum.id}"),
            )
            for erratum in self._errata
        )

    @errata.setter
    def errata(self, value: Iterable[PaperErratum]) -> None:
        self._errata = tuple(value)

    @deprecated("Paper.get_editors() is deprecated in favor of Paper.editors")
    def get_editors(self) -> tuple[NameSpecification, ...]:  # pragma: no cover
        return self.editors

    def get_events(self) -> list[Event]:
        """
        Returns:
            A list of events associated with this paper.
        """
        return self.root.events.by_volume(self.parent.full_id_tuple)

    @deprecated("Paper.get_ingest_date() is deprecated in favor of Paper.ingest_date")
    def get_ingest_date(self) -> datetime.date:  # pragma: no cover
        return self.ingest_date

    @deprecated("Paper.get_issue() is deprecated in favor of Paper.journal_issue")
    def get_issue(self) -> Optional[str]:  # pragma: no cover
        return self.journal_issue

    @deprecated("Paper.get_journal_title() is deprecated in favor of Paper.journal_title")
    def get_journal_title(self) -> str:  # pragma: no cover
        return self.journal_title or ""

    def _bibtex_container_fields(self) -> list[tuple[str, SerializableAsBibTeX]]:
        if self.parent.type == VolumeType.JOURNAL:
            return [
                ("journal", self.journal_title),
                ("volume", self.journal_volume),
                ("number", self.journal_issue),
            ]
        return [("booktitle", self.parent.title)]

    @classmethod
    def from_frontmatter_xml(cls, parent: Volume, paper: etree._Element) -> Frontmatter:
        """Compatibility entry point returning a distinct Frontmatter instance."""
        from .frontmatter import Frontmatter

        return Frontmatter.from_xml(parent, paper)

    @classmethod
    def from_xml(cls, parent: Volume, paper: etree._Element) -> Paper | Frontmatter:
        """Instantiates a new paper from its `<paper>` block in the XML.

        This function can also be called with a `<frontmatter>` block, in which case it will just defer to [self.from_frontmatter_xml][acl_anthology.collections.paper.Paper.from_frontmatter_xml].
        """
        if paper.tag == "frontmatter":
            return Paper.from_frontmatter_xml(parent, paper)
        if paper.tag != "paper":
            raise AnthologyXMLError(
                parent.full_id_tuple, str(paper.tag), "expected <paper>"
            )
        # Remainder of this function assumes paper.tag == "paper"
        kwargs: dict[str, Any] = {
            "id": str(paper.get("id")),
            "type": PaperType(paper.get("type", "paper")),
            "parent": parent,
            "authors": [],
            "editors": [],
            "attachments": [],
            "urls": [],
        }
        if (ingest_date := paper.get("ingest-date")) is not None:
            kwargs["ingest_date"] = str(ingest_date)
        for element in paper:
            if isinstance(element, etree._Comment):
                continue  # allow, but ignore comments
            tag = str(element.tag)
            if tag in (
                "bibkey",
                "doi",
                "issue",
                "journal",
                "language",
                "month",
                "note",
                "pages",
            ):
                kwargs[tag] = element.text
            elif tag in ("author", "editor"):
                kwargs[f"{tag}s"].append(NameSpecification.from_xml(element))
            elif tag in ("abstract", "title"):
                kwargs[tag] = MarkupText.from_xml(element)
            elif tag == "attachment":
                type_ = str(element.get("type", ""))
                kwargs["attachments"].append(
                    (type_, AttachmentReference.from_xml(element))
                )
            elif tag == "award":
                if "awards" not in kwargs:
                    kwargs["awards"] = []
                kwargs["awards"].append(Award.from_xml(element))
            elif tag == "erratum":
                if "errata" not in kwargs:
                    kwargs["errata"] = []
                kwargs["errata"].append(PaperErratum.from_xml(element))
            elif tag in ("removed", "retracted"):
                kwargs["deletion"] = PaperDeletionNotice.from_xml(element)
            elif tag == "revision":
                if "revisions" not in kwargs:
                    kwargs["revisions"] = []
                kwargs["revisions"].append(PaperRevision.from_xml(element))
            elif tag == "pdf":
                kwargs["pdf"] = PDFReference.from_xml(element)
            elif tag == "url":
                type_ = str(element.get("type", ""))
                kwargs["urls"].append((type_, URLReference.from_xml(element)))
            elif tag == "video":
                if "videos" not in kwargs:
                    kwargs["videos"] = []
                kwargs["videos"].append(VideoReference.from_xml(element))
            elif tag == "audio":
                kwargs.setdefault("audios", []).append(AudioReference.from_xml(element))
            elif tag == ("mrf"):
                # consider an attachment of type "mrf"
                kwargs["attachments"].append(
                    ("mrf", AttachmentReference.from_xml(element))
                )
            else:
                raise AnthologyXMLError(
                    parent.full_id_tuple, tag, "unsupported element for <paper>"
                )
        return cls(**kwargs)

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this paper as a `<paper>` block in the Anthology XML format.

        Raises:
            ValueError: If 'bibkey' is set to [`constants.NO_BIBKEY`][acl_anthology.constants.NO_BIBKEY].
        """
        if self.bibkey == constants.NO_BIBKEY:  # pragma: no cover
            raise ValueError("Cannot serialize a Paper without bibkey")
        paper = etree.Element("paper", attrib={"id": self.id})
        if self._ingest_date is not None:
            paper.set("ingest-date", self._ingest_date)
        if self.type != PaperType.PAPER:
            paper.set("type", self.type.value)
        paper.append(etree.Comment(self.web_url))
        paper.append(self.title.to_xml("title"))
        for name_spec in self.authors:
            paper.append(name_spec.to_xml("author"))
        for name_spec in self._editors:
            paper.append(name_spec.to_xml("editor"))
        if self.pages is not None:
            paper.append(E.pages(self.pages))
        if self.abstract is not None:
            paper.append(self.abstract.to_xml("abstract"))
        if self._pdf is not None:
            paper.append(self._pdf.to_xml())
        for type_, url in self.urls:
            elem = url.to_xml("url")
            if type_:
                elem.set("type", type_)
            paper.append(elem)
        for erratum in self._errata:
            paper.append(erratum.to_xml())
        for revision in self._revisions:
            paper.append(revision.to_xml())
        if self.doi is not None:
            paper.append(E.doi(self.doi))
        if self._journal_issue is not None:
            paper.append(E.issue(self._journal_issue))
        if self._journal_title is not None:
            paper.append(E.journal(self._journal_title))
        for tag in ("language", "month", "note"):
            if hasattr(self, f"_{tag}"):
                value = getattr(self, f"_{tag}")
            else:
                value = getattr(self, tag)
            if value is not None:
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
        for audio in self.audios:
            paper.append(audio.to_xml())
        for award in self.awards:
            paper.append(award.to_xml())
        if self.deletion is not None:
            paper.append(self.deletion.to_xml())
        paper.append(E.bibkey(self.bibkey))
        return paper
