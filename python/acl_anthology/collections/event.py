# Copyright 2022 Matt Post <post@cs.jhu.edu>
# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
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
from lxml.builder import E
from typing import Any, Iterator, Optional, TYPE_CHECKING

from ..files import AttachmentReference
from ..people import NameSpecification
from ..text import MarkupText
from ..utils.ids import AnthologyIDTuple, parse_id, build_id_from_tuple

if TYPE_CHECKING:
    from ..anthology import Anthology
    from . import Collection, Volume


@define
class Event:
    """An event, such as a meeting or a conference.

    Attributes: Required Attributes:
        id: The ID of this event.
        parent: The Collection object that this event belongs to.
        is_explicit: True if this event was defined explicitly in the XML.

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
    is_explicit: bool = field(default=False)

    colocated_ids: list[AnthologyIDTuple] = field(
        factory=list, repr=lambda x: f"<list of {len(x)} AnthologyIDTuple objects>"
    )
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

    def volumes(self) -> Iterator[Volume]:
        """Returns an iterator over all volumes co-located with this event."""
        for anthology_id in self.colocated_ids:
            volume = self.root.get_volume(anthology_id)
            if volume is None:
                raise ValueError(
                    f"Event {self.id} lists co-located volume "
                    f"{build_id_from_tuple(anthology_id)}, which doesn't exist"
                )
            yield volume

    @classmethod
    def from_xml(cls, parent: Collection, event: etree._Element) -> Event:
        """Instantiates a new event from an `<event>` block in the XML."""
        kwargs: dict[str, Any] = {
            "id": event.get("id"),
            "parent": parent,
            "is_explicit": True,
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
                    type_ = str(url.get("type", "attachment"))
                    kwargs["links"][type_] = AttachmentReference.from_xml(url)
            elif element.tag == "talk":
                kwargs["talks"].append(Talk.from_xml(element))
            elif element.tag == "colocated":
                kwargs["colocated_ids"] = [
                    parse_id(str(volume_id.text)) for volume_id in element
                ]
            else:
                raise ValueError(f"Unsupported element for Event: <{element.tag}>")
        return cls(**kwargs)

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this event as an `<event>` block in the Anthology XML format.
        """
        elem = E.event(id=self.id)
        # <meta> block
        meta = E.meta()
        if self.title is not None:
            meta.append(self.title.to_xml("title"))
        if self.location is not None:
            meta.append(E.location(self.location))
        if self.dates is not None:
            meta.append(E.dates(self.dates))
        if len(meta) > 0:
            elem.append(meta)
        # <links> block
        if self.links:
            links = E.links()
            for type_, attachment in self.links.items():
                url = attachment.to_xml("url")
                url.set("type", type_)
                links.append(url)
            elem.append(links)
        # <talk>s
        for talk in self.talks:
            elem.append(talk.to_xml())
        # <colocated>
        if self.colocated_ids:
            colocated = E.colocated()
            for id_tuple in self.colocated_ids:
                if id_tuple[0] != self.parent.id:
                    colocated.append(
                        getattr(E, "volume-id")(build_id_from_tuple(id_tuple))
                    )
            elem.append(colocated)
        return elem


@define
class Talk:
    """A talk without an associated paper, such as a keynote or invited talk.

    Attributes:
        title: The title of the talk.
        type: Type of talk, e.g. "keynote".
        speakers: Name(s) of speaker(s) who gave this talk; can be empty.
        attachments: Links to attachments for this talk. The dictionary key specifies the type of attachment (e.g., "video" or "slides").
    """

    title: MarkupText = field()
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
                type_ = str(meta.get("type", "attachment"))
                kwargs["attachments"][type_] = AttachmentReference.from_xml(meta)
            else:
                raise ValueError(f"Unsupported element for Talk: <{meta.tag}>")
        return cls(**kwargs)

    def to_xml(self) -> etree._Element:
        """
        Returns:
            A serialization of this talk as a `<talk>` block in the Anthology XML format.
        """
        elem = E.talk()
        if self.type is not None:
            elem.set("type", self.type)
        elem.append(self.title.to_xml("title"))
        for name_spec in self.speakers:
            elem.append(name_spec.to_xml("speaker"))
        for type_, attachment in self.attachments.items():
            url = attachment.to_xml("url")
            url.set("type", type_)
            elem.append(url)
        return elem
