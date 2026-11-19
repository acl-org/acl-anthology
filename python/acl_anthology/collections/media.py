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

import datetime
from typing import Any, ClassVar, Iterable, Optional, TYPE_CHECKING

from attrs import converters, define, field, setters, validators as v
from lxml import etree
from lxml.builder import E

from .item import update_person_itemids
from .record import DeletionNotice, Record, update_bibkey, validate_attachment
from .types import MediaType
from .. import constants
from ..exceptions import AnthologyInvalidIDError, AnthologyXMLError
from ..files import (
    AttachmentReference,
    AudioReference,
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

if TYPE_CHECKING:
    from ..utils.latex import SerializableAsBibTeX
    from .volume import Volume


@attach_custom_repr
@define(
    field_transformer=auto_validate_types,
    on_setattr=[setters.convert, setters.validate, track_modifications],
)
class Media(Record):
    """A standalone audio/video work, serialized as `<media>`, never `<paper>`.

    Create records through `Volume.create_media()` so IDs, bibliography keys,
    contributor normalization, and person indexing are handled together.
    """

    _namespec_fields: ClassVar[tuple[str, ...]] = ("authors", "_editors")
    id: str = field(converter=int_to_str)
    parent: Volume = field(repr=False, eq=False)
    bibkey: str = field(
        validator=v.matches_re(constants.RE_BIBKEY),
        on_setattr=[setters.validate, track_modifications, update_bibkey],
    )
    title: MarkupText = field(converter=to_markuptext)
    type: MediaType = field(default=MediaType.MEDIA, converter=MediaType)
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
    audios: tuple[AudioReference, ...] = field(default=(), converter=tuple)
    videos: tuple[VideoReference, ...] = field(default=(), converter=tuple)
    urls: tuple[tuple[str, URLReference], ...] = field(
        default=(),
        converter=tuple,
        validator=v.deep_iterable(
            member_validator=validate_url_tuple,
            iterable_validator=v.instance_of(tuple),
        ),
    )
    attachments: tuple[tuple[str, AttachmentReference], ...] = field(
        default=(),
        converter=tuple,
        validator=v.deep_iterable(
            member_validator=validate_attachment,
            iterable_validator=v.instance_of(tuple),
        ),
    )
    abstract: Optional[MarkupText] = field(
        default=None, converter=converters.optional(to_markuptext)
    )
    deletion: Optional[DeletionNotice] = field(
        default=None, validator=v.optional(v.instance_of(DeletionNotice))
    )
    doi: Optional[str] = field(default=None)
    language: Optional[str] = field(default=None)
    note: Optional[str] = field(default=None)
    _month: Optional[str] = field(default=None)
    _ingest_date: Optional[str] = field(
        default=None,
        converter=date_to_str,
        validator=v.optional(v.matches_re(constants.RE_ISO_DATE)),
    )
    publication_date: Optional[str] = field(
        default=None,
        converter=date_to_str,
        validator=v.optional(v.matches_re(constants.RE_ISO_DATE)),
    )
    duration: Optional[int] = field(
        default=None,
        validator=v.optional(
            v.and_(v.instance_of(int), v.gt(0), v.not_(v.instance_of(bool)))
        ),
    )
    episode: Optional[str] = field(
        default=None,
        converter=int_to_str,
        validator=v.optional(v.matches_re(r"\S(?:.*\S)?")),
    )
    license: Optional[str] = field(default=None)

    def __attrs_post_init__(self) -> None:
        for spec in self.namespecs:
            spec.parent = self

    @id.validator
    def _check_id(self, _: Any, value: str) -> None:
        if not value.isascii() or not value.isdecimal() or int(value) < 1:
            raise AnthologyInvalidIDError(value, "not a positive media item ID")

    @publication_date.validator
    def _check_date(self, _: Any, value: Optional[str]) -> None:
        if value is not None:
            datetime.date.fromisoformat(value)

    @property
    def is_media(self) -> bool:
        return True

    @property
    def type_label(self) -> str:
        if self.type == MediaType.PODCAST:
            return "Podcast episode"
        if self.type == MediaType.MEDIA:
            return "Media recording"
        return self.type.value.capitalize()

    @property
    def media_format(self) -> str:
        if self.audios and self.videos:
            return "Audio and video recording"
        if self.audios:
            return "Audio recording"
        if self.videos:
            return "Video recording"
        return "Recording"

    @property
    def editors(self) -> tuple[NameSpecification, ...]:
        return self._editors or self.parent.editors

    @editors.setter
    def editors(self, value: Iterable[NameSpecification]) -> None:
        self._editors = into_namespec_tuple(value)

    @property
    def year(self) -> str:
        return self.publication_date[:4] if self.publication_date else self.parent.year

    @property
    def month(self) -> Optional[str]:
        if self._month is not None:
            return self._month
        if self.publication_date:
            return datetime.date.fromisoformat(self.publication_date).strftime("%B")
        return self.parent.month

    @month.setter
    def month(self, value: Optional[str]) -> None:
        self._month = value

    @property
    def bibtype(self) -> str:
        return "misc"

    @property
    def csltype(self) -> str:
        if self.type == MediaType.PODCAST:
            return "broadcast"
        if self.type == MediaType.MEDIA and self.videos:
            return "motion_picture"
        return "speech"

    def _citeproc_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "container-title": self.parent.title.as_text(),
            "genre": self.type_label,
            "medium": self.media_format,
            "number": self.episode,
        }
        if self.publication_date:
            fields["issued"] = {
                "date-parts": [[int(part) for part in self.publication_date.split("-")]]
            }
        return fields

    def _bibtex_container_fields(self) -> list[tuple[str, SerializableAsBibTeX]]:
        return [
            ("howpublished", self.parent.title),
            ("type", self.type_label),
            ("number", self.episode),
            ("date", self.publication_date),
        ]

    def _bibtex_note(self) -> str:
        return ". ".join(
            filter(
                None,
                (
                    f"{self.type_label} {self.episode}"
                    if self.episode is not None
                    else self.type_label,
                    self.media_format,
                    f"Released {self.publication_date}"
                    if self.publication_date
                    else None,
                    self.note,
                ),
            )
        )

    @classmethod
    def from_xml(cls, parent: Volume, element: etree._Element) -> Media:
        if element.tag != "media":
            raise AnthologyXMLError(
                parent.full_id_tuple, str(element.tag), "expected <media>"
            )
        kwargs: dict[str, Any] = {
            "parent": parent,
            "id": str(element.get("id")),
            "type": MediaType(element.get("type", "media")),
            "authors": [],
            "editors": [],
            "audios": [],
            "videos": [],
            "attachments": [],
            "urls": [],
        }
        if value := element.get("ingest-date"):
            kwargs["ingest_date"] = value
        for child in element:
            if isinstance(child, etree._Comment):
                continue
            tag = str(child.tag)
            if tag in ("title", "abstract"):
                kwargs[tag] = MarkupText.from_xml(child)
            elif tag in ("author", "editor"):
                kwargs[f"{tag}s"].append(NameSpecification.from_xml(child))
            elif tag in ("audio", "video"):
                reference = AudioReference if tag == "audio" else VideoReference
                kwargs[f"{tag}s"].append(reference.from_xml(child))
            elif tag == "attachment":
                kwargs["attachments"].append(
                    (str(child.get("type", "")), AttachmentReference.from_xml(child))
                )
            elif tag == "url":
                kwargs["urls"].append(
                    (str(child.get("type", "")), URLReference.from_xml(child))
                )
            elif tag == "date":
                kwargs["publication_date"] = child.text
            elif tag == "duration":
                kwargs["duration"] = int(str(child.text))
            elif tag in (
                "bibkey",
                "doi",
                "language",
                "month",
                "note",
                "episode",
                "license",
            ):
                kwargs[tag] = child.text
            elif tag in ("removed", "retracted"):
                kwargs["deletion"] = DeletionNotice.from_xml(child)
            else:
                raise AnthologyXMLError(
                    parent.full_id_tuple, tag, "unsupported element for <media>"
                )
        return cls(**kwargs)

    def to_xml(self) -> etree._Element:
        if self.bibkey == constants.NO_BIBKEY:
            raise ValueError("Cannot serialize media without bibkey")
        element = etree.Element("media", id=self.id, type=self.type.value)
        if self._ingest_date:
            element.set("ingest-date", self._ingest_date)
        element.append(etree.Comment(self.web_url))
        element.append(self.title.to_xml("title"))
        for spec in self.authors:
            element.append(spec.to_xml("author"))
        for spec in self._editors:
            element.append(spec.to_xml("editor"))
        if self.abstract is not None:
            element.append(self.abstract.to_xml("abstract"))
        for kind, url_ref in self.urls:
            child = url_ref.to_xml("url")
            if kind:
                child.set("type", kind)
            element.append(child)
        for kind, attachment in self.attachments:
            child = attachment.to_xml("attachment")
            if kind:
                child.set("type", kind)
            element.append(child)
        for video in self.videos:
            element.append(video.to_xml())
        for audio in self.audios:
            element.append(audio.to_xml())
        for tag, value in (
            ("doi", self.doi),
            ("language", self.language),
            ("month", self._month),
            ("note", self.note),
            ("date", self.publication_date),
            ("duration", str(self.duration) if self.duration is not None else None),
            ("episode", self.episode),
            ("license", self.license),
        ):
            if value is not None:
                element.append(getattr(E, tag)(value))
        if self.deletion:
            element.append(self.deletion.to_xml())
        element.append(E.bibkey(self.bibkey))
        return element
