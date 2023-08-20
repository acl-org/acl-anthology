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

from attrs import define
from pathlib import Path

from acl_anthology.collections import Event, Talk, Collection
from acl_anthology.text import MarkupText


@define
class AttachmentReferenceMock:
    name: str


def test_event_minimum_attribs():
    parent = Collection("Foo", None, Path("."))
    event = Event(
        "foobar-2023",
        parent,
    )
    assert event.id == "foobar-2023"
    assert event.collection_id == "Foo"
    assert not event.is_explicit
    assert not event.colocated_ids
    assert not event.links
    assert not event.talks
    assert event.title is None
    assert event.location is None
    assert event.dates is None


def test_talk_minimum_attribs():
    title = "On the Development of Software Tests"
    talk = Talk(title)
    assert talk.title == title
    assert talk.type is None
    assert not talk.speakers
    assert not talk.attachments


def test_event_all_attribs():
    event_title = MarkupText.from_string("Lorem ipsum")
    parent = Collection("2023.li", None, Path("."))
    event = Event(
        id="li-2023",
        parent=parent,
        is_explicit=True,
        title=event_title,
        location="Online",
        dates="August 17-19, 2023",
        colocated_ids=[
            ("2023.foobar", "1", None),
            ("2023.baz", "1", None),
            ("2023.asdf", "1", None),
        ],
        talks=[Talk("Invited talk")],
        links={"Website": AttachmentReferenceMock("http://foobar.com")},
    )
    assert event.collection_id == "2023.li"
    assert event.title == event_title
    assert event.is_explicit
