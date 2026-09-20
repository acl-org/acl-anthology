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
from acl_anthology.files import PDFReference, URLReference
from acl_anthology.people import (
    Name,
    NameSpecification as NameSpec,
    UNVERIFIED_PID_FORMAT,
)
from acl_anthology.text import MarkupText
from acl_anthology.utils.xml import indent


class CollectionIndexStub:
    def __init__(self, parent):
        self.parent = parent


test_cases_volume_xml = (
    """<volume id="long" type="proceedings" ingest-date="2022-05-15">
  <!-- https://aclanthology.org/2026.dummy-long/ -->
  <meta>
    <booktitle>Proceedings of the 60th Annual Fabricated Meeting on Computational Linguistics (Volume 1: Long Papers)</booktitle>
    <editor><first>Selin</first><last>Aksoy</last></editor>
    <editor><first>Dario</first><last>Pretto</last></editor>
    <editor><first>Nadia</first><last>Ferris</last></editor>
    <publisher>Association for Computational Linguistics</publisher>
    <address>Porto, Portugal</address>
    <month>May</month>
    <year>2022</year>
    <pdf hash="b8317652"/>
    <url type="website">https://2022.facl-conf.example.org</url>
    <url type="handbook">https://2022.facl-conf.example.org/handbook.pdf</url>
    <venue>facl</venue>
  </meta>
  <frontmatter>
    <!-- https://aclanthology.org/2026.dummy-long.0/ -->
    <pdf hash="56ea4e43"/>
    <bibkey>facl-2022-long</bibkey>
  </frontmatter>
</volume>
""",
    """<volume id="demo" type="proceedings" ingest-date="2022-05-15">
  <!-- https://aclanthology.org/2026.dummy-demo/ -->
  <meta>
    <booktitle>Proceedings of the 60th Annual Fabricated Meeting on Computational Linguistics: System Demonstrations</booktitle>
    <editor><first>Petro</first><last>Ilyash</last></editor>
    <editor><first>Noor</first><last>Haddad</last></editor>
    <editor><first>Farah</first><last>Kildal</last></editor>
    <publisher>Association for Computational Linguistics</publisher>
    <address>Porto, Portugal</address>
    <doi>10.18653/v1/2022.facl-demo</doi>
    <month>May</month>
    <year>2022</year>
    <pdf hash="d92e3f4d"/>
    <venue>facl</venue>
  </meta>
  <frontmatter>
    <!-- https://aclanthology.org/2026.dummy-demo.0/ -->
    <pdf hash="ad64a7d9"/>
    <bibkey>facl-2022-demo</bibkey>
  </frontmatter>
</volume>
""",
    """<volume id="1" type="journal">
  <!-- https://aclanthology.org/2026.dummy-1/ -->
  <meta>
    <booktitle>Journal of Fabricated Computational Linguistics, Volume 15, Number 1, March 1989</booktitle>
    <year>1989</year>
    <venue>fcl</venue>
    <journal-volume>15</journal-volume>
    <journal-issue>1</journal-issue>
  </meta>
  <frontmatter>
    <!-- https://aclanthology.org/2026.dummy-1.0/ -->
    <pdf hash="363084f8"/>
    <bibkey>fcl-1989-linguistics</bibkey>
  </frontmatter>
  <paper id="1">
    <!-- https://aclanthology.org/2026.dummy-1.1/ -->
    <title>Bracketing with Elastic Alignment, Adaptive Heuristics, and Analogy in Mind</title>
    <author><first>Elena</first><last>Voss</last></author>
    <pages>1-18</pages>
    <pdf hash="ad57020c"/>
    <bibkey>voss-1989-bracketing</bibkey>
  </paper>
</volume>
""",
    """<volume id="4" type="journal">
  <!-- https://aclanthology.org/2026.dummy-4/ -->
  <meta>
    <booktitle>American Journal of Fabricated Computational Linguistics (November 1975)</booktitle>
    <editor><first>Halvard</first><last>Reyes</last></editor>
    <month>November</month>
    <year>1975</year>
    <venue>fcl</venue>
    <journal-title>American Journal of Fabricated Computational Linguistics</journal-title>
  </meta>
</volume>
""",
    """<volume id="75" type="proceedings" ingest-date="2019-10-16">
  <!-- https://aclanthology.org/2026.dummy-75/ -->
  <meta>
    <booktitle>Proceedings of the 6th International Fabricated Computational Linguistics Symposium</booktitle>
    <shortbooktitle>6th IFCLS</shortbooktitle>
    <editor><first>Priya</first><last>Nkemelu</last></editor>
    <publisher>Association for Computational Linguistics</publisher>
    <address>Fakerhausen, Elsewhere</address>
    <month>October</month>
    <year>2019</year>
    <pdf hash="48102019"/>
    <venue>fcl</venue>
  </meta>
</volume>
""",
)


def test_volume_minimum_attribs(anthology):
    parent = Collection("L05", CollectionIndexStub(anthology), Path("."))
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
    assert volume.ingest_date.year == 1900
    assert not volume.is_workshop


def test_volume_all_attribs(anthology):
    parent = Collection("2023.acl", CollectionIndexStub(anthology), Path("."))
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
        venue_ids=["li", "facl"],
    )
    assert volume.ingest_date == date(2023, 1, 12)


def test_volume_attributes_2022acl_long(anthology):
    volume = anthology.get_volume("2022.facl-long")
    assert isinstance(volume, Volume)
    assert volume.id == "long"
    assert volume.ingest_date == date(2022, 5, 15)
    assert volume.address == "Porto, Portugal"
    assert volume.publisher == "Association for Computational Linguistics"
    assert volume.doi is None
    assert volume.month == "May"
    assert volume.year == "2022"
    assert volume.pdf.name == "2022.facl-long"
    assert volume.pdf.checksum == "b8317652"
    assert volume.venue_ids == ("facl",)
    assert volume.venue_acronym == "FACL"
    assert not volume.is_workshop
    assert isinstance(volume.frontmatter, Paper) and volume.frontmatter.id == "0"


def test_volume_attributes_2022acl_demo(anthology):
    volume = anthology.get_volume("2022.facl-demo")
    assert isinstance(volume, Volume)
    assert volume.id == "demo"
    assert volume.ingest_date == date(2022, 5, 15)
    assert volume.address == "Porto, Portugal"
    assert volume.publisher == "Association for Computational Linguistics"
    assert volume.doi == "10.18653/v1/2022.facl-demo"
    assert volume.month == "May"
    assert volume.year == "2022"
    assert volume.pdf.name == "2022.facl-demo"
    assert volume.pdf.checksum == "d92e3f4d"
    assert volume.venue_ids == ("facl",)
    assert volume.venue_acronym == "FACL"
    assert not volume.is_workshop
    assert isinstance(volume.frontmatter, Paper) and volume.frontmatter.id == "0"
    assert len(volume.editors) == 3
    assert volume.editors == volume.namespecs


def test_volume_attributes_j89(anthology):
    volume = anthology.get_volume("Q89-1")
    assert isinstance(volume, Volume)
    assert volume.id == "1"
    assert volume.venue_ids == ("fcl",)
    assert volume.venue_acronym == "FCL"
    assert volume.year == "1989"
    assert not volume.is_workshop
    assert volume.type == VolumeType.JOURNAL
    assert volume.journal_issue == "1"
    assert volume.journal_volume == "15"
    assert volume.journal_title == "Journal of Fabricated Computational Linguistics"
    assert isinstance(volume.frontmatter, Paper) and volume.frontmatter.id == "0"


def test_volume_attributes_natfake(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    assert isinstance(volume, Volume)
    assert volume.id == "1"
    assert volume.year == "2022"
    assert volume.is_workshop
    assert volume.venue_ids == ("natfake", "ws")
    assert volume.venue_acronym == "NATFAKE"
    assert isinstance(volume.frontmatter, Paper) and volume.frontmatter.id == "0"


def test_volume_without_frontmatter(anthology):
    volume = anthology.get_volume("Q89-3")
    assert isinstance(volume, Volume)
    assert volume.frontmatter is None


def test_volume_explicit_journal_title(anthology):
    volume = anthology.get_volume("Q89-4")
    assert isinstance(volume, Volume)
    assert volume._journal_title is not None
    assert volume.journal_title == volume._journal_title
    volume.journal_title = "Journal of Fabricated Computational Linguistics"
    assert volume._journal_title == "Journal of Fabricated Computational Linguistics"


def test_volume_set_ingest_date(anthology):
    volume = anthology.get_volume("2022.facl-demo")
    volume.ingest_date = "2025-07-15"
    assert volume.ingest_date == date(2025, 7, 15)
    volume.ingest_date = date(2026, 3, 1)
    assert volume.ingest_date == date(2026, 3, 1)


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
    volume = anthology.get_volume("2022.facl-long")
    assert not volume.parent.is_modified
    setattr(volume, attr_name, getattr(volume, attr_name))
    assert volume.parent.is_modified


def test_paper_setattr_on_namespec_sets_collection_is_modified(anthology):
    volume = anthology.get_volume("2022.facl-long")
    assert not volume.collection.is_modified
    volume.editors[0].affiliation = "University of Someplace"
    assert volume.collection.is_modified


def test_volume_venues_j89(anthology):
    volume = anthology.get_volume("Q89-1")
    assert volume.venue_ids == ("fcl",)
    venues = volume.venues()
    assert len(venues) == 1
    assert venues[0].id == "fcl"


def test_volume_venues_natfake(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    assert volume.venue_ids == ("natfake", "ws")
    venues = volume.venues()
    assert len(venues) == 2
    assert venues[0].id == "natfake"
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
    parent = Collection("2092.facl", CollectionIndexStub(anthology), Path("."))
    volume = Volume(
        "1",
        parent,
        type=VolumeType.PROCEEDINGS,
        booktitle=volume_title,
        venue_ids=["facl", "flrec"],
        year="2092",
    )
    assert volume.full_id == "2092.facl-1"
    assert volume.title == volume_title
    assert volume.venue_ids == ("facl", "flrec")
    assert volume.venue_acronym == "FACL-FLREC"


def test_volume_get_events(anthology):
    volume = anthology.get_volume("2022.facl-demo")
    assert volume.get_events() == [anthology.events["facl-2022"]]


def test_volume_get_sigs(anthology):
    volume = anthology.get_volume("2022.facl-demo")
    assert volume.get_sigs() == [anthology.sigs["sigfake1"]]
    volume = anthology.get_volume("2022.facl-long")
    assert volume.get_sigs() == []


def test_volume_change_id(anthology):
    volume = anthology.get_volume("2022.facl-demo")
    volume.id = "demonstration"  # okay
    volume.id = "demo2"  # okay
    volume.id = "42"  # okay

    with pytest.raises(ValueError):
        volume.id = "demo-2"  # invalid format

    # BUT: currently no automatic check if ID already exists, so this works
    volume.id = "long"


def test_volume_add_sig_updates_sig(anthology):
    volume = anthology.get_volume("2022.facl-long")
    sigfake1 = anthology.sigs["sigfake1"]
    assert volume.full_id_tuple not in sigfake1.item_ids

    # Add a SIG to this volume
    volume.sig_ids = ("sigfake1",)

    # SIG should be updated
    assert volume.full_id_tuple in sigfake1.item_ids


def test_volume_remove_sig_updates_sig(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    sigfake1 = anthology.sigs["sigfake1"]
    sigfake2 = anthology.sigs["sigfake2"]
    assert volume.full_id_tuple in sigfake1.item_ids
    assert volume.full_id_tuple in sigfake2.item_ids

    # Remove a SIG from this volume
    volume.sig_ids = ("sigfake2",)

    # SIGs should be updated
    assert volume.full_id_tuple in sigfake2.item_ids
    assert volume.full_id_tuple not in sigfake1.item_ids


def test_volume_add_sig_raises(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    anthology.sigs.load()
    with pytest.raises(ValueError):
        # Adding a SIG to this volume that doesn't exist
        volume.sig_ids += ("doesntexist",)


def test_volume_add_sig_by_id(anthology):
    volume = anthology.get_volume("2022.facl-long")
    sigfake1 = anthology.sigs["sigfake1"]
    assert "sigfake1" not in volume.sig_ids
    assert volume.full_id_tuple not in sigfake1.item_ids

    volume.add_sig("sigfake1")

    assert volume.sig_ids == ("sigfake1",)
    assert volume.full_id_tuple in sigfake1.item_ids


def test_volume_add_sig_by_object(anthology):
    volume = anthology.get_volume("2022.facl-long")
    sigfake1 = anthology.sigs["sigfake1"]
    assert "sigfake1" not in volume.sig_ids

    volume.add_sig(sigfake1)

    assert volume.sig_ids == ("sigfake1",)
    assert volume.full_id_tuple in sigfake1.item_ids


def test_volume_add_sig_already_present_is_noop(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    assert "sigfake1" in volume.sig_ids

    volume.add_sig("sigfake1")

    assert volume.sig_ids.count("sigfake1") == 1


def test_volume_add_sig_nonexistent_raises(anthology):
    volume = anthology.get_volume("2022.facl-long")
    anthology.sigs.load()
    with pytest.raises(ValueError):
        volume.add_sig("doesntexist")


def test_volume_remove_sig_by_id(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    sigfake1 = anthology.sigs["sigfake1"]
    assert "sigfake1" in volume.sig_ids
    assert volume.full_id_tuple in sigfake1.item_ids

    volume.remove_sig("sigfake1")

    assert "sigfake1" not in volume.sig_ids
    assert volume.full_id_tuple not in sigfake1.item_ids


def test_volume_remove_sig_by_object(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    sigfake2 = anthology.sigs["sigfake2"]
    assert "sigfake2" in volume.sig_ids

    volume.remove_sig(sigfake2)

    assert "sigfake2" not in volume.sig_ids
    assert volume.full_id_tuple not in sigfake2.item_ids


def test_volume_remove_sig_not_present_is_noop(anthology):
    volume = anthology.get_volume("2022.facl-long")
    assert volume.sig_ids == ()

    volume.remove_sig("sigfake1")

    assert volume.sig_ids == ()


def test_volume_add_venue_updates_venue(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    natfake = anthology.venues["natfake"]
    humfake = anthology.venues["humfake"]
    assert volume.full_id_tuple in natfake.item_ids
    assert volume.full_id_tuple not in humfake.item_ids

    # Adding a venue to this volume
    volume.venue_ids += ("humfake",)

    # Venues should be updated
    assert volume.full_id_tuple in natfake.item_ids
    assert volume.full_id_tuple in humfake.item_ids


def test_volume_add_venue_raises(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    anthology.venues.load()
    with pytest.raises(ValueError):
        # Adding a venue to this volume that doesn't exist
        volume.venue_ids += ("doesntexist",)


def test_volume_add_venue_creates_event(anthology):
    # NOTE: this volume also picks up "facl-2022" here, because 2022.facl.xml's
    # own event lists this volume's collection ("2022.natfake-1") explicitly
    # under its <colocated> tag.
    volume = anthology.get_volume("2022.natfake-1")
    events = anthology.events.by_volume(volume)
    assert set(ev.id for ev in events) == {"ws-2022", "natfake-2022", "facl-2022"}
    assert "humfake-2022" not in anthology.events

    # Adding a venue to this volume
    volume.venue_ids += ("humfake",)

    # Events should be updated
    events = anthology.events.by_volume(volume)
    assert set(ev.id for ev in events) == {
        "ws-2022",
        "humfake-2022",
        "natfake-2022",
        "facl-2022",
    }
    assert "humfake-2022" in anthology.events


def test_volume_remove_venue_updates_venue(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    natfake = anthology.venues["natfake"]
    assert volume.full_id_tuple in natfake.item_ids

    # Removing a venue from this volume
    volume.venue_ids = ("ws",)

    # Venue should be updated
    assert volume.full_id_tuple not in natfake.item_ids


def test_volume_remove_venue_updates_event(anthology):
    volume = anthology.get_volume("2022.natfake-1")

    # Removing a venue from this volume
    volume.venue_ids = ("ws",)

    # Events should be updated; "facl-2022" remains because it explicitly
    # co-locates this volume regardless of its declared venues.
    events = anthology.events.by_volume(volume)
    assert set(ev.id for ev in events) == {"ws-2022", "facl-2022"}


def test_volume_add_venue_by_id(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    humfake = anthology.venues["humfake"]
    assert "humfake" not in volume.venue_ids
    assert volume.full_id_tuple not in humfake.item_ids

    volume.add_venue("humfake")

    assert "humfake" in volume.venue_ids
    assert volume.full_id_tuple in humfake.item_ids


def test_volume_add_venue_by_object(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    humfake = anthology.venues["humfake"]
    assert "humfake" not in volume.venue_ids

    volume.add_venue(humfake)

    assert "humfake" in volume.venue_ids
    assert volume.full_id_tuple in humfake.item_ids


def test_volume_add_venue_already_present_is_noop(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    assert "natfake" in volume.venue_ids

    volume.add_venue("natfake")

    assert volume.venue_ids.count("natfake") == 1


def test_volume_add_venue_nonexistent_raises(anthology):
    volume = anthology.get_volume("2022.facl-long")
    anthology.venues.load()
    with pytest.raises(ValueError):
        volume.add_venue("doesntexist")


def test_volume_remove_venue_by_id(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    natfake = anthology.venues["natfake"]
    assert "natfake" in volume.venue_ids
    assert volume.full_id_tuple in natfake.item_ids

    volume.remove_venue("natfake")

    assert "natfake" not in volume.venue_ids
    assert volume.full_id_tuple not in natfake.item_ids


def test_volume_remove_venue_by_object(anthology):
    volume = anthology.get_volume("2022.natfake-1")
    ws = anthology.venues["ws"]
    assert "ws" in volume.venue_ids

    volume.remove_venue(ws)

    assert "ws" not in volume.venue_ids
    assert volume.full_id_tuple not in ws.item_ids


def test_volume_remove_venue_not_present_is_noop(anthology):
    volume = anthology.get_volume("2022.facl-long")
    assert volume.venue_ids == ("facl",)

    volume.remove_venue("humfake")

    assert volume.venue_ids == ("facl",)


@pytest.mark.parametrize("xml", test_cases_volume_xml)
def test_volume_roundtrip_xml(xml, anthology):
    # Create and populate volume
    volume_element = etree.fromstring(xml)
    meta = volume_element.find("meta")
    parent = Collection("2026.dummy", CollectionIndexStub(anthology), Path("."))
    volume = Volume.from_xml(parent, meta)
    for child in volume_element:
        if child.tag in ("frontmatter", "paper"):
            volume._add_paper_from_xml(child)
    # Serialize and compare
    out = volume.to_xml()
    indent(out)
    assert etree.tostring(out, encoding="unicode") == xml


def test_volume_generate_paper_id(anthology):
    volume = anthology.get_volume("2022.facl-long")
    # Highest paper ID in 2022.facl-long is 601
    assert volume.generate_paper_id() == "602"
    # Calling this repeatedly will generate the same ID
    assert volume.generate_paper_id() == "602"
    # Adding a Paper with this ID should then generate the next-higher one
    volume.create_paper(
        id="602",
        bibkey="my-awesome-paper",
        title="The awesome paper I have never written",
    )
    assert volume.generate_paper_id() == "603"


def test_volume_create_paper_implicit(anthology):
    volume = anthology.get_volume("2022.facl-long")
    assert not volume.collection.is_modified
    authors = (NameSpec("Fenwick, Alex"),)
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
        ingest_date="2025-01-07",
    )
    assert volume.collection.is_modified
    assert paper.authors == authors
    assert paper.title.as_text() == "The awesome paper I have never written"
    assert paper.ingest_date.isoformat() == "2025-01-07"
    assert paper.parent is volume
    assert paper.id in volume
    # Highest paper ID in 2022.facl-long is 601, so this one should automatically get 602
    assert paper.id == "602"
    assert paper.full_id == "2022.facl-long.602"
    # Bibkey should automatically have been generated
    assert paper.bibkey == "fenwick-2022-awesome"


def test_volume_create_paper_explicit(anthology):
    volume = anthology.get_volume("2022.facl-long")
    assert not volume.collection.is_modified
    authors = (NameSpec("Fenwick, Alex"),)
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
        ingest_date="2025-01-07",
        id="701",
        bibkey="fenwick-2022-the-awesome",
    )
    assert volume.collection.is_modified
    assert paper.authors == authors
    assert paper.title.as_text() == "The awesome paper I have never written"
    assert paper.ingest_date.isoformat() == "2025-01-07"
    assert paper.parent is volume
    assert paper.id in volume
    assert paper.id == "701"
    assert paper.full_id == "2022.facl-long.701"
    assert paper.bibkey == "fenwick-2022-the-awesome"


@pytest.mark.parametrize(
    "before, after",
    (
        (("John C.s.", "Lui"), ("John C.S.", "Lui")),
        (("Santosh", "T.y.s.s"), ("Santosh", "T.Y.S.S")),
        ((None, "S.b.priya"), (None, "S.B.Priya")),
    ),
)
def test_volume_create_paper_case_normalizes_author_names(before, after, anthology):
    volume = anthology.get_volume("2022.facl-long")
    authors = (NameSpec(Name(*before)),)
    paper = volume.create_paper(
        title="Paper with normalized author initials",
        authors=authors,
    )
    assert paper.authors[0].name == authors[0].name == Name(*after)


def test_volume_create_paper_with_duplicate_id_should_fail(anthology):
    volume = anthology.get_volume("2022.facl-long")
    authors = (NameSpec("Fenwick, Alex"),)
    with pytest.raises(ValueError):
        _ = volume.create_paper(
            title="The awesome paper I have never written",
            authors=authors,
            id="42",
        )


def test_volume_create_paper_should_parse_markup(anthology):
    volume = anthology.get_volume("2022.facl-long")
    authors = [NameSpec("Fenwick, Alex")]
    paper = volume.create_paper(
        title="Towards $\\infty$",
        authors=authors,
    )
    assert paper.title.as_text() == "Towards ∞"


def test_volume_create_paper_with_editors(anthology):
    volume = anthology.get_volume("2022.facl-long")

    # For most papers, the editors are the volume's editors
    authors = (NameSpec("Fenwick, Alex"),)
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
    )
    assert not paper._editors
    assert paper.editors == volume.editors

    # But the schema allows paper-level editors too
    editors = (NameSpec("Lindholm, Petra"),)
    paper = volume.create_paper(
        title="The awesome paper I have never written",
        authors=authors,
        editors=editors,
        ingest_date="2025-01-07",
    )
    assert paper.editors == editors


def test_volume_create_paper_with_existing_explicit_author(anthology):
    volume = anthology.get_volume("2022.facl-long")

    authors = [NameSpec("Fenwick, Alex", orcid="0009-0001-4567-8902")]
    paper = volume.create_paper(
        title="New paper by existing author",
        authors=authors,
    )
    assert (person := anthology.people.get_by_orcid("0009-0001-4567-8902")) is not None
    assert paper.authors[0].id == "alex-fenwick"
    assert paper.authors[0].resolve() is person
    assert paper.full_id_tuple in person.item_ids


@pytest.mark.parametrize("name", ("Tånnander, Christina", "tånnander, christina"))
def test_volume_create_paper_with_new_explicit_author(name, anthology):
    volume = anthology.get_volume("2022.facl-long")
    assert "christina-tannander" not in anthology.people

    authors = [NameSpec(name, orcid="0000-0002-9659-1532")]
    paper = volume.create_paper(
        title="First paper by new author",
        authors=authors,
    )
    assert (person := anthology.people.get_by_orcid("0000-0002-9659-1532")) is not None
    assert person.canonical_name == Name.from_(
        "Tånnander, Christina"
    )  # always the case-normalized version
    assert paper.authors[0].id == "christina-tannander"
    assert paper.authors[0].resolve() is person
    assert person.item_ids == set([paper.full_id_tuple])


@pytest.mark.parametrize("pre_load", (True, False))
def test_volume_create_paper_should_update_person(anthology, pre_load):
    if pre_load:
        anthology.people.load()  # otherwise we test creation, not updating

    volume = anthology.get_volume("2022.facl-long")
    authors = (NameSpec("Berg-Kirkpatrick, Taylor"),)
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

    volume = anthology.get_volume("2022.facl-long")
    authors = (NameSpec("Nonexistant, Guy Absolutely"),)
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
    volume = anthology.get_volume("2022.facl-long")
    ns = volume.editors[1]
    person = ns.resolve()
    assert person.id == UNVERIFIED_PID_FORMAT.format(pid="dario-pretto")
    assert volume.full_id_tuple in person.item_ids

    # Removing editor from volume
    volume.editors = [volume.editors[0], volume.editors[2]]

    # Person should be updated
    assert volume.full_id_tuple not in person.item_ids


def test_volume_add_editor(anthology):
    volume = anthology.get_volume("2022.facl-long")
    # This person exists, but is not an editor on this volume
    ns = NameSpec("Livia Marchetti")
    assert ns not in volume.editors
    person = anthology.people.get_by_namespec(ns)
    assert volume.full_id_tuple not in person.item_ids

    # Adding this editor to the volume
    volume.editors += (ns,)

    # NameSpecification should point to volume
    assert ns.parent is volume
    # Person should be updated
    assert volume.full_id_tuple in person.item_ids


def test_volume_get_namespec_for(anthology):
    volume = anthology.get_volume("2022.facl-demo")
    person = volume.editors[1].resolve()
    namespec = volume.get_namespec_for(person)
    assert person.has_name(namespec.name)
    assert namespec.resolve() is person


def test_volume_get_namespec_for_should_fail(anthology):
    volume = anthology.get_volume("2022.facl-demo")
    person = anthology.get_person("matt-post")
    with pytest.raises(ValueError):
        volume.get_namespec_for(person)


def test_volume_type_conversion(anthology):
    parent = Collection("L05", CollectionIndexStub(anthology), Path("."))
    volume = Volume(
        6,
        parent,
        type="journal",
        booktitle="Lorem ipsum",
        journal_title="Foo bar",
        year=2005,
    )
    assert volume.id == "6"  # str
    assert volume.full_id == "L05-6"
    assert isinstance(volume.title, MarkupText)
    assert volume.year == "2005"
    assert volume.type == VolumeType.JOURNAL


def test_volume_type_validation(anthology):
    volume_title = MarkupText.from_string("Lorem ipsum")
    parent = Collection("L05", CollectionIndexStub(anthology), Path("."))
    volume = Volume(
        "6",
        parent,
        type=VolumeType.JOURNAL,
        booktitle=volume_title,
        journal_title="Foo bar",
        year="2005",
    )
    with pytest.raises(TypeError):
        volume.doi = 42
    with pytest.raises(TypeError):
        volume.venue_ids = "lrec"
    with pytest.raises(TypeError):
        volume.pdf = "L05-6000.pdf"


def test_volume_pdf_must_be_local(anthology):
    volume_title = MarkupText.from_string("Lorem ipsum")
    parent = Collection("L05", CollectionIndexStub(anthology), Path("."))
    with pytest.raises(ValueError, match="must be a local file reference"):
        Volume(
            "6",
            parent,
            type=VolumeType.JOURNAL,
            booktitle=volume_title,
            journal_title="Foo bar",
            year="2005",
            pdf=PDFReference("https://external.com/volume.pdf"),
        )
    volume = Volume(
        "6",
        parent,
        type=VolumeType.JOURNAL,
        booktitle=volume_title,
        journal_title="Foo bar",
        year="2005",
    )
    with pytest.raises(ValueError, match="must be a local file reference"):
        volume.pdf = PDFReference("https://external.com/volume.pdf")


def test_volume_pdf_name_must_match_full_id_if_given(anthology):
    volume_title = MarkupText.from_string("Lorem ipsum")
    parent = Collection("L05", CollectionIndexStub(anthology), Path("."))
    with pytest.raises(ValueError, match="does not match"):
        Volume(
            "6",
            parent,
            type=VolumeType.JOURNAL,
            booktitle=volume_title,
            journal_title="Foo bar",
            year="2005",
            pdf=PDFReference("wrong-name", checksum="abcd1234"),
        )
    volume = Volume(
        "6",
        parent,
        type=VolumeType.JOURNAL,
        booktitle=volume_title,
        journal_title="Foo bar",
        year="2005",
    )
    assert volume.full_id == "L05-6"
    with pytest.raises(ValueError, match="does not match"):
        volume.pdf = PDFReference("wrong-name", checksum="abcd1234")
    # ...but an empty name, or one that already matches full_id, is accepted
    volume.pdf = PDFReference("", checksum="abcd1234")
    assert volume.pdf.name == "L05-6"
    volume.pdf = PDFReference("L05-6", checksum="abcd1234")
    assert volume.pdf.name == "L05-6"


def test_volume_urls_must_be_non_local(anthology):
    volume_title = MarkupText.from_string("Lorem ipsum")
    parent = Collection("L05", CollectionIndexStub(anthology), Path("."))
    with pytest.raises(ValueError, match="must only contain non-local"):
        Volume(
            "6",
            parent,
            type=VolumeType.JOURNAL,
            booktitle=volume_title,
            journal_title="Foo bar",
            year="2005",
            urls=[("website", URLReference("some-local-filename"))],
        )
    volume = Volume(
        "6",
        parent,
        type=VolumeType.JOURNAL,
        booktitle=volume_title,
        journal_title="Foo bar",
        year="2005",
    )
    with pytest.raises(ValueError, match="must only contain non-local"):
        volume.urls = [("website", URLReference("some-local-filename"))]
    # Sanity check: non-local URLs are fine
    volume.urls = [("website", URLReference("https://example.com"))]
    assert volume.urls[0][1].name == "https://example.com"
