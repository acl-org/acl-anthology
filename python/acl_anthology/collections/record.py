# Copyright 2026 ACL Anthology
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

from abc import abstractmethod
import datetime
from typing import Any, Iterable, Optional, TYPE_CHECKING, cast

import attrs
from attrs import define, field, validators as v
import langcodes
from lxml import etree
from lxml.builder import E

from .item import CollectionItem
from .types import MediaType, PaperDeletionType, PaperType, VolumeType
from .. import constants
from ..config import config
from ..files import (
    AttachmentReference,
    AudioReference,
    PDFReference,
    PDFThumbnailReference,
    URLReference,
    VideoReference,
)
from ..utils.attrs import (
    ConvertableIntoDate,
    attach_custom_repr,
    auto_validate_types,
    date_to_str,
)
from ..utils.citation import citeproc_render_html, render_acl_citation
from ..utils.ids import AnthologyIDTuple
from ..utils.latex import make_bibtex_entry

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..people import NameSpecification
    from ..text import MarkupText
    from ..utils.latex import SerializableAsBibTeX
    from .collection import Collection
    from .event import Event
    from .paper import Award, PaperErratum, PaperRevision
    from .volume import Volume


@attach_custom_repr
@define(field_transformer=auto_validate_types, frozen=True)
class DeletionNotice:
    """A retraction or removal of a citable record."""

    type: PaperDeletionType = field(converter=PaperDeletionType)
    note: Optional[str] = field()
    date: str = field(
        default=None, converter=date_to_str, validator=v.matches_re(constants.RE_ISO_DATE)
    )

    @classmethod
    def from_xml(cls, element: etree._Element) -> DeletionNotice:
        return cls(
            type=PaperDeletionType(str(element.tag)),
            note=element.text or None,
            date=str(element.get("date")),
        )

    def to_xml(self) -> etree._Element:
        return cast(
            etree._Element,
            getattr(E, self.type.value)(self.note or "", date=self.date),
        )


def update_bibkey(item: Record, _: attrs.Attribute[Any], value: str) -> str:
    return item.root.collections.bibkeys._index_record(value, item)


def validate_attachment(_: Record, __: Any, value: Any) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not isinstance(value[0], str)
        or not isinstance(value[1], AttachmentReference)
    ):
        raise TypeError(
            f"'attachments' needs tuples of (str, AttachmentReference) (got {value!r})"
        )


class Record(CollectionItem):
    """Shared identity, metadata views, and citation behavior for volume children.

    Concrete record types own their fields and XML serializers. This class
    does not make media or frontmatter instances of Paper.
    """

    __slots__ = ()
    parent: Volume

    @property
    @abstractmethod
    def bibkey(self) -> str:
        """The record's unique citation key."""

    @bibkey.setter
    @abstractmethod
    def bibkey(self, value: str) -> None: ...

    @property
    @abstractmethod
    def _ingest_date(self) -> Optional[str]: ...

    @_ingest_date.setter
    @abstractmethod
    def _ingest_date(self, value: Optional[str]) -> None: ...

    @property
    @abstractmethod
    def type(self) -> PaperType | MediaType:
        """The concrete record's type discriminator."""

    @property
    def collection(self) -> Collection:
        return self.parent.parent

    @property
    def root(self) -> Anthology:
        return self.parent.parent.parent.parent

    @property
    def volume_id(self) -> str:
        return self.parent.id

    @property
    def full_id_tuple(self) -> AnthologyIDTuple:
        return (self.parent.parent.id, self.parent.id, self.id)

    @property
    def web_url(self) -> str:
        return cast(str, config["paper_page_template"]).format(self.full_id)

    @property
    def authors(self) -> tuple[NameSpecification, ...]:
        return ()

    @property
    def editors(self) -> tuple[NameSpecification, ...]:
        return self.parent.editors

    @property
    def abstract(self) -> Optional[MarkupText]:
        return None

    @property
    def deletion(self) -> Optional[DeletionNotice]:
        return None

    @property
    def is_deleted(self) -> bool:
        return self.deletion is not None

    @property
    def doi(self) -> Optional[str]:
        return None

    @property
    def pages(self) -> Optional[str]:
        return None

    @property
    def language(self) -> Optional[str]:
        return None

    @property
    def language_name(self) -> Optional[str]:
        return (
            langcodes.Language.get(self.language).display_name()
            if self.language
            else None
        )

    @property
    def note(self) -> Optional[str]:
        return None

    @property
    def attachments(self) -> tuple[tuple[str, AttachmentReference], ...]:
        return ()

    @property
    def urls(self) -> tuple[tuple[str, URLReference], ...]:
        return ()

    @property
    def videos(self) -> tuple[VideoReference, ...]:
        return ()

    @property
    def audios(self) -> tuple[AudioReference, ...]:
        return ()

    @property
    def pdf(self) -> Optional[PDFReference]:
        return None

    @property
    def thumbnail(self) -> Optional[PDFThumbnailReference]:
        return None

    @property
    def awards(self) -> tuple[Award, ...]:
        return ()

    @property
    def errata(self) -> tuple[PaperErratum, ...]:
        return ()

    @property
    def revisions(self) -> tuple[PaperRevision, ...]:
        return ()

    @property
    def address(self) -> Optional[str]:
        return self.parent.address

    @property
    def publisher(self) -> Optional[str]:
        return self.parent.publisher

    @property
    def year(self) -> str:
        return self.parent.year

    @property
    def month(self) -> Optional[str]:
        return self.parent.month

    @property
    def journal_title(self) -> Optional[str]:
        return self.parent.journal_title

    @property
    def journal_volume(self) -> Optional[str]:
        return self.parent.journal_volume

    @property
    def journal_issue(self) -> Optional[str]:
        return self.parent.journal_issue

    @property
    def venue_ids(self) -> tuple[str, ...]:
        return self.parent.venue_ids

    @property
    def ingest_date(self) -> datetime.date:
        if self._ingest_date is None:
            return self.parent.ingest_date
        return datetime.date.fromisoformat(self._ingest_date)

    @ingest_date.setter
    def ingest_date(self, value: ConvertableIntoDate) -> None:
        self._ingest_date = date_to_str(value)

    @property
    @abstractmethod
    def bibtype(self) -> str:
        """The BibTeX entry type for this concrete record."""

    @property
    @abstractmethod
    def csltype(self) -> str:
        """The CSL entry type for this concrete record."""

    def get_events(self) -> list[Event]:
        """Return the events associated with this record's volume."""
        return self.root.events.by_volume(self.parent.full_id_tuple)

    @property
    def citation_authors(self) -> tuple[NameSpecification, ...]:
        return self.authors

    def _citeproc_fields(self) -> dict[str, Any]:
        if self.parent.type == VolumeType.JOURNAL:
            return {
                "container-title": self.journal_title,
                "volume": self.journal_volume,
                "issue": self.journal_issue,
            }
        return {"container-title": self.parent.title.as_text()}

    @property
    def citeproc_dict(self) -> dict[str, Any]:
        """Return CSL-JSON metadata for this concrete bibliographic record."""
        data: dict[str, Any] = {
            "id": self.bibkey,
            "title": self.title.as_text(),
            "type": self.csltype,
            "author": [spec.citeproc_dict for spec in self.citation_authors],
            "editor": [spec.citeproc_dict for spec in self.editors],
            "publisher": self.publisher,
            "publisher-place": self.address,
            "issued": {"date-parts": [[self.year]]},
            "URL": self.web_url,
            "DOI": self.doi,
            "ISBN": self.parent.isbn,
            "page": self.pages,
            **self._citeproc_fields(),
        }
        return {key: value for key, value in data.items() if value is not None}

    def refresh_bibkey(self) -> str:
        """Generate and index a unique citation key for this record."""
        self.bibkey = constants.NO_BIBKEY
        return self.bibkey

    def _bibtex_container_fields(self) -> list[tuple[str, SerializableAsBibTeX]]:
        return []

    def _bibtex_note(self) -> Optional[str]:
        return self.note

    def to_bibtex(self, with_abstract: bool = False) -> str:
        """Generate a BibTeX entry, optionally including the abstract."""
        if self.bibkey == constants.NO_BIBKEY:
            raise ValueError("Cannot generate BibTeX entry without bibkey")
        fields: list[tuple[str, SerializableAsBibTeX]] = [
            ("title", self.title),
            ("author", self.authors),
            ("editor", self.editors),
            *self._bibtex_container_fields(),
            ("month", self.month),
            ("year", self.year),
            ("address", self.address),
            ("publisher", self.publisher),
            ("note", self._bibtex_note()),
            ("url", self.web_url),
            ("doi", self.doi),
            ("pages", self.pages),
            ("language", self.language),
            ("ISBN", self.parent.isbn),
        ]
        if with_abstract and self.abstract is not None:
            fields.append(("abstract", self.abstract))
        return make_bibtex_entry(self.bibtype, self.bibkey, fields)

    def to_citation(self, style: Optional[str] = None) -> str:
        """Render an ACL citation, or use the supplied CSL style file."""
        if style is None:
            return render_acl_citation(self)
        return citeproc_render_html(self.citeproc_dict, style)

    def to_markdown_citation(self) -> str:
        """Generate the brief, linked Markdown citation used in Anthology lists."""
        specs = self.citation_authors
        if not specs:
            name = ""
        elif len(specs) == 1:
            name = specs[0].last
        elif len(specs) == 2:
            name = f"{specs[0].last} & {specs[1].last}"
        else:
            name = f"{specs[0].last} et al."
        venue_year = (
            self.year
            if self.parent.venue_acronym == "WS"
            else f"{self.parent.venue_acronym} {self.year}"
        )
        suffix = f"{name}, {venue_year}" if name else venue_year
        return f"[{self.title.as_text()}]({self.web_url}) ({suffix})"


class PDFRecord(Record):
    """Shared PDF/revision access for papers and frontmatter, not media."""

    __slots__ = ()

    @property
    @abstractmethod
    def _pdf(self) -> Optional[PDFReference]: ...

    @_pdf.setter
    @abstractmethod
    def _pdf(self, value: Optional[PDFReference]) -> None: ...

    @property
    @abstractmethod
    def _revisions(self) -> tuple[PaperRevision, ...]: ...

    @_revisions.setter
    @abstractmethod
    def _revisions(self, value: tuple[PaperRevision, ...]) -> None: ...

    @property
    def pdf(self) -> Optional[PDFReference]:
        """Return the canonical PDF reference with its persistent filename."""
        return attrs.evolve(self._pdf, name=self.full_id) if self._pdf else None

    @pdf.setter
    def pdf(self, value: Optional[PDFReference]) -> None:
        self._pdf = value

    @property
    def thumbnail(self) -> Optional[PDFThumbnailReference]:
        """Return a PDF thumbnail reference when a canonical PDF exists."""
        return PDFThumbnailReference(self.full_id) if self._pdf else None

    @property
    def revisions(self) -> tuple[PaperRevision, ...]:
        """Return PDF revisions with filenames derived from this record's ID."""
        return tuple(
            attrs.evolve(
                revision,
                pdf=attrs.evolve(revision.pdf, name=f"{self.full_id}v{revision.id}"),
            )
            for revision in self._revisions
        )

    @revisions.setter
    def revisions(self, value: Iterable[PaperRevision]) -> None:
        self._revisions = tuple(value)
