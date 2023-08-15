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

from attrs import define, field
from lxml import etree
from typing import Any, Optional, TYPE_CHECKING

from ..files import (
    AttachmentReference,
)
from ..people import NameSpecification
from ..text import MarkupText

if TYPE_CHECKING:
    from ..anthology import Anthology
    from . import Collection


@define
class Event:
    """An event, such as a meeting or a conference.

    Attributes: Required Attributes:
        id: The ID of this event.
        parent: The Collection object that this event belongs to.

    Attributes: List Attributes:
        colocated_ids: Volume IDs of proceedings that were colocated with this event.
        links: Links to materials for this event paper. The dictionary key specifies the type of link (e.g., "handbook" or "website").
        talks: Zero or more references to talks belonging to this event.

    Attributes: Optional Attributes:
        title: The title of the event.
        location: The location of the event.
        dates: The dates when the event happened.
    """

    id: str
    parent: Collection = field(repr=False, eq=False)

    colocated_ids: list[str] = field(factory=list, repr=False)
    links: dict[str, AttachmentReference] = field(factory=dict, repr=False)
    talks: list[Talk] = field(factory=list, repr=False)

    title: Optional[MarkupText] = field(default=None)
    location: Optional[str] = field(default=None)
    dates: Optional[str] = field(default=None)

    @property
    def collection_id(self) -> str:
        """The collection ID this event belongs to."""
        return self.parent.id

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.parent.parent.parent

    @classmethod
    def from_xml(cls, parent: Collection, event: etree._Element) -> Event:
        """Instantiates a new event from an `<event>` block in the XML."""
        kwargs: dict[str, Any] = {
            "id": event.attrib["id"],
            "parent": parent,
            "talks": [],
        }
        for element in event:
            if element.tag == "meta":
                for meta in element:
                    if meta.tag == "title":
                        kwargs["title"] = MarkupText.from_xml(meta)
                    elif meta.tag in ("location", "dates"):
                        kwargs[meta.tag] = str(meta.text)
            elif element.tag == "links":
                kwargs["links"] = {}
                for url in element:
                    checksum = url.attrib.get("hash")
                    type_ = str(url.attrib.get("type", "attachment"))
                    kwargs["links"][type_] = AttachmentReference(
                        str(url.text), str(checksum)
                    )
            elif element.tag == "talk":
                kwargs["talks"].append(Talk.from_xml(element))
            elif element.tag == "colocated":
                kwargs["colocated_ids"] = [str(volume_id.text) for volume_id in element]
            else:
                raise ValueError(f"Unsupported element for Event: <{element.tag}>")
        return cls(**kwargs)


@define
class Talk:
    """A talk without an associated paper, such as a keynote or invited talk.

    Attributes:
        title: The title of the talk.
        type: Type of talk, e.g. "keynote".
        speakers: Name(s) of speaker(s) who gave this talk; can be empty.
        attachments: Links to attachments for this talk. The dictionary key specifies the type of attachment (e.g., "video" or "slides").
    """

    title: str
    type: Optional[str] = field(default=None)
    speakers: list[NameSpecification] = field(factory=list)
    attachments: dict[str, AttachmentReference] = field(factory=dict)

    @classmethod
    def from_xml(cls, element: etree._Element) -> Talk:
        """Instantiates a Talk from its `<talk>` block in the XML."""
        kwargs: dict[str, Any] = {
            "type": element.get("type"),
            "speakers": [],
            "attachments": {},
        }
        for meta in element:
            if meta.tag == "title":
                kwargs["title"] = MarkupText.from_xml(meta)
            elif meta.tag == "speaker":
                kwargs["speakers"].append(NameSpecification.from_xml(meta))
            elif meta.tag == "url":
                checksum = meta.attrib.get("hash")
                type_ = str(meta.attrib.get("type", "attachment"))
                kwargs["attachments"][type_] = AttachmentReference(
                    str(meta.text), str(checksum)
                )
            else:
                raise ValueError(f"Unsupported element for Talk: <{meta.tag}>")
        return cls(**kwargs)
