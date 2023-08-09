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

from acl_anthology.venues import VenueIndex, Venue


def test_venue_defaults():
    venue = Venue("foo", "FOO", "Workshop on Foobar")
    assert venue.id == "foo"
    assert venue.acronym == "FOO"
    assert venue.name == "Workshop on Foobar"
    assert not venue.is_acl
    assert not venue.is_toplevel
    assert venue.oldstyle_letter is None
    assert venue.url is None


def test_venueindex_cl(anthology):
    index = VenueIndex(anthology)
    venue = index.get("cl")
    assert venue.id == "cl"
    assert venue.acronym == "CL"
    assert venue.name == "Computational Linguistics"
    assert venue.is_acl
    assert venue.is_toplevel
    assert venue.oldstyle_letter == "J"


def test_venueindex_iter(anthology):
    index = VenueIndex(anthology)
    venue_ids = set(venue.id for venue in index)
    assert venue_ids == {"acl", "cl", "humeval", "lrec"}
