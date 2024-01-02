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

import pytest
from attrs import define
from lxml import etree

from acl_anthology.collections import Event, Talk
from acl_anthology.text import MarkupText
from acl_anthology.utils.xml import indent


@define
class AttachmentReferenceMock:
    name: str


@define
class CollectionStub:
    id: str


test_cases_event_xml = (
    """<event id="ws-1985">
  <colocated>
    <volume-id>W85-01</volume-id>
  </colocated>
</event>
""",
    """<event id="acl-2022">
  <meta>
    <title>60th Annual Meeting of the Association for Computational Linguistics</title>
    <location>Dublin, Ireland</location>
    <dates>May 22–27, 2022</dates>
  </meta>
  <links>
    <url type="website">https://2022.aclweb.org</url>
    <url type="handbook">2022.acl.handbook.pdf</url>
  </links>
  <talk>
    <title>Keynote 1: Language in the human brain</title>
    <speaker><first>Angela D.</first><last>Friederici</last></speaker>
    <url type="video">2022.acl.keynote1.mp4</url>
  </talk>
  <colocated>
    <volume-id>2022.findings-acl</volume-id>
    <volume-id>2022.bigscience-1</volume-id>
    <volume-id>2022.wit-1</volume-id>
  </colocated>
</event>
""",
    """<event id="hypothetical-2099">
  <meta>
    <title>I only have a <b>fancy</b> title</title>
  </meta>
</event>
""",
)


def test_event_minimum_attribs():
    event = Event(
        "foobar-2023",
        CollectionStub("Foo"),
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


def test_event_all_attribs():
    event_title = MarkupText.from_string("Lorem ipsum")
    event = Event(
        id="li-2023",
        parent=CollectionStub("2023.li"),
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


def test_event_to_xml_dont_list_colocated_volumes_of_parent():
    event = Event(
        id="li-2023",
        parent=CollectionStub("2023.li"),
        colocated_ids=[
            ("2023.baz", "1", None),
            ("2023.li", "main", None),
            ("2023.li", "side", None),
            ("2023.ling", "1", None),
        ],
    )
    out = event.to_xml()
    indent(out)
    assert (
        etree.tostring(out, encoding="unicode")
        == """<event id="li-2023">
  <colocated>
    <volume-id>2023.baz-1</volume-id>
    <volume-id>2023.ling-1</volume-id>
  </colocated>
</event>
"""
    )


@pytest.mark.parametrize("xml", test_cases_event_xml)
def test_event_roundtrip_xml(xml):
    element = etree.fromstring(xml)
    event = Event.from_xml(parent=CollectionStub("foo"), event=element)
    out = event.to_xml()
    indent(out)
    assert etree.tostring(out, encoding="unicode") == xml


def test_event_volumes(anthology):
    event = anthology.events.get("cl-1989")
    assert str(event.title) == "Computational Linguistics (1989)"
    assert len(event.colocated_ids) == 4
    volumes = list(event.volumes())
    assert len(volumes) == 4
    assert {vol.full_id_tuple for vol in volumes} == set(event.colocated_ids)
    with pytest.raises(ValueError):
        # acl-2022 lists co-located volumes that we don't have in the toy
        # dataset, so trying to access them should raise an error
        list(anthology.events.get("acl-2022").volumes())


test_cases_talk_xml = (
    """<talk>
  <title>Keynote 1: Language in the human brain</title>
  <speaker><first>Angela D.</first><last>Friederici</last></speaker>
  <url type="video">2022.acl.keynote1.mp4</url>
</talk>
""",
    """<talk type="keynote">
  <title>Keynote 2: Fire-side Chat with Barbara Grosz and Yejin Choi search lectures</title>
  <speaker><first>Yejin</first><last>Choi</last></speaker>
  <speaker><first>Barbara</first><last>Grosz</last></speaker>
  <url type="video">2022.acl.keynote2.mp4</url>
</talk>
""",
)


def test_talk_minimum_attribs():
    title = "On the Development of Software Tests"
    talk = Talk(title)
    assert talk.title == title
    assert talk.type is None
    assert not talk.speakers
    assert not talk.attachments


@pytest.mark.parametrize("xml", test_cases_talk_xml)
def test_talk_roundtrip_xml(xml):
    element = etree.fromstring(xml)
    talk = Talk.from_xml(element)
    out = talk.to_xml()
    indent(out)
    assert etree.tostring(out, encoding="unicode") == xml
