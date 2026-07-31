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

import logging
import pytest

from acl_anthology.venues import VenueIndex, Venue

all_toy_venue_ids = ("acl", "cl", "humeval", "lrec", "nlma", "ws")


def test_venue_defaults():
    venue = Venue("foo", None, "FOO", "Workshop on Foobar")
    assert venue.id == "foo"
    assert venue.acronym == "FOO"
    assert venue.name == "Workshop on Foobar"
    assert not venue.is_acl
    assert not venue.is_toplevel
    assert venue.oldstyle_letter is None
    assert venue.url is None
    assert venue.item_ids == set()


def test_venue_set_itemids():
    venue = Venue("foo", None, "FOO", "Workshop on Foobar")
    venue.item_ids = [("2099.foo", "long", None), ("2099.foo", "short", None)]

    with pytest.raises(TypeError):
        venue.item_ids = ["2099.foo-long", "2099.foo-short"]

    with pytest.raises(TypeError):
        venue.item_ids = "$§§$§$"


def test_venueindex_create(anthology):
    index = anthology.venues
    venue = index.create(
        id="acla", acronym="ACLA", name="ACL Anthology Workshop", is_acl=True
    )
    assert "acla" in index
    assert index["acla"] is venue
    assert venue.acronym == "ACLA"
    assert venue.name == "ACL Anthology Workshop"
    assert venue.is_acl


def test_venueindex_create_with_invalid_id(anthology):
    with pytest.raises(ValueError):
        anthology.venues.create(id="acl-a", acronym="ACLA", name="ACL Anthology Workshop")


def test_venueindex_cl(anthology):
    index = anthology.venues
    venue = index.get("cl")
    assert venue.id == "cl"
    assert venue.acronym == "CL"
    assert venue.name == "Computational Linguistics"
    assert venue.is_acl
    assert venue.is_toplevel
    assert venue.oldstyle_letter == "J"
    assert venue.item_ids == {
        ("J89", "1", None),
        ("J89", "2", None),
        ("J89", "3", None),
        ("J89", "4", None),
    }


def test_venue_volumes(anthology):
    index = anthology.venues
    venue = index.get("cl")
    volumes = list(venue.volumes())
    assert len(volumes) == 4
    assert set(volume.full_id_tuple for volume in volumes) == {
        ("J89", "1", None),
        ("J89", "2", None),
        ("J89", "3", None),
        ("J89", "4", None),
    }


def test_venueindex_iter(anthology):
    index = VenueIndex(anthology)
    venue_ids = index.keys()
    assert set(venue_ids) == set(all_toy_venue_ids)


def test_venueindex_noindex(anthology, caplog):
    """Accessing venues with no_item_ids=True should not load XML files."""
    with caplog.at_level(logging.DEBUG):
        index = VenueIndex(anthology, no_item_ids=True)
        _ = index.get("cl").name
    assert not any("XML data file" in rec.message for rec in caplog.records)


def test_venueindex_roundtrip_data(anthology, tmp_path):
    index = anthology.venues
    index.load()
    data_in = index.path
    data_out = tmp_path / "venues.json"
    index.save(data_out)
    assert data_out.is_file()
    with (
        open(data_in, "r", encoding="utf-8") as f,
        open(data_out, "r", encoding="utf-8") as g,
    ):
        expected = f.read()
        out = g.read()
    assert out == expected
