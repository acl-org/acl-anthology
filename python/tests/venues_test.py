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
from pathlib import Path
from unittest.mock import patch

from acl_anthology.venues import VenueIndex, Venue


all_toy_venue_ids = ("acl", "cl", "humeval", "lrec", "nlma", "ws")


def test_venue_defaults():
    venue = Venue("foo", None, "FOO", "Workshop on Foobar", Path("foo.yaml"))
    assert venue.id == "foo"
    assert venue.acronym == "FOO"
    assert venue.name == "Workshop on Foobar"
    assert venue.path.name == "foo.yaml"
    assert not venue.is_acl
    assert not venue.is_toplevel
    assert venue.oldstyle_letter is None
    assert venue.url is None
    assert venue.item_ids == list()


def test_venue_set_itemids():
    venue = Venue("foo", None, "FOO", "Workshop on Foobar", Path("foo.yaml"))
    venue.item_ids = [("2099.foo", "long", None), ("2099.foo", "short", None)]

    with pytest.raises(TypeError):
        venue.item_ids = ["2099.foo-long", "2099.foo-short"]

    with pytest.raises(TypeError):
        venue.item_ids = "$§§$§$"


def test_venue_save(tmp_path):
    path = tmp_path / "foo.yaml"
    venue = Venue("foo", None, "FOO", "Workshop on Foobar", path)
    venue.save()
    assert path.is_file()
    with open(path, "r", encoding="utf-8") as f:
        out = f.read()
    expected = """acronym: FOO
name: Workshop on Foobar
"""
    assert out == expected


@pytest.mark.parametrize("venue_id", all_toy_venue_ids)
def test_venue_roundtrip_yaml(anthology_stub, tmp_path, venue_id):
    yaml_in = anthology_stub.datadir / "yaml" / "venues" / f"{venue_id}.yaml"
    venue = Venue.load_from_yaml(yaml_in, anthology_stub)
    yaml_out = tmp_path / f"{venue_id}.yaml"
    venue.save(yaml_out)
    assert yaml_out.is_file()
    with (
        open(yaml_in, "r", encoding="utf-8") as f,
        open(yaml_out, "r", encoding="utf-8") as g,
    ):
        expected = f.read()
        out = g.read()
    assert out == expected


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
    assert venue.path.name == "acla.yaml"


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
    assert venue.item_ids == [
        ("J89", "1", None),
        ("J89", "2", None),
        ("J89", "3", None),
        ("J89", "4", None),
    ]


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


def test_venueindex_save(anthology):
    index = VenueIndex(anthology)
    index.load()
    with patch.object(Venue, "save") as mock:
        index.save()
        assert mock.call_count == len(index)
