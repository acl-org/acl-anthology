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

from datetime import date
from pathlib import Path

from acl_anthology.collections import Collection, Volume, VolumeType
from acl_anthology.text import MarkupText


def test_volume_minimum_attribs():
    volume_title = MarkupText.from_string("Lorem ipsum")
    parent = Collection("L05", None, Path("."))
    volume = Volume(
        "6",
        parent,
        type=VolumeType.JOURNAL,
        booktitle=volume_title,
        venue_ids=["li"],
        year="2005",
    )
    assert volume.full_id == "L05-6"
    assert volume.title == volume_title
    assert volume.get_ingest_date().year == 1900


def test_volume_all_attribs():
    volume_title = MarkupText.from_string("Lorem ipsum")
    volume_shorttitle = MarkupText.from_string("L.I.")
    parent = Collection("2023.acl-long", None, Path("."))
    volume = Volume(
        id="42",
        parent=parent,
        type="proceedings",
        booktitle=volume_title,
        year="2023",
        address="Online",
        doi="10.100/0000",
        editors=[],
        ingest_date="2023-01-12",
        isbn="0000-0000-0000",
        month="jan",
        pdf=None,
        publisher="Myself",
        shortbooktitle=volume_shorttitle,
        venue_ids=["li", "acl"],
    )
    assert volume.ingest_date == "2023-01-12"
    assert volume.get_ingest_date() == date(2023, 1, 12)


def test_volume_attributes_2022acl(anthology):
    volume = anthology.get_volume("2022.acl-long")
    assert isinstance(volume, Volume)
    assert volume.id == "long"
    assert volume.ingest_date == "2022-05-15"
    assert volume.get_ingest_date() == date(2022, 5, 15)
    assert volume.address == "Dublin, Ireland"
    assert volume.publisher == "Association for Computational Linguistics"
    assert volume.month == "May"
    assert volume.year == "2022"
    assert volume.pdf.name == "2022.acl-long"
    assert volume.pdf.checksum == "b8317652"
    assert volume.venue_ids == ["acl"]


def test_volume_attributes_j89(anthology):
    volume = anthology.get_volume("J89-1")
    assert isinstance(volume, Volume)
    assert volume.id == "1"
    assert volume.venue_ids == ["cl"]
    assert volume.year == "1989"


def test_volume_venues_j89(anthology):
    volume = anthology.get_volume("J89-1")
    assert volume.venue_ids == ["cl"]
    venues = volume.venues()
    assert len(venues) == 1
    assert venues[0].id == "cl"
