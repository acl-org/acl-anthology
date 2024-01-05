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
from pathlib import Path
from acl_anthology.venues import VenueIndex, Venue


all_toy_venue_ids = ("acl", "cl", "humeval", "lrec", "nlma")


def test_venue_defaults():
    venue = Venue("foo", "FOO", "Workshop on Foobar", Path("foo.yaml"))
    assert venue.id == "foo"
    assert venue.acronym == "FOO"
    assert venue.name == "Workshop on Foobar"
    assert venue.path.name == "foo.yaml"
    assert not venue.is_acl
    assert not venue.is_toplevel
    assert venue.oldstyle_letter is None
    assert venue.url is None


def test_venue_save(tmp_path):
    path = tmp_path / "foo.yaml"
    venue = Venue("foo", "FOO", "Workshop on Foobar", path)
    venue.save()
    assert path.is_file()
    with open(path, "r") as f:
        out = f.read()
    expected = """acronym: FOO
name: Workshop on Foobar
"""
    assert out == expected


@pytest.mark.parametrize("venue_id", all_toy_venue_ids)
def test_venue_roundtrip_yaml(anthology_stub, tmp_path, venue_id):
    yaml_in = anthology_stub.datadir / "yaml" / "venues" / f"{venue_id}.yaml"
    venue = Venue.load_from_yaml(yaml_in)
    yaml_out = tmp_path / f"{venue_id}.yaml"
    venue.save(yaml_out)
    assert yaml_out.is_file()
    with open(yaml_in, "r") as f, open(yaml_out, "r") as g:
        expected = f.read()
        out = g.read()
    assert out == expected


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
    venue_ids = index.keys()
    assert set(venue_ids) == set(all_toy_venue_ids)
