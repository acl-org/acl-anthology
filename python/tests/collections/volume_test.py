# Copyright 2023-2026 Marcel Bollmann <marcel@bollmann.me>
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

from acl_anthology.collections import Collection, Volume, VolumeType, Paper
from acl_anthology.people import NameSpecification as NameSpec, UNVERIFIED_PID_FORMAT
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
    """<volume id="demo" type="proceedings" ingest-date="2022-05-15">
  <meta>
    <booktitle>Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics: System Demonstrations</booktitle>
    <editor><first>Valerio</first><last>Basile</last></editor>
    <editor><first>Zornitsa</first><last>Kozareva</last></editor>
    <editor><first>Sanja</first><last>Stajner</last></editor>
    <publisher>Association for Computational Linguistics</publisher>
    <address>Dublin, Ireland</address>
    <doi>10.18653/v1/2022.acl-demo</doi>
    <month>May</month>
    <year>2022</year>
    <url hash="d92e3f4d">2022.acl-demo</url>
    <venue>acl</venue>
  </meta>
  <frontmatter>
    <url hash="ad64a7d9">2022.acl-demo.0</url>
    <bibkey>acl-2022-association-linguistics-system</bibkey>
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
    parent = Collection("L05", None, Path("."))
    volume = Volume(
        "6",
        parent,
        type=VolumeType.JOURNAL,
        booktitle="Lorem ipsum",
        venue_ids=["li"],
        year="2005",
    )
    assert volume.full_id == "L05-6"
    assert volume.title == "Lorem ipsum"
    assert volume.get_ingest_date().year == 1900
    assert not volume.is_workshop


def test_volume_all_attribs():
    parent = Collection("2023.acl", None, Path("."))
    volume = Volume(
        id="long",
        parent=parent,
        type="proceedings",
        booktitle="Lorem ipsum",
        year="2023",
        address="Online",
        doi="10.100/0000",
        editors=[],
        ingest_date="2023-01-12",
        isbn="0000-0000-0000",
        month="jan",
        pdf=None,
        publisher="Myself",
        shortbooktitle="L.I.",
        venue_ids=["li", "acl"],
    )
    assert volume.ingest_date == "2023-01-12"
    assert volume.get_ingest_date() == date(2023, 1, 12)


def test_volume_attributes_2022acl_long(anthology):
    volume = anthology.get_volume("2022.acl-long")
    assert isinstance(volume, Volume)
    assert volume.id == "long"
    assert volume.ingest_date == "2022-05-15"
    assert volume.get_ingest_date() == date(2022, 5, 15)
    assert volume.address == "Dublin, Ireland"
    assert volume.publisher == "Association for Computational Linguistics"
    assert volume.doi is None
    assert volume.month == "May"
    assert volume.year == "2022"
    assert volume.pdf.name == "2022.acl-long"
    assert volume.pdf.checksum == "b8317652"
    assert volume.venue_ids == ["acl"]
    assert volume.venue_acronym == "ACL"
    assert not volume.is_workshop
    assert isinstance(volume.frontmatter, Paper) and volume.frontmatter.id == "0"


def test_volume_attributes_2022acl_demo(anthology):
    volume = anthology.get_volume("2022.acl-demo")
    assert isinstance(volume, Volume)
    assert volume.id == "demo"
    assert volume.ingest_date == "2022-05-15"
    assert volume.get_ingest_date() == date(2022, 5, 15)
    assert volume.address == "Dublin, Ireland"
    assert volume.publisher == "Association for Computational Linguistics"
    assert volume.doi == "10.18653/v1/2022.acl-demo"
    assert volume.month == "May"
    assert volume.year == "2022"
    assert volume.pdf.name == "2022.acl-demo"
    assert volume.pdf.checksum == "d92e3f4d"
    assert volume.venue_ids == ["acl"]
    assert volume.venue_acronym == "ACL"
    assert not volume.is_workshop
    assert isinstance(volume.frontmatter, Paper) and volume.frontmatter.id == "0"
    assert len(volume.editors) == 3
    assert volume.editors == volume.namespecs


def test_volume_attributes_j89(anthology):
    volume = anthology.get_volume("J89-1")
    assert isinstance(volume, Volume)
    assert volume.id == "1"
    assert volume.venue_ids == ["cl"]
    assert volume.venue_acronym == "CL"
    assert volume.year == "1989"
    assert not volume.is_workshop
    assert volume.type == VolumeType.JOURNAL
    assert volume.journal_issue == "1"
    assert volume.journal_volume == "15"
    assert volume.get_journal_title() == "Computational Linguistics"
    assert isinstance(volume.frontmatter, Paper) and volume.frontmatter.id == "0"


def test_volume_attributes_naloma(anthology):
    volume = anthology.get_volume("2022.naloma-1")
    assert isinstance(volume, Volume)
    assert volume.id == "1"
    assert volume.year == "2022"
    assert volume.is_workshop
    assert volume.venue_ids == ["nlma", "ws"]
    assert volume.venue_acronym == "NALOMA"
    assert isinstance(volume.frontmatter, Paper) and volume.frontmatter.id == "0"


def test_volume_without_frontmatter(anthology):
    volume = anthology.get_volume("J89-3")
    assert isinstance(volume, Volume)
    assert volume.frontmatter is None


def test_volume_set_ingest_date(anthology):
    volume = anthology.get_volume("2022.acl-demo")
    volume.ingest_date = "2025-07-15"
    assert volume.get_ingest_date() == date(2025, 7, 15)
    volume.ingest_date = date(2026, 3, 1)
    assert volume.get_ingest_date() == date(2026, 3, 1)
    assert volume.ingest_date == "2026-03-01"


@pytest.mark.parametrize(
    "attr_name",
    (
        "id",
        "title",
        "year",
        "editors",
        "venue_ids",
        "address",
        "ingest_date",
        "pdf",
        "shorttitle",
    ),
)
def test_volume_setattr_sets_collection_is_modified(anthology, attr_name):
    volume = anthology.get_volume("2022.acl-long")
    assert not volume.parent.is_modified
    setattr(volume, attr_name, getattr(volume, attr_name))
    assert volume.parent.is_modified


def test_paper_setattr_on_namespec_sets_collection_is_modified(anthology):
    volume = anthology.get_volume("2022.acl-long")
    assert not volume.collection.is_modified
    volume.editors[0].affiliation = "University of Someplace"
    assert volume.collection.is_modified


def test_volume_venues_j89(anthology):
    volume = anthology.get_volume("J89-1")
    assert volume.venue_ids == ["cl"]
    venues = volume.venues()
    assert len(venues) == 1
    assert venues[0].id == "cl"


def test_volume_venues_naloma(anthology):
    volume = anthology.get_volume("2022.naloma-1")
    assert volume.venue_ids == ["nlma", "ws"]
    venues = volume.venues()
    assert len(venues) == 2
    assert venues[0].id == "nlma"
    assert venues[1].id == "ws"


def test_volume_with_nonexistent_venue(anthology):
    parent = Collection("L05", CollectionIndexStub(anthology), Path("."))
    volume = Volume(
        "42",
        parent,
        type=VolumeType.JOURNAL,
        booktitle="Lorem ipsum",
        venue_ids=["doesntexist"],
        year="2005",
    )
    with pytest.raises(KeyError):
        _ = volume.venues()


def test_volume_with_multiple_venues(anthology):
    volume_title = MarkupText.from_string(
        "Joint conference of ACL and LREC (hypothetical)"
    )
    parent = Collection("2092.acl", CollectionIndexStub(anthology), Path("."))
    volume = Volume(
        "1",
        parent,
        type=VolumeType.PROCEEDINGS,
        booktitle=volume_title,
        venue_ids=["acl", "lrec"],
        year="2092",
    )
    assert volume.full_id == "2092.acl-1"
    assert volume.title == volume_title
    assert volume.venue_ids == ["acl", "lrec"]
    assert volume.venue_acronym == "ACL-LREC"


def test_volume_get_events(anthology):
    volume = anthology.get_volume("2022.acl-demo")
    assert volume.get_events() == [anthology.events["acl-2022"]]


def test_volume_get_sigs(anthology):
    volume = anthology.get_volume("2022.acl-demo")
    assert volume.get_sigs() == [anthology.sigs["sigdat"]]
    volume = anthology.get_volume("2022.acl-long")
    assert volume.get_sigs() == []


def test_volume_change_id(anthology):
    volume = anthology.get_volume("2022.acl-demo")
    volume.id = "demonstration"  # okay
    volume.id = "demo2"  # okay
    volume.id = "42"  # okay

    with pytest.raises(ValueError):
        volume.id = "demo-2"  # invalid format

    # BUT: currently no automatic check if ID already exists, so this works
    volume.id = "long"


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


def test_volume_generate_paper_id(anthology):
    volume = anthology.get_volume("2022.acl-long")
    # Highest paper ID in 2022.acl-long is 603
    assert volume.generate_paper_id() == "604"
    # Calling this repeatedly will generate the same ID
    assert volume.generate_paper_id() == "604"
    # Adding a Paper with this ID should then generate the next-higher one
    volume.create_paper(
        id="604",
        bibkey="my-awesome-paper",
        title="The awesome paper I have never written",
    )
    assert volume.generate_paper_id() == "605"


def test_volume_create_paper_implicit(anthology):
    volume = anthology.get_volume("2022.acl-long")
    assert not volume.collection.is_modified
    authors = [NameSpec("Bollmann, Marcel")]
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
        ingest_date="2025-01-07",
    )
    assert volume.collection.is_modified
    assert paper.authors == authors
    assert paper.title.as_text() == "The awesome paper I have never written"
    assert paper.ingest_date == "2025-01-07"
    assert paper.parent is volume
    assert paper.id in volume
    # Highest paper ID in 2022.acl-long is 603, so this one should automatically get 604
    assert paper.id == "604"
    assert paper.full_id == "2022.acl-long.604"
    # Bibkey should automatically have been generated
    assert paper.bibkey == "bollmann-2022-awesome"


def test_volume_create_paper_explicit(anthology):
    volume = anthology.get_volume("2022.acl-long")
    assert not volume.collection.is_modified
    authors = [NameSpec("Bollmann, Marcel")]
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
        ingest_date="2025-01-07",
        id="701",
        bibkey="bollmann-2022-the-awesome",
    )
    assert volume.collection.is_modified
    assert paper.authors == authors
    assert paper.title.as_text() == "The awesome paper I have never written"
    assert paper.ingest_date == "2025-01-07"
    assert paper.parent is volume
    assert paper.id in volume
    assert paper.id == "701"
    assert paper.full_id == "2022.acl-long.701"
    assert paper.bibkey == "bollmann-2022-the-awesome"


def test_volume_create_paper_with_duplicate_id_should_fail(anthology):
    volume = anthology.get_volume("2022.acl-long")
    authors = [NameSpec("Bollmann, Marcel")]
    with pytest.raises(ValueError):
        _ = volume.create_paper(
            title="The awesome paper I have never written",
            authors=authors,
            id="42",
        )


def test_volume_create_paper_should_parse_markup(anthology):
    volume = anthology.get_volume("2022.acl-long")
    authors = [NameSpec("Bollmann, Marcel")]
    paper = volume.create_paper(
        title="Towards $\\infty$",
        authors=authors,
    )
    assert paper.title.as_text() == "Towards ∞"


def test_volume_create_paper_with_editors(anthology):
    volume = anthology.get_volume("2022.acl-long")

    # For most papers, the editors are the volume's editors
    authors = [NameSpec("Bollmann, Marcel")]
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
    )
    assert not paper.editors
    assert paper.get_editors() == volume.editors

    # But the schema allows paper-level editors too
    editors = [NameSpec("Calzolari, Nicoletta")]
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
        editors=editors,
        ingest_date="2025-01-07",
    )
    assert paper.editors == editors
    assert paper.get_editors() == editors


@pytest.mark.parametrize("pre_load", (True, False))
def test_volume_create_paper_should_update_person(anthology, pre_load):
    if pre_load:
        anthology.people.load()  # otherwise we test creation, not updating

    volume = anthology.get_volume("2022.acl-long")
    authors = [NameSpec("Berg-Kirkpatrick, Taylor")]
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
        ingest_date="2025-01-07",
    )
    assert paper.authors == authors

    # Paper should have been added to the person object
    person = authors[0].resolve()
    assert paper.full_id_tuple in person.item_ids


@pytest.mark.parametrize("pre_load", (True, False))
def test_volume_create_paper_should_update_personindex(anthology, pre_load):
    if pre_load:
        anthology.people.load()  # otherwise we test creation, not updating

    volume = anthology.get_volume("2022.acl-long")
    authors = [NameSpec("Nonexistant, Guy Absolutely")]
    paper = volume.create_paper(
        title="An entirely imaginary paper",
        authors=authors,
        ingest_date="2025-01-07",
    )
    assert paper.authors == authors

    # New author should exist in the author index
    person = authors[0].resolve()
    assert paper.full_id_tuple in person.item_ids


def test_volume_remove_editor(anthology):
    volume = anthology.get_volume("2022.acl-long")
    ns = volume.editors[1]
    person = ns.resolve()
    assert person.id == UNVERIFIED_PID_FORMAT.format(pid="preslav-nakov")
    assert volume.full_id_tuple in person.item_ids

    # Removing editor from volume
    volume.editors = [volume.editors[0], volume.editors[2]]
    # Person should be updated after resetting indices
    anthology.reset_indices()
    person = ns.resolve()
    assert volume.full_id_tuple not in person.item_ids


def test_volume_add_editor(anthology):
    volume = anthology.get_volume("2022.acl-long")
    # This person exists, but is not an editor on this volume
    ns = NameSpec("Rada Mihalcea")
    assert ns not in volume.editors
    person = anthology.people.get_by_namespec(ns)
    assert volume.full_id_tuple not in person.item_ids

    # Adding this editor to the volume
    volume.editors += [ns]
    # Person should be updated after resetting indices
    anthology.reset_indices()
    person = ns.resolve()
    assert volume.full_id_tuple in person.item_ids


def test_volume_get_namespec_for(anthology):
    volume = anthology.get_volume("2022.acl-demo")
    person = volume.editors[1].resolve()
    namespec = volume.get_namespec_for(person)
    assert person.has_name(namespec.name)
    assert namespec.resolve() is person


def test_volume_type_conversion():
    parent = Collection("L05", None, Path("."))
    volume = Volume(
        6,
        parent,
        type="journal",
        booktitle="Lorem ipsum",
        year=2005,
    )
    assert volume.id == "6"  # str
    assert volume.full_id == "L05-6"
    assert isinstance(volume.title, MarkupText)
    assert volume.year == "2005"
    assert volume.type == VolumeType.JOURNAL


def test_volume_type_validation():
    volume_title = MarkupText.from_string("Lorem ipsum")
    parent = Collection("L05", None, Path("."))
    volume = Volume(
        "6",
        parent,
        type=VolumeType.JOURNAL,
        booktitle=volume_title,
        year="2005",
    )
    with pytest.raises(TypeError):
        volume.doi = 42
    with pytest.raises(TypeError):
        volume.venue_ids = "lrec"
    with pytest.raises(TypeError):
        volume.pdf = "L05-6000.pdf"
