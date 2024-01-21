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

from acl_anthology.collections import EventIndex


def test_all_defined_events(anthology):
    index = EventIndex(anthology)
    expected_ids = {"acl-2022", "nlma-2022", "cl-1989", "lrec-2006"}
    event_ids = set(index.keys())
    assert event_ids == expected_ids


def test_implicit_events(anthology):
    index = EventIndex(anthology)
    assert index["acl-2022"].is_explicit
    assert not index["nlma-2022"].is_explicit
    assert not index["cl-1989"].is_explicit
    assert not index["lrec-2006"].is_explicit


def test_explicit_event(anthology):
    index = EventIndex(anthology)
    event = index["acl-2022"]
    assert (
        event.title.as_text()
        == "60th Annual Meeting of the Association for Computational Linguistics"
    )
    assert event.location == "Dublin, Ireland"
    assert event.dates == "May 22–27, 2022"
    assert event.colocated_ids == [
        ("2022.acl", "long", None),
        ("2022.acl", "short", None),
        ("2022.acl", "srw", None),
        ("2022.acl", "demo", None),
        ("2022.acl", "tutorials", None),
        ("2022.findings", "acl", None),
        ("2022.bigscience", "1", None),
        ("2022.naloma", "1", None),
        ("2022.wit", "1", None),
    ]


def test_event_by_volume(anthology):
    index = EventIndex(anthology)
    assert index.by_volume("2022.acl-demo") == [index["acl-2022"]]
    assert index.by_volume("L06-1") == [index["lrec-2006"]]
    events = index.by_volume("2022.naloma-1")
    assert {event.id for event in events} == {"acl-2022", "nlma-2022"}
    # This volume is defined under <colocated>, even though it doesn't exist in the toy data
    assert index.by_volume("2022.bigscience-1") == [index["acl-2022"]]
