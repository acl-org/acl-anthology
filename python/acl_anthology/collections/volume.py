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

import datetime
from attrs import define, field, validators
from lxml import etree
from lxml.builder import E
from typing import Any, Iterator, Optional, cast, TYPE_CHECKING
import sys

from .. import constants
from ..config import config
from ..containers import SlottedDict
from ..exceptions import AnthologyDuplicateIDError, AnthologyInvalidIDError
from ..files import PDFReference
from ..people import NameSpecification
from ..text import MarkupText
from ..venues import Venue
from ..utils.attrs import auto_validate_types, date_to_str, int_to_str
from ..utils.ids import build_id, is_valid_item_id, AnthologyIDTuple
from .paper import Paper
from .types import VolumeType

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..sigs import SIG
    from . import Collection, Event


@define(field_transformer=auto_validate_types)
class Volume(SlottedDict[Paper]):
    """A publication volume.

    Provides dictionary-like functionality mapping paper IDs to [Paper][acl_anthology.collections.paper.Paper] objects in the volume.

    Info:
        To create a new volume, use [`Collection.create_volume()`][acl_anthology.collections.collection.Collection.create_volume].

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

    id: str = field(converter=int_to_str)
    parent: Collection = field(repr=False, eq=False)
    type: VolumeType = field(repr=False, converter=VolumeType)
    title: MarkupText = field(alias="booktitle")
    year: str = field(
        converter=int_to_str, validator=validators.matches_re(r"^[0-9]{4}$")
    )

    editors: list[NameSpecification] = field(factory=list)
    venue_ids: list[str] = field(factory=list)

    address: Optional[str] = field(default=None, repr=False)
    doi: Optional[str] = field(default=None, repr=False)
    ingest_date: Optional[str] = field(
        default=None,
        repr=False,
        converter=date_to_str,
        validator=validators.optional(validators.matches_re(constants.RE_ISO_DATE)),
    )
    isbn: Optional[str] = field(default=None, repr=False)
    journal_issue: Optional[str] = field(default=None, repr=False, converter=int_to_str)
    journal_volume: Optional[str] = field(default=None, repr=False, converter=int_to_str)
    journal_title: Optional[str] = field(default=None, repr=False)
    month: Optional[str] = field(default=None, repr=False)  # TODO: validate/convert?
    pdf: Optional[PDFReference] = field(default=None, repr=False)
    publisher: Optional[str] = field(default=None, repr=False)
    shorttitle: Optional[MarkupText] = field(
        default=None, alias="shortbooktitle", repr=False
    )

    @id.validator
    def _check_id(self, _: Any, value: str) -> None:
        if not is_valid_item_id(value):
            raise AnthologyInvalidIDError(value, "Not a valid Volume ID")

    @property
    def frontmatter(self) -> Paper | None:
        """Returns the volume's frontmatter, if any."""
        return self.data.get(constants.FRONTMATTER_ID)

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
    def has_abstracts(self) -> bool:
        """True if at least one paper in this volume has an abstract."""
        return any(paper.abstract is not None for paper in self.data.values())

    @property
    def has_frontmatter(self) -> bool:
        """True if this volume has frontmatter."""
        return constants.FRONTMATTER_ID in self.data

    @property
    def is_workshop(self) -> bool:
        """True if this volume is a workshop proceedings."""
        # Venue "ws" is inconsistently marked, so we also look at the title
        return "ws" in self.venue_ids or "workshop" in str(self.title).lower()

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.parent.parent.parent

    @property
    def venue_acronym(self) -> str:
        """The acronym of the venue(s) associated with this volume.  In case of multiple venues, this will be a concatenation of the individual venue acronyms."""
        return "-".join(venue.acronym for venue in self.venues() if venue.id != "ws")

    @property
    def web_url(self) -> str:
        """The URL of this volume's landing page on the ACL Anthology website."""
        return cast(str, config["volume_page_template"]).format(self.full_id)

    def get_events(self) -> list[Event]:
        """
        Returns:
            A list of events associated with this volume.
        """
        return self.root.events.by_volume(self.full_id_tuple)

    def get_ingest_date(self) -> datetime.date:
        """
        Returns:
            The date when this volume was added to the Anthology. If not set, will return [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE] instead.
        """
        if self.ingest_date is None:
            return constants.UNKNOWN_INGEST_DATE
        return datetime.date.fromisoformat(self.ingest_date)

    def get_journal_title(self) -> str:
        """
        Returns:
            The journal title for this volume, fetching this information from the associated venue if it isn't explicit set.

        Raises:
            TypeError: If this volume doesn't represent a journal.
            ValueError: If the journal title isn't explicitly set, but there isn't exactly one venue associated with this volume.
        """
        if self.type != VolumeType.JOURNAL:
            raise TypeError("Volume is not a journal")
        if self.journal_title is not None:
            return self.journal_title
        # If journal-title isn't explicit set, we fetch it from the associated venue
        if len(self.venue_ids) != 1:
            raise ValueError(
                "Journal volume must have exactly one venue or an explicit <journal-title>"
            )
        return self.root.venues[self.venue_ids[0]].name

    def get_sigs(self) -> list[SIG]:
        """
        Returns:
            A list of SIGs associated with this volume.
        """
        return self.root.sigs.by_volume(self.full_id_tuple)

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

    def to_bibtex(self) -> str:
        """Generate a BibTeX entry for this volume.

        Returns:
            The BibTeX entry for this volume as a formatted string.  Currently, this is simply the frontmatter's BibTeX.

        Raises:
            Exception: If this volume has no frontmatter.
        """
        if self.frontmatter is None:  # pragma: no cover
            raise Exception("Cannot generate BibTeX for volume without frontmatter.")
        return self.frontmatter.to_bibtex()

    def generate_paper_id(self) -> str:
        """Generate a paper ID that is not yet taken in this volume.

        This will always generate a numeric ID that is one higher than the currently highest numeric ID in this volume.  If the volume is empty, it will return "1".

        Returns:
            A paper ID not yet taken in this volume.
        """
        numeric_keys = sorted(int(n) for n in self.data.keys() if n.isnumeric())
        return "1" if not numeric_keys else str(numeric_keys[-1] + 1)

    def create_paper(
        self,
        title: MarkupText,
        id: Optional[str] = None,
        bibkey: str = constants.NO_BIBKEY,
        **kwargs: Any,
    ) -> Paper:
        """Create a new [Paper][acl_anthology.collections.paper.Paper] object in this volume.

        Parameters:
            title: The title of the new paper.
            id: The ID of the new paper (optional); if None, will generate the next-highest numeric ID that doesn't already exist in this volume.
            bibkey: The citation key of the new paper (optional); defaults to [`constants.NO_BIBKEY`][acl_anthology.constants.NO_BIBKEY], in which case a non-clashing citation key will be automatically generated (recommended!).
            **kwargs: Any valid list or optional attribute of [Paper][acl_anthology.collections.paper.Paper].

        Returns:
            The created [Paper][acl_anthology.collections.paper.Paper] object.

        Raises:
            AnthologyDuplicateIDError: If a paper with the given ID or bibkey already exists.
        """
        if id is None:
            id = self.generate_paper_id()
        elif id in self.data:
            raise AnthologyDuplicateIDError(
                id, "Paper ID already exists in volume {self.full_id}"
            )

        kwargs["parent"] = self
        paper = Paper(id=id, bibkey=bibkey, title=title, **kwargs)

        # Necessary because on_setattr is not called during initialization:
        paper.bibkey = bibkey  # triggers bibkey generating (if necessary) & indexing

        # For convenience, if authors/editors were given, we add them to the index here
        if paper.authors:
            self.root.people._add_to_index(paper.authors, paper.full_id_tuple)
        if paper.editors:
            self.root.people._add_to_index(paper.editors, paper.full_id_tuple)

        self.data[id] = paper
        return paper

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
            "id": str(volume.get("id")),
            "type": VolumeType(volume.get("type")),
            "parent": parent,
            "editors": [],
            "venue_ids": [],
        }
        if (ingest_date := volume.get("ingest-date")) is not None:
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
            else:  # pragma: no cover
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
            volume.set("ingest-date", self.ingest_date)
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
