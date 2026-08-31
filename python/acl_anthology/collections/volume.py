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

import datetime
import attrs
from attrs import define, field, converters, setters, validators
from lxml import etree
from lxml.builder import E
from typing import Any, Iterator, Optional, cast, TYPE_CHECKING
import sys

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

from .. import constants
from ..config import config
from ..containers import SlottedDict
from ..exceptions import AnthologyDuplicateIDError, AnthologyInvalidIDError
from ..files import PDFReference, URLReference, validate_url_tuple
from ..people import NameSpecification
from ..text import MarkupText, to_markuptext
from ..venues import Venue
from ..utils.attrs import (
    attach_custom_repr,
    attach_parent,
    auto_validate_types,
    date_to_str,
    int_to_str,
    into_namespec_tuple,
    into_str_tuple,
    track_modifications,
    ConvertableIntoDate,
)
from ..utils.ids import build_id, is_valid_item_id, AnthologyIDTuple
from .event import Event
from .paper import (
    Paper,
    _update_person_itemids,
)  # Note: importing a private function from Paper will be unnecessary after CollectionItem refactoring
from .types import EventLink, VolumeType

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..people import Person
    from ..sigs import SIG
    from . import Collection, Event


def _update_sigs(
    volume: Volume, attr: attrs.Attribute[Any], value: tuple[str, ...]
) -> tuple[str, ...]:
    """Update objects depending on a volume's `sig_ids`.

    This will:
    - Update `SIG.item_ids` for SIGs linked to or unlinked from a volume

    Intended to be called from `on_setattr` of an [attrs.field][].
    """
    sig_index = volume.root.sigs
    old_value = getattr(volume, attr.name)
    for sig in set(old_value) - set(value):
        # SIGs that are being removed from this volume
        if sig_index.is_data_loaded:
            sig_index[sig].item_ids.discard(volume.full_id_tuple)

    for sig in set(value) - set(old_value):
        # SIGs that are being added to this volume
        if sig_index.is_data_loaded:
            try:
                # Update SIG.item_ids
                sig_index[sig].item_ids.add(volume.full_id_tuple)
            except KeyError:
                raise ValueError(f"Tried setting SIG that doesn't exist: {sig}")
    return value


def _update_venues(
    volume: Volume, attr: attrs.Attribute[Any], value: tuple[str, ...]
) -> tuple[str, ...]:
    """Update objects depending on a volume's `venue_ids`.

    This will:
    - Update `Venue.item_ids` for venues linked to or unlinked from a volume
    - Create or remove implicitly created events
    - Update the EventIndex and any connected `Event.colocated_ids`

    Intended to be called from `on_setattr` of an [attrs.field][].
    """
    venue_index = volume.root.venues
    event_index = volume.root.events
    old_value = getattr(volume, attr.name)
    for venue in set(old_value) - set(value):
        # Venues that are being removed from this volume
        if venue_index.is_data_loaded:
            venue_index[venue].item_ids.discard(volume.full_id_tuple)
        if (
            event_index.is_data_loaded
            and (
                implicit_event := event_index.get_or_create_implicit_event(
                    volume, venue, create=False
                )
            )
            is not None
            and (
                implicit_event.colocated_ids.get(volume.full_id_tuple)
                == EventLink.INFERRED
            )
        ):
            # Update Event.colocated_ids
            del implicit_event.colocated_ids[volume.full_id_tuple]
            # Update EventIndex.reverse
            event_index.reverse[volume.full_id_tuple].discard(implicit_event.id)
            # Check if implicit event can be deleted
            if not implicit_event.colocated_ids:
                del event_index[implicit_event.id]

    for venue in set(value) - set(old_value):
        # Venues that are being added to this volume
        if venue_index.is_data_loaded:
            try:
                # Update Venue.item_ids
                venue_index[venue].item_ids.add(volume.full_id_tuple)
            except KeyError:
                raise ValueError(f"Tried setting venue that doesn't exist: {venue}")
        if event_index.is_data_loaded:
            # Update Event.colocated_ids
            implicit_event = cast(
                Event,
                event_index.get_or_create_implicit_event(volume, venue, create=True),
            )
            implicit_event.add_colocated(volume.full_id_tuple, EventLink.INFERRED)
            # Update EventIndex.reverse
            event_index.reverse[volume.full_id_tuple].add(implicit_event.id)
    return value


@attach_custom_repr
@define(
    field_transformer=auto_validate_types,
    on_setattr=[setters.convert, setters.validate, track_modifications],
)
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

    Attributes: Tuple Attributes:
        editors: Names of editors associated with this volume.
        sig_ids: List of SIG IDs associated with this volume. See also [sigs][acl_anthology.collections.volume.Volume.sigs]/[add_sig][acl_anthology.collections.volume.Volume.add_sig]/[remove_sig][acl_anthology.collections.volume.Volume.remove_sig].
        venue_ids: List of venue IDs associated with this volume. See also [venues][acl_anthology.collections.volume.Volume.venues]/[add_venue][acl_anthology.collections.volume.Volume.add_venue]/[remove_venue][acl_anthology.collections.volume.Volume.remove_venue].
        urls: Links to external, non-locally-hosted resources associated with this volume (e.g. supplementary materials), as tuples of `(type_of_link, reference)`; can be empty.

    Attributes: Optional Attributes:
        address: The publisher's address for this volume.
        doi: The DOI for the volume.
        isbn: The ISBN for the volume.
        journal_issue: The journal's issue number, if this volume belongs to a journal.
        journal_volume: The journal's volume number, if this volume belongs to a journal.
        journal_title: The journal's title (without volume/issue/subtitle), if this volume belongs to a journal.
        month: The month of publication.
        pdf: A reference to the volume's PDF.
        publisher: The volume's publisher.
        shorttitle: A shortened form of the title. (Aliased to `shortbooktitle` for initialization.)
    """

    id: str = field(converter=int_to_str)  # validator defined below
    parent: Collection = field(repr=False, eq=False)
    type: VolumeType = field(converter=VolumeType)
    title: MarkupText = field(alias="booktitle", converter=to_markuptext)
    year: str = field(
        converter=int_to_str, validator=validators.matches_re(r"^[0-9]{4}$")
    )

    editors: tuple[NameSpecification, ...] = field(
        default=(),
        converter=into_namespec_tuple,
        on_setattr=[
            setters.convert,
            setters.validate,
            attach_parent,
            _update_person_itemids,
            track_modifications,
        ],
    )
    sig_ids: tuple[str, ...] = field(
        default=(),
        converter=into_str_tuple,
        on_setattr=[
            setters.convert,
            setters.validate,
            _update_sigs,
            track_modifications,
        ],
    )
    venue_ids: tuple[str, ...] = field(
        default=(),
        converter=into_str_tuple,
        on_setattr=[
            setters.convert,
            setters.validate,
            _update_venues,
            track_modifications,
        ],
    )
    urls: tuple[tuple[str, URLReference], ...] = field(
        default=(),
        converter=tuple,
        validator=validators.deep_iterable(
            member_validator=validate_url_tuple,
            iterable_validator=validators.instance_of(tuple),
        ),  # necessary because auto_validate_types cannot cover this
    )

    address: Optional[str] = field(default=None)
    doi: Optional[str] = field(default=None)
    _ingest_date: Optional[str] = field(
        default=None,
        converter=date_to_str,
        validator=validators.optional(validators.matches_re(constants.RE_ISO_DATE)),
    )
    isbn: Optional[str] = field(default=None)
    journal_issue: Optional[str] = field(default=None, converter=int_to_str)
    journal_volume: Optional[str] = field(default=None, converter=int_to_str)
    _journal_title: Optional[str] = field(default=None)
    month: Optional[str] = field(default=None)  # TODO: validate/convert?
    _pdf: Optional[PDFReference] = field(default=None)
    publisher: Optional[str] = field(default=None)
    shorttitle: Optional[MarkupText] = field(
        default=None,
        alias="shortbooktitle",
        repr=False,
        converter=converters.optional(to_markuptext),
    )

    def __attrs_post_init__(self) -> None:
        for namespec in self.editors:
            namespec.parent = self
        if self.root.venues.is_data_loaded:
            for venue in self.venue_ids:
                self.root.venues[venue].item_ids.add(self.full_id_tuple)

        if (
            self.type == VolumeType.JOURNAL
            and self._journal_title is None
            and len(self.venue_ids) != 1
        ):
            raise ValueError(
                "Journal volume must have exactly one venue or an explicit <journal-title>"
            )  # pragma: no cover

    @id.validator
    def _check_id(self, _: Any, value: str) -> None:
        if not is_valid_item_id(value):
            raise AnthologyInvalidIDError(value, "Not a valid Volume ID")

    @_pdf.validator
    def _check_pdf(self, _: Any, value: Any) -> None:
        # Adding this validator disables auto_validate_types for this field, so
        # we need to check the type explicitly here, too.
        if value is None:
            return
        if not isinstance(value, PDFReference):
            raise TypeError(
                f"'pdf' must be Optional[{PDFReference!r}] (got '{value!r}' that is a {type(value)!r})"
            )
        # <pdf> must be a local file reference according to the schema
        if not value.is_local:
            raise ValueError(
                f"'pdf' of a Volume must be a local file reference (got '{value}')"
            )
        # If a name is given, it must match what would be derived automatically
        # (an empty name, e.g. from PDFReference.from_xml(), is always fine)
        if value.name and value.name != self.full_id:
            raise ValueError(
                f"PDF reference name {value.name!r} does not match this volume's full_id {self.full_id!r}"
            )

    @property
    def pdf(self) -> Optional[PDFReference]:
        """A reference to the volume's PDF.

        `<pdf>` always refers to a local file, so the reference's `name` is derived from this volume's `full_id` rather than stored -- it is not present in the XML.
        """
        if self._pdf is None:
            return None
        return attrs.evolve(self._pdf, name=self.full_id)

    @pdf.setter
    def pdf(self, value: Optional[PDFReference]) -> None:
        self._pdf = value

    @property
    def frontmatter(self) -> Paper | None:
        """Returns the volume's frontmatter, if any."""
        return self.data.get(constants.FRONTMATTER_ID)

    @property
    def collection(self) -> Collection:
        """The collection this volume belongs to."""
        return self.parent

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

    @property
    def namespecs(self) -> tuple[NameSpecification, ...]:
        """All name specifications on this volume."""
        return self.editors

    @property
    def ingest_date(self) -> datetime.date:
        """The date when this volume was added to the Anthology.  If not set explicitly, will use [constants.UNKNOWN_INGEST_DATE][acl_anthology.constants.UNKNOWN_INGEST_DATE] instead."""
        if self._ingest_date is None:
            return constants.UNKNOWN_INGEST_DATE
        return datetime.date.fromisoformat(self._ingest_date)

    @ingest_date.setter
    def ingest_date(self, value: ConvertableIntoDate) -> None:
        self._ingest_date = date_to_str(value)

    @property
    def journal_title(self) -> Optional[str]:
        """The journal title for this volume. Fetched from the associated venue if not explicitly set."""
        if self.type != VolumeType.JOURNAL:
            return None
        if self._journal_title is not None:
            return self._journal_title
        return self.root.venues[self.venue_ids[0]].name

    @journal_title.setter
    def journal_title(self, value: Optional[str]) -> None:
        self._journal_title = value

    def get_events(self) -> list[Event]:
        """
        Returns:
            A list of events associated with this volume.
        """
        return self.root.events.by_volume(self.full_id_tuple)

    @deprecated("Volume.get_ingest_date() is deprecated in favor of Volume.ingest_date")
    def get_ingest_date(self) -> datetime.date:  # pragma: no cover
        return self.ingest_date

    @deprecated(
        "Volume.get_journal_title() is deprecated in favor of Volume.journal_title"
    )
    def get_journal_title(self) -> str:  # pragma: no cover
        return self.journal_title or ""

    def get_namespec_for(self, person: Person) -> NameSpecification:
        """Find the NameSpecification on this volume that refers to a given Person.

        Arguments:
            person: A person that is an editor on this volume.

        Returns:
            The NameSpecification that resolves to the given Person.

        Raises:
            ValueError: If none of the editors resolve to the given Person.
        """
        for namespec in self.namespecs:
            if namespec.resolve() is person:
                return namespec
        raise ValueError(f"No NameSpecification on {self.full_id} resolves to {person}")

    def get_sigs(self) -> list[SIG]:
        return self.sigs()

    def papers(self) -> Iterator[Paper]:
        """An iterator over all Paper objects in this volume."""
        yield from self.data.values()

    def add_sig(self, sig: str | SIG) -> None:
        """Associate a SIG with this volume.

        If the SIG is already associated with this volume, this will do nothing.

        Arguments:
            sig: A SIG object, or a string representing a SIG ID.

        Raises:
            ValueError: If a string was given, but the SIG does not exist.
        """
        if isinstance(sig, str):
            sig_id = sig
            if sig_id not in self.root.sigs:
                raise ValueError(f"SIG doesn't exist: '{sig_id}'")
        else:
            sig_id = sig.id
        if sig_id in self.sig_ids:
            return
        self.sig_ids += (sig_id,)

    def remove_sig(self, sig: str | SIG) -> None:
        """Remove a SIG association from this volume.

        If the SIG is not associated with this volume, this will do nothing.

        Arguments:
            sig: A SIG object, or a string representing a SIG ID.
        """
        sig_id = sig if isinstance(sig, str) else sig.id
        if sig_id in self.sig_ids:
            self.sig_ids = tuple(x for x in self.sig_ids if x != sig_id)

    def sigs(self) -> list[SIG]:
        """
        Returns:
            A list of SIGs associated with this volume.
        """
        try:
            return [self.root.sigs[sig] for sig in self.sig_ids]
        except KeyError as exc:  # pragma: no cover
            exc.add_note(
                f"Most likely, SIG ID '{exc.args[0]}' is not defined in sigs.json"
            )
            raise exc

    def add_venue(self, venue: str | Venue) -> None:
        """Associate a venue with this volume.

        If the venue is already associated with this volume, this will do nothing.

        Arguments:
            venue: A Venue object, or a string representing a venue ID.

        Raises:
            ValueError: If a string was given, but the venue does not exist.
        """
        if isinstance(venue, str):
            venue_id = venue
            if venue_id not in self.root.venues:
                raise ValueError(f"Venue doesn't exist: '{venue_id}'")
        else:
            venue_id = venue.id
        if venue_id in self.venue_ids:
            return
        self.venue_ids += (venue_id,)

    def remove_venue(self, venue: str | Venue) -> None:
        """Remove a venue association from this volume.

        If the venue is not associated with this volume, this will do nothing.

        Arguments:
            venue: A Venue object, or a string representing a venue ID.
        """
        venue_id = venue.id if isinstance(venue, Venue) else venue
        if venue_id in self.venue_ids:
            self.venue_ids = tuple(x for x in self.venue_ids if x != venue_id)

    def venues(self) -> list[Venue]:
        """A list of venues associated with this volume."""
        try:
            return [self.root.venues[vid] for vid in self.venue_ids]
        except KeyError as exc:  # pragma: no cover
            exc.add_note(
                f"Most likely, venue ID '{exc.args[0]}' is not defined in venues.json"
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
        title: MarkupText | str,
        id: Optional[str] = None,
        bibkey: str = constants.NO_BIBKEY,
        **kwargs: Any,
    ) -> Paper:
        """Create a new [Paper][acl_anthology.collections.paper.Paper] object in this volume.

        Parameters:
            title: The title of the new paper.  If given as a string, it will be [heuristically parsed for markup][acl_anthology.text.markuptext.MarkupText.from_].
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
        paper = Paper(
            id=id,
            bibkey=bibkey,
            title=title,
            **kwargs,
        )

        # Necessary because on_setattr is not called during initialization:
        paper.bibkey = bibkey  # triggers bibkey generating (if necessary) & indexing

        # If authors/editors were given, we fill in their ID & add them to the index
        if paper.authors:
            for namespec in paper.authors:
                namespec.normalize(skip_setter=True)
                self.root.people.ingest_namespec(namespec)
            self.root.people._add_to_index(paper.authors, paper.full_id_tuple)
        if paper.editors:
            for namespec in paper.editors:
                namespec.normalize(skip_setter=True)
                self.root.people.ingest_namespec(namespec)
            self.root.people._add_to_index(paper.editors, paper.full_id_tuple)

        self.data[id] = paper
        self.parent.is_modified = True
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
            "type": VolumeType(
                cast(str, volume.get("type"))
            ),  # 'type' required by schema
            "parent": parent,
            "editors": [],
            "sig_ids": [],
            "venue_ids": [],
            "urls": [],
        }
        if (ingest_date := volume.get("ingest-date")) is not None:
            kwargs["ingest_date"] = str(ingest_date)
        for element in meta:
            tag = str(element.tag)
            if tag in (
                "address",
                "doi",
                "isbn",
                "month",
                "publisher",
                "year",
            ):
                kwargs[tag] = element.text
            elif tag in (
                "journal-issue",
                "journal-volume",
                "journal-title",
            ):
                kwargs[tag.replace("-", "_")] = element.text
            elif tag in ("booktitle", "shortbooktitle"):
                kwargs[tag] = MarkupText.from_xml(element)
            elif tag == "editor":
                kwargs["editors"].append(NameSpecification.from_xml(element))
            elif tag == "pdf":
                kwargs["pdf"] = PDFReference.from_xml(element)
            elif tag == "url":
                type_ = str(element.get("type", ""))
                kwargs["urls"].append((type_, URLReference.from_xml(element)))
            elif tag == "sig":
                kwargs["sig_ids"].append(str(element.text))
            elif tag == "venue":
                kwargs["venue_ids"].append(str(element.text))
            else:  # pragma: no cover
                raise ValueError(f"Unsupported element for Volume: <{tag}>")
        return cls(**kwargs)

    def to_xml(self, with_papers: bool = True) -> etree._Element:
        """Serialize this volume in the Anthology XML format.

        Arguments:
            with_papers: If False, the returned `<volume>` will only contain the volume's `<meta>` block, but no contained papers.  Defaults to True.

        Returns:
            A serialization of this volume as a `<volume>` block in the Anthology XML format.
        """
        volume = E.volume(id=self.id, type=self.type.value)
        if self._ingest_date is not None:
            volume.set("ingest-date", self._ingest_date)
        volume.append(etree.Comment(self.web_url))
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
        if self._pdf is not None:
            meta.append(self._pdf.to_xml())
        for type_, url in self.urls:
            elem = url.to_xml("url")
            if type_:
                elem.set("type", type_)
            meta.append(elem)
        for sig in self.sig_ids:
            meta.append(E.sig(sig))
        for venue in self.venue_ids:
            meta.append(E.venue(venue))
        for tag in (
            "journal_volume",
            "journal_issue",
        ):
            if (value := getattr(self, tag)) is not None:
                meta.append(getattr(E, tag.replace("_", "-"))(value))
        if self._journal_title is not None:
            meta.append(getattr(E, "journal-title")(self._journal_title))
        volume.append(meta)

        if with_papers:
            for paper in self.values():
                volume.append(paper.to_xml())

        return volume
