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
from acl_anthology.collections import EventIndex, EventLink


def test_eventindex_load(anthology):
    index = EventIndex(anthology)
    assert not index.is_data_loaded
    was_verbose = anthology.verbose
    anthology.verbose = True
    index.load()
    anthology.verbose = was_verbose
    assert index.is_data_loaded


def test_all_defined_events(anthology):
    index = EventIndex(anthology)
    expected_ids = {
        "facl-2022",
        "natfake-2022",
        "fcl-1989",
        "flrec-2006",
        "ws-2022",
    }
    event_ids = set(index.keys())
    assert event_ids == expected_ids


def test_are_events_correctly_defined_as_explicit_implicit(anthology):
    index = EventIndex(anthology)
    assert index["facl-2022"].is_explicit
    assert index["ws-2022"].is_explicit
    assert not index["natfake-2022"].is_explicit
    assert not index["fcl-1989"].is_explicit
    assert not index["flrec-2006"].is_explicit


def test_implicit_event_data(anthology):
    index = EventIndex(anthology)
    event = index["natfake-2022"]
    assert (
        event.title.as_text()
        == "Workshop on Fabricated Logic Meets Machine Learning (2022)"
    )
    assert event.location is None
    assert event.dates is None
    assert list(event.colocated_ids.items()) == [
        (("2022.natfake", "1", None), EventLink.INFERRED)
    ]


def test_implicit_and_explicit_event_data(anthology):
    index = EventIndex(anthology)
    # This event is explicitly defined in 2022.fws.xml (colocated with a
    # nonexistent volume) and now also implicitly picks up 2022.natfake-1,
    # since that volume also declares <venue>ws</venue>.
    event = index["ws-2022"]
    # assert event.title.as_text() == "Other Fabricated Workshops and Events (2022)"
    assert event.location is None
    assert event.dates is None
    assert list(event.colocated_ids.items()) == [
        (("2022.nonexistant", "1", None), EventLink.EXPLICIT),
        (("2022.natfake", "1", None), EventLink.INFERRED),
    ]


@pytest.mark.xfail(reason="bug: event title not created when event is implicitly defined")
def test_event_should_always_get_title(anthology):
    index = EventIndex(anthology)
    event = index["ws-2022"]
    # Currently not created when event is implicitly defined...
    assert event.title.as_text() == "Other Fabricated Workshops and Events (2022)"


def test_explicit_event_data(anthology):
    index = EventIndex(anthology)
    event = index["facl-2022"]
    assert (
        event.title.as_text()
        == "60th Annual Fabricated Meeting on Computational Linguistics"
    )
    assert event.location == "Porto, Portugal"
    assert event.dates == "May 16–21, 2022"
    assert list(event.colocated_ids.items()) == [
        (("2022.facl", "long", None), EventLink.INFERRED),
        (("2022.facl", "short", None), EventLink.INFERRED),
        (("2022.facl", "srw", None), EventLink.INFERRED),
        (("2022.facl", "demo", None), EventLink.INFERRED),
        (("2022.facl", "tutorials", None), EventLink.INFERRED),
        (("2022.ffindings", "facl", None), EventLink.EXPLICIT),
        (("2022.fabscience", "1", None), EventLink.EXPLICIT),
        (("2022.natfake", "1", None), EventLink.EXPLICIT),
        (("2022.fwit", "1", None), EventLink.EXPLICIT),
    ]


def test_event_by_volume(anthology):
    index = EventIndex(anthology)
    assert index.by_volume("2022.facl-demo") == [index["facl-2022"]]
    assert index.by_volume("K06-1") == [index["flrec-2006"]]
    events = index.by_volume("2022.natfake-1")
    # "facl-2022" is also picked up here because 2022.facl.xml's own event
    # explicitly lists this volume's collection under its <colocated> tag.
    assert {event.id for event in events} == {"natfake-2022", "ws-2022", "facl-2022"}
    # This volume is defined under <colocated>, even though it doesn't exist in the toy data
    assert index.by_volume("2022.fabscience-1") == [index["facl-2022"]]
