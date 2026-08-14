# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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


import re
import itertools as it
from rich.console import Console

import acl_anthology.utils.attrs as my_attrs


def test_all_objects_have_functioning_rich_repr(anthology):
    console = Console(quiet=True, width=120)
    anthology.load_all()
    for obj in it.chain(
        (
            anthology.collections,
            anthology.events,
            anthology.people,
            anthology.sigs,
            anthology.venues,
        ),
        anthology.collections.values(),
        anthology.volumes(),
        list(anthology.papers())[:5],  # slow, so we limit ourselves to a sample
        anthology.events.values(),
        list(anthology.people.values())[:5],  # slow, so we limit ourselves to a sample
        anthology.sigs.values(),
        anthology.venues.values(),
    ):
        repr(obj)
        assert hasattr(obj, "__rich_repr__")
        console.print(obj)


def test_repr_item_ids():
    assert my_attrs.repr_item_ids([]) == "[]"
    assert (
        re.search(
            r"list.* with 1 item ", my_attrs.repr_item_ids([("2024.aacl", "main", "777")])
        )
        is not None
    )
    item_ids = [
        ("2026.acl", "long", "1"),
        ("2028.eacl", "main", "100"),
        ("2030.emnlp", "short", "9870"),
    ]
    assert re.search(r"list.* with 3 items", my_attrs.repr_item_ids(item_ids)) is not None
    assert (
        re.search(r"tuple.* with 3 items", my_attrs.repr_item_ids(tuple(item_ids)))
        is not None
    )
    assert (
        re.search(r"set.* with 3 items", my_attrs.repr_item_ids(set(item_ids)))
        is not None
    )
