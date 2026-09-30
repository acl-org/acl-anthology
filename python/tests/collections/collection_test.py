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

import filecmp
import pytest
from lxml import etree
from pathlib import Path

from acl_anthology import Anthology
from acl_anthology.collections import (
    Collection,
    CollectionIndex,
    EventLink,
    VolumeType,
)
from acl_anthology.people import Name, NameSpecification
from acl_anthology.utils import xml
from acl_anthology.text import MarkupText

test_cases_xml_collections = (
    # (filename, # volumes, # papers, has event?)
    ("2022.facl.xml", 5, 41, True),
    ("2022.natfake.xml", 1, 10, False),
    ("Q89.xml", 4, 61, False),
    ("K06.xml", 1, 5, False),
)


test_cases_xml_roundtrip = tuple(x[0] for x in test_cases_xml_collections)


@pytest.fixture
def collection_index(anthology):
    return CollectionIndex(parent=anthology)


def test_collection_instantiate_empty(collection_index):
    collection = Collection("2000.empty", parent=collection_index, path=Path("."))
    assert not collection.is_data_loaded
    collection.is_data_loaded = True
    assert isinstance(collection.root, Anthology)
    assert len(list(collection.volumes())) == 0
    assert len(list(collection.papers())) == 0
    assert collection.get_event() is None


def test_collection_should_raise_on_invalid_id(collection_index):
    with pytest.raises(ValueError):
        collection = Collection("2000-empty", parent=collection_index, path=Path("."))

    collection = Collection("2000.empty", parent=collection_index, path=Path("."))
    with pytest.raises(ValueError):
        collection.id = "2099-empty"


@pytest.mark.parametrize(
    "filename, no_volumes, no_papers, has_event", test_cases_xml_collections
)
def test_collection_load(
    collection_index, shared_datadir, filename, no_volumes, no_papers, has_event
):
    infile = shared_datadir / "anthology" / "xml" / filename
    collection = Collection(
        filename.replace(".xml", ""), parent=collection_index, path=infile
    )
    collection.load()
    assert collection.is_data_loaded
    assert len(list(collection.volumes())) == no_volumes
    assert len(list(collection.papers())) == no_papers
    if has_event:
        assert collection.get_event() is not None
    else:
        assert collection.get_event() is None
    assert not collection.is_modified


@pytest.mark.filterwarnings(
    "ignore::ResourceWarning"
)  # lxml doesn't properly close XML file here
def test_collection_load_id_mismatch(collection_index, shared_datadir):
    collection = Collection(
        "2019.emnlp",
        parent=collection_index,
        path=shared_datadir / "anthology" / "xml" / "2022.facl.xml",
    )
    with pytest.raises(ValueError):
        collection.load()


@pytest.mark.parametrize("filename", test_cases_xml_roundtrip)
def test_collection_validate_schema(collection_index, shared_datadir, filename):
    infile = shared_datadir / "anthology" / "xml" / filename
    collection = Collection(
        filename.replace(".xml", ""), parent=collection_index, path=infile
    )
    collection.validate_schema()


@pytest.mark.parametrize("minimal_diff", (True, False))
@pytest.mark.parametrize("filename", test_cases_xml_roundtrip)
def test_collection_roundtrip_save(
    collection_index, shared_datadir, tmp_path, filename, minimal_diff
):
    infile = shared_datadir / "anthology" / "xml" / filename
    outfile = tmp_path / filename
    # Load & save collection
    collection = Collection(
        filename.replace(".xml", ""), parent=collection_index, path=infile
    )
    collection.load()
    collection.save(path=outfile, minimal_diff=minimal_diff)
    # Compare
    assert outfile.is_file()
    if not minimal_diff:
        # Tests for logical equivalence
        expected = etree.parse(collection.path)
        result = etree.parse(outfile)
        xml.assert_equals(result.getroot(), expected.getroot())
    else:
        # Tests for byte-level equivalence
        if not filecmp.cmp(outfile, infile):
            # Assertion failed, but assert on the lines so we see a diff
            with (
                open(outfile, "r", encoding="utf-8") as f,
                open(infile, "r", encoding="utf-8") as g,
            ):
                out_lines, exp_lines = f.readlines(), g.readlines()
            assert exp_lines == out_lines


def test_collection_create_volume_implicit(collection_index):
    collection = collection_index.get("2022.facl")
    assert not collection.is_modified
    volume = collection.create_volume(
        "keynotes",
        title="Keynotes from FACL 2022",
    )
    assert collection.is_modified
    assert volume.id in collection
    assert volume.year == "2022"
    assert volume.id == "keynotes"
    assert volume.title == "Keynotes from FACL 2022"
    assert volume.full_id == "2022.facl-keynotes"
    assert volume.type == VolumeType.PROCEEDINGS


def test_collection_create_volume_explicit(collection_index):
    collection = collection_index.get("1979.fcl")
    assert not collection.is_modified
    volume = collection.create_volume(
        id="99",
        title=MarkupText.from_string("Special Issue"),
        year="1979",
        type="journal",
        journal_issue="99",
        venue_ids=["fcl"],
    )
    assert collection.is_modified
    assert volume.id in collection
    assert volume.year == "1979"
    assert volume.id == "99"
    assert volume.title == "Special Issue"
    assert volume.full_id == "1979.fcl-99"
    assert volume.type == VolumeType.JOURNAL
    assert volume.journal_issue == "99"
    assert "fcl" in volume.venue_ids


def test_collection_create_volume_should_parse_markup(collection_index):
    collection = collection_index.get("2022.facl")
    volume = collection.create_volume("infinity", title="Special issue on $\\infty$")
    assert volume.title.as_text() == "Special issue on ∞"


@pytest.mark.parametrize(
    "before, after",
    (
        (("John C.s.", "Lui"), ("John C.S.", "Lui")),
        (("Santosh", "T.y.s.s"), ("Santosh", "T.Y.S.S")),
        ((None, "S.b.priya"), (None, "S.B.Priya")),
    ),
)
def test_collection_create_volume_case_normalizes_editor_names(
    before, after, collection_index
):
    collection = collection_index.get("2022.facl")
    editors = (NameSpecification(Name(*before)),)
    volume = collection.create_volume(
        "initials",
        title="Volume with normalized editor initials",
        editors=editors,
    )
    assert volume.editors[0].name == editors[0].name == Name(*after)


def test_collection_create_volume_should_fail_in_oldstyle_volumes(collection_index):
    collection = collection_index.get("K06")
    with pytest.raises(ValueError):
        _ = collection.create_volume(
            "keynotes",
            title=MarkupText.from_string("Keynotes from FLREC 2006"),
        )


def test_collection_create_volume_should_fail_if_already_exists(collection_index):
    collection = collection_index.get("2022.facl")
    with pytest.raises(ValueError):
        _ = collection.create_volume(
            "long",
            title=MarkupText.from_string("Long papers from FACL 2022"),
        )


@pytest.mark.parametrize("pre_load", (True, False))
def test_collection_create_volume_should_update_person(anthology, pre_load):
    if pre_load:
        anthology.people.load()  # otherwise we test creation, not updating

    collection = anthology.collections.get("2022.facl")
    editors = (NameSpecification("Livia Marchetti"),)
    volume = collection.create_volume(
        "keynotes",
        title=MarkupText.from_string("Keynotes from FACL 2022"),
        editors=editors,
    )
    assert volume.editors == editors

    # Volume should have been added to the person object
    person = editors[0].resolve()
    assert volume.full_id_tuple in person.item_ids


@pytest.mark.parametrize("pre_load", (True, False))
def test_collection_create_volume_should_update_personindex(anthology, pre_load):
    if pre_load:
        anthology.people.load()  # otherwise we test creation, not updating

    collection = anthology.collections.get("2022.facl")
    editors = (NameSpecification("Nonexistant, Guy Absolutely"),)
    volume = collection.create_volume(
        "keynotes",
        title=MarkupText.from_string("Keynotes from FACL 2022"),
        editors=editors,
    )
    assert volume.editors == editors

    # New editor should exist in the person index
    person = editors[0].resolve()
    assert volume.full_id_tuple in person.item_ids


@pytest.mark.parametrize(
    "pre_load, reset",
    (
        (True, True),
        (True, False),
        (False, False),
        (False, True),
    ),
)
def test_collection_create_volume_should_create_event(anthology, pre_load, reset):
    if pre_load:
        anthology.events.load()  # otherwise we test creation, not updating

    collection = anthology.collections.create("2000.empty")
    volume = collection.create_volume(
        "1",
        title=MarkupText.from_string("Empty volume"),
        venue_ids=["facl"],
    )

    if reset:
        anthology.reset_indices()

    # New implicit event should exist in the event index
    assert "facl-2000" in anthology.events
    assert (
        anthology.events["facl-2000"].colocated_ids.get(volume.full_id_tuple)
        == EventLink.INFERRED
    )
    assert volume.full_id_tuple in anthology.events.reverse
    assert anthology.events.reverse[volume.full_id_tuple] == {"facl-2000"}


@pytest.mark.parametrize(
    "pre_load, reset",
    (
        (True, True),
        (True, False),
        (False, False),
        (False, True),
    ),
)
def test_collection_create_volume_should_update_event(anthology, pre_load, reset):
    if pre_load:
        anthology.events.load()  # otherwise we test creation, not updating

    collection = anthology.collections.get("2022.facl")
    collection.is_data_loaded = True
    volume = collection.create_volume(
        "keynotes",
        title=MarkupText.from_string("Keynotes from FACL 2022"),
        venue_ids=["facl"],
    )

    if reset:
        anthology.reset_indices()

    # New volume should be added to existing event
    assert "facl-2022" in anthology.events
    assert (
        anthology.events["facl-2022"].colocated_ids.get(volume.full_id_tuple)
        == EventLink.INFERRED
    )
    assert volume.full_id_tuple in anthology.events.reverse
    assert anthology.events.reverse[volume.full_id_tuple] == {"facl-2022"}


@pytest.mark.parametrize(
    "pre_load, reset",
    (
        (True, True),
        (True, False),
        (False, False),
        (False, True),
    ),
)
def test_collection_create_volume_should_update_venue(anthology, pre_load, reset):
    if pre_load:
        anthology.venues.load()  # otherwise we test creation, not updating

    collection = anthology.collections.create("2000.empty")
    volume = collection.create_volume(
        "1",
        title=MarkupText.from_string("Empty volume"),
        venue_ids=["facl"],
    )

    if reset:
        anthology.reset_indices()

    # Nev volume should be added to existing venue
    assert volume.full_id_tuple in anthology.venues["facl"].item_ids


@pytest.mark.parametrize(
    "pre_load, reset",
    (
        (True, True),
        (True, False),
        (False, False),
        (False, True),
    ),
)
def test_collection_create_volume_should_update_sig(anthology, pre_load, reset):
    if pre_load:
        anthology.venues.load()  # otherwise we test creation, not updating

    collection = anthology.collections.create("2000.empty")
    volume = collection.create_volume(
        "1",
        title=MarkupText.from_string("Empty volume"),
        sig_ids=["sigfake1"],
    )

    if reset:
        anthology.reset_indices()

    # Nev volume should be added to existing venue
    assert volume.full_id_tuple in anthology.sigs["sigfake1"].item_ids


def test_collection_create_event_oldstyle_ids(collection_index):
    collection = collection_index.get("K06")

    # For old-style ID collections, an ID must be explicitly given
    with pytest.raises(ValueError):
        _ = collection.create_event()

    event = collection.create_event(id="flrec-2006")
    assert event.id == "flrec-2006"

    # Trying to create yet another event in the same collection should raise
    with pytest.raises(ValueError):
        _ = collection.create_event(id="flrecagain-2006")


def test_collection_create_event_newstyle_ids(collection_index):
    collection = collection_index.get("1979.fcl")
    assert not collection.is_modified

    # For new-style ID collections, an explicit event ID is not required
    event = collection.create_event()
    assert collection.is_modified
    assert event.id == "fcl-1979"

    # Trying to create yet another event in the same collection should raise
    with pytest.raises(ValueError):
        _ = collection.create_event(id="fcl-1979")


@pytest.mark.parametrize("pre_load", (True, False))
def test_collection_create_event_should_update_eventindex(pre_load, anthology):
    if pre_load:
        anthology.events.load()  # otherwise we test creation, not updating

    collection = anthology.collections.get("K06")
    event = collection.create_event(id="flrec-2006")

    if pre_load:
        # Volume should automatically have been added
        assert event.colocated_ids == {
            collection.get("1").full_id_tuple: EventLink.INFERRED
        }
    else:
        # If event index wasn't loaded, it's not
        assert event.colocated_ids == {}
