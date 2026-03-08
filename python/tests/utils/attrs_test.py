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


import itertools as it


def test_all_objects_have_functioning_rich_repr(anthology):
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
        anthology.papers(),
        anthology.events.values(),
        anthology.people.values(),
        anthology.sigs.values(),
        anthology.venues.values(),
    ):
        repr(obj)
        assert hasattr(obj, "__rich_repr__")
        list(obj.__rich_repr__())
