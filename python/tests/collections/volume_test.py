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

from datetime import date
from lxml import etree
from pathlib import Path
import pytest

from acl_anthology.collections import Collection, Volume, VolumeType
from acl_anthology.text import MarkupText
from acl_anthology.utils.xml import indent


class CollectionIndexStub:
    def __init__(self, parent):
        self.parent = parent


test_cases_volume_xml = (
    """<volume id="long" type="proceedings" ingest-date="2022-05-15">
  <meta>
    <booktitle>Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)</booktitle>
    <editor><first>Smaranda</first><last>Muresan</last></editor>
    <editor><first>Preslav</first><last>Nakov</last></editor>
    <editor><first>Aline</first><last>Villavicencio</last></editor>
    <publisher>Association for Computational Linguistics</publisher>
    <address>Dublin, Ireland</address>
    <month>May</month>
    <year>2022</year>
    <url hash="b8317652">2022.acl-long</url>
    <venue>acl</venue>
  </meta>
  <frontmatter>
    <url hash="56ea4e43">2022.acl-long.0</url>
    <bibkey>acl-2022-association-linguistics-1</bibkey>
  </frontmatter>
</volume>
""",
    """<volume id="1" type="journal">
  <meta>
    <booktitle>Computational Linguistics, Volume 15, Number 1, March 1989</booktitle>
    <year>1989</year>
    <venue>cl</venue>
    <journal-volume>15</journal-volume>
    <journal-issue>1</journal-issue>
  </meta>
  <frontmatter>
    <url hash="363084f8">J89-1000</url>
    <bibkey>cl-1989-linguistics</bibkey>
  </frontmatter>
  <paper id="1">
    <title>Parsing with Flexibility, Dynamic Strategies, and Idioms in Mind</title>
    <author><first>Oliviero</first><last>Stock</last></author>
    <pages>1-18</pages>
    <url hash="ad57020c">J89-1001</url>
    <bibkey>stock-1989-parsing</bibkey>
  </paper>
</volume>
""",
    """<volume id="4" type="journal">
  <meta>
    <booktitle>American Journal of Computational Linguistics (November 1975)</booktitle>
    <editor><first>David G.</first><last>Hays</last></editor>
    <month>November</month>
    <year>1975</year>
    <venue>cl</venue>
    <journal-title>American Journal of Computational Linguistics</journal-title>
  </meta>
</volume>
""",
    """<volume id="75" type="proceedings" ingest-date="2019-10-16">
  <meta>
    <booktitle>Proceedings of the 6th International Sanskrit Computational Linguistics Symposium</booktitle>
    <shortbooktitle>6th ISCLS</shortbooktitle>
    <editor><first>Pawan</first><last>Goyal</last></editor>
    <publisher>Association for Computational Linguistics</publisher>
    <address>IIT Kharagpur, India</address>
    <month>October</month>
    <year>2019</year>
    <url hash="48102019">W19-75</url>
    <venue>iscls</venue>
  </meta>
</volume>
""",
)


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
    assert not volume.is_workshop


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
    assert not volume.is_workshop


def test_volume_attributes_j89(anthology):
    volume = anthology.get_volume("J89-1")
    assert isinstance(volume, Volume)
    assert volume.id == "1"
    assert volume.venue_ids == ["cl"]
    assert volume.year == "1989"
    assert not volume.is_workshop
    assert volume.type == VolumeType.JOURNAL
    assert volume.journal_issue == "1"
    assert volume.journal_volume == "15"
    assert volume.get_journal_title() == "Computational Linguistics"


def test_volume_attributes_naloma(anthology):
    volume = anthology.get_volume("2022.naloma-1")
    assert isinstance(volume, Volume)
    assert volume.id == "1"
    assert volume.year == "2022"
    assert volume.is_workshop


def test_volume_venues_j89(anthology):
    volume = anthology.get_volume("J89-1")
    assert volume.venue_ids == ["cl"]
    venues = volume.venues()
    assert len(venues) == 1
    assert venues[0].id == "cl"


def test_volume_venues_naloma(anthology):
    volume = anthology.get_volume("2022.naloma-1")
    assert volume.venue_ids == ["nlma"]
    venues = volume.venues()
    assert len(venues) == 1
    assert venues[0].id == "nlma"


def test_volume_with_nonexistent_venue(anthology):
    volume_title = MarkupText.from_string("Lorem ipsum")
    parent = Collection("L05", CollectionIndexStub(anthology), Path("."))
    volume = Volume(
        "42",
        parent,
        type=VolumeType.JOURNAL,
        booktitle=volume_title,
        venue_ids=["doesntexist"],
        year="2005",
    )
    with pytest.raises(KeyError):
        _ = volume.venues()


def test_volume_get_events(anthology):
    volume = anthology.get_volume("2022.acl-demo")
    assert volume.get_events() == [anthology.events["acl-2022"]]


@pytest.mark.parametrize("xml", test_cases_volume_xml)
def test_volume_roundtrip_xml(xml):
    # Create and populate volume
    volume_element = etree.fromstring(xml)
    meta = volume_element.find("meta")
    volume = Volume.from_xml(None, meta)
    for child in volume_element:
        if child.tag in ("frontmatter", "paper"):
            volume._add_paper_from_xml(child)
    # Serialize and compare
    out = volume.to_xml()
    indent(out)
    assert etree.tostring(out, encoding="unicode") == xml
