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

from typing import Any, Optional, TYPE_CHECKING
from attrs import define, field, setters, validators as v
from lxml import etree
from lxml.builder import E

from .item import validate_pdf
from .paper import PaperRevision, _check_revisions_pdf_names
from .record import PDFRecord, update_bibkey, validate_attachment
from .types import PaperType, VolumeType
from .. import constants
from ..exceptions import AnthologyXMLError
from ..files import AttachmentReference, PDFReference, URLReference, validate_url_tuple
from ..text import MarkupText
from ..utils.attrs import (
    attach_custom_repr,
    auto_validate_types,
    date_to_str,
    track_modifications,
)

if TYPE_CHECKING:
    from ..people import NameSpecification
    from .volume import Volume


@attach_custom_repr
@define(
    field_transformer=auto_validate_types,
    on_setattr=[setters.convert, setters.validate, track_modifications],
)
class Frontmatter(PDFRecord):
    """A volume's frontmatter, with its own restricted fields and XML serializer."""

    parent: Volume = field(repr=False, eq=False)
    bibkey: str = field(
        validator=v.matches_re(constants.RE_BIBKEY),
        on_setattr=[setters.validate, track_modifications, update_bibkey],
    )
    id: str = field(init=False, default=constants.FRONTMATTER_ID, validator=v.in_(("0",)))
    _pdf: Optional[PDFReference] = field(default=None, validator=validate_pdf)
    pages: Optional[str] = field(default=None)
    doi: Optional[str] = field(default=None)
    urls: tuple[tuple[str, URLReference], ...] = field(
        default=(),
        converter=tuple,
        validator=v.deep_iterable(
            member_validator=validate_url_tuple, iterable_validator=v.instance_of(tuple)
        ),
    )
    attachments: tuple[tuple[str, AttachmentReference], ...] = field(
        default=(),
        converter=tuple,
        validator=v.deep_iterable(
            member_validator=validate_attachment, iterable_validator=v.instance_of(tuple)
        ),
    )
    _revisions: tuple[PaperRevision, ...] = field(
        default=(),
        converter=tuple,
        validator=[
            v.deep_iterable(
                member_validator=v.instance_of(PaperRevision),
                iterable_validator=v.instance_of(tuple),
            ),
            _check_revisions_pdf_names,
        ],
    )
    _ingest_date: Optional[str] = field(
        default=None,
        converter=date_to_str,
        validator=v.optional(v.matches_re(constants.RE_ISO_DATE)),
    )

    @property
    def title(self) -> MarkupText:
        return self.parent.title

    @property
    def type(self) -> PaperType:
        """Legacy type discriminator; this object is not a Paper."""
        return PaperType.FRONTMATTER

    @property
    def is_frontmatter(self) -> bool:
        return True

    @property
    def namespecs(self) -> tuple[NameSpecification, ...]:
        return self.editors

    @property
    def citation_authors(self) -> tuple[NameSpecification, ...]:
        return self.editors

    @property
    def bibtype(self) -> str:
        if self.parent.type == VolumeType.JOURNAL:
            return "book"
        if self.parent.type == VolumeType.PROCEEDINGS:
            return "proceedings"
        raise ValueError("Media volumes do not have printed frontmatter")

    @property
    def csltype(self) -> str:
        return "book"

    @classmethod
    def from_xml(cls, parent: Volume, element: etree._Element) -> Frontmatter:
        kwargs: dict[str, Any] = {"parent": parent, "attachments": [], "urls": []}
        if value := element.get("ingest-date"):
            kwargs["ingest_date"] = value
        for child in element:
            if isinstance(child, etree._Comment):
                continue
            tag = str(child.tag)
            if tag in ("bibkey", "doi", "pages"):
                kwargs[tag] = child.text
            elif tag == "pdf":
                kwargs["pdf"] = PDFReference.from_xml(child)
            elif tag == "revision":
                kwargs.setdefault("revisions", []).append(PaperRevision.from_xml(child))
            elif tag == "attachment":
                kwargs["attachments"].append(
                    (str(child.get("type", "")), AttachmentReference.from_xml(child))
                )
            elif tag == "url":
                kwargs["urls"].append(
                    (str(child.get("type", "")), URLReference.from_xml(child))
                )
            else:
                raise AnthologyXMLError(
                    parent.full_id_tuple, tag, "unsupported element for <frontmatter>"
                )
        return cls(**kwargs)

    def to_xml(self) -> etree._Element:
        if self.bibkey == constants.NO_BIBKEY:
            raise ValueError("Cannot serialize frontmatter without bibkey")
        element = etree.Element("frontmatter")
        if self._ingest_date:
            element.set("ingest-date", self._ingest_date)
        element.append(etree.Comment(self.web_url))
        if self.pages is not None:
            element.append(E.pages(self.pages))
        if self._pdf is not None:
            element.append(self._pdf.to_xml())
        for kind, url_ref in self.urls:
            child = url_ref.to_xml("url")
            if kind:
                child.set("type", kind)
            element.append(child)
        for revision in self._revisions:
            element.append(revision.to_xml())
        if self.doi is not None:
            element.append(E.doi(self.doi))
        for kind, attachment in self.attachments:
            child = attachment.to_xml("attachment")
            if kind:
                child.set("type", kind)
            element.append(child)
        element.append(E.bibkey(self.bibkey))
        return element
