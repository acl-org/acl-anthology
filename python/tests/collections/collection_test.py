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
from lxml import etree
from pathlib import Path

from acl_anthology import Anthology
from acl_anthology.collections import Collection, CollectionIndex, VolumeType
from acl_anthology.people import NameSpecification
from acl_anthology.utils import xml
from acl_anthology.text import MarkupText


test_cases_xml_collections = (
    # (filename, # volumes, # papers, has event?)
    ("2022.acl.xml", 5, 779, True),
    ("2022.naloma.xml", 1, 6, False),
    ("J89.xml", 4, 62, False),
    ("L06.xml", 1, 5, False),
)


test_cases_xml_roundtrip = tuple(x[0] for x in test_cases_xml_collections)


@pytest.fixture
def collection_index(anthology):
    return CollectionIndex(parent=anthology)


def test_empty_collection(collection_index):
    collection = Collection("2000.empty", parent=collection_index, path=Path("."))
    assert not collection.is_data_loaded
    collection.is_data_loaded = True
    assert isinstance(collection.root, Anthology)
    assert len(list(collection.volumes())) == 0
    assert len(list(collection.papers())) == 0
    assert collection.get_event() is None


@pytest.mark.parametrize(
    "filename, no_volumes, no_papers, has_event", test_cases_xml_collections
)
def test_collection_load(
    collection_index, datadir, filename, no_volumes, no_papers, has_event
):
    infile = datadir / "xml" / filename
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


@pytest.mark.parametrize("filename", test_cases_xml_roundtrip)
def test_collection_validate_schema(collection_index, datadir, filename):
    infile = datadir / "xml" / filename
    collection = Collection(
        filename.replace(".xml", ""), parent=collection_index, path=infile
    )
    collection.validate_schema()


@pytest.mark.parametrize("filename", test_cases_xml_roundtrip)
def test_collection_roundtrip_save(collection_index, datadir, tmp_path, filename):
    infile = datadir / "xml" / filename
    outfile = tmp_path / filename
    # Load & save collection
    collection = Collection(
        filename.replace(".xml", ""), parent=collection_index, path=infile
    )
    collection.load()
    collection.save(path=outfile)
    # Compare
    assert outfile.is_file()
    expected = etree.parse(infile)
    generated = etree.parse(outfile)
    xml.assert_equals(generated.getroot(), expected.getroot())


def test_collection_create_volume_implicit(collection_index):
    collection = collection_index.get("2022.acl")
    volume = collection.create_volume(
        "keynotes",
        title=MarkupText.from_string("Keynotes from ACL 2022"),
    )
    assert volume.id in collection
    assert volume.year == "2022"
    assert volume.id == "keynotes"
    assert volume.full_id == "2022.acl-keynotes"
    assert volume.type == VolumeType.PROCEEDINGS


def test_collection_create_volume_explicit(collection_index):
    collection = collection_index.get("J89")
    collection.id = "1989.cl"  # because we can't create volumes with old-style ID
    volume = collection.create_volume(
        id="99",
        title=MarkupText.from_string("Special Issue"),
        year="1989",
        type="journal",
        journal_issue="99",
        venue_ids=["cl"],
    )
    assert volume.id in collection
    assert volume.year == "1989"
    assert volume.id == "99"
    assert volume.full_id == "1989.cl-99"
    assert volume.type == VolumeType.JOURNAL
    assert volume.journal_issue == "99"
    assert "cl" in volume.venue_ids


@pytest.mark.parametrize("pre_load", (True, False))
def test_collection_create_volume_should_update_person(anthology, pre_load):
    if pre_load:
        anthology.people.load()  # otherwise we test creation, not updating

    collection = anthology.collections.get("2022.acl")
    editors = [NameSpecification("Rada Mihalcea")]
    volume = collection.create_volume(
        "keynotes",
        title=MarkupText.from_string("Keynotes from ACL 2022"),
        editors=editors,
    )
    assert volume.editors == editors

    # Volume should have been added to the person object
    person = anthology.resolve(editors[0])
    assert volume.full_id_tuple in person.item_ids


@pytest.mark.parametrize("pre_load", (True, False))
def test_collection_create_volume_should_update_personindex(anthology, pre_load):
    if pre_load:
        anthology.people.load()  # otherwise we test creation, not updating

    collection = anthology.collections.get("2022.acl")
    editors = [NameSpecification("Nonexistant, Guy Absolutely")]
    volume = collection.create_volume(
        "keynotes",
        title=MarkupText.from_string("Keynotes from ACL 2022"),
        editors=editors,
    )
    assert volume.editors == editors

    # New editor should exist in the person index
    person = anthology.resolve(editors[0])
    assert volume.full_id_tuple in person.item_ids


@pytest.mark.parametrize(
    "pre_load, reset",
    (
        (True, True),
        pytest.param(True, False, marks=pytest.mark.xfail(reason="not implemented")),
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
        venue_ids=["acl"],
    )

    if reset:
        anthology.reset_indices()

    # New implicit event should exist in the event index
    assert "acl-2000" in anthology.events
    assert volume.full_id_tuple in anthology.events["acl-2000"].colocated_ids
    assert volume.full_id_tuple in anthology.events.reverse
    assert anthology.events.reverse[volume.full_id_tuple] == {"acl-2000"}


@pytest.mark.parametrize(
    "pre_load, reset",
    (
        (True, True),
        pytest.param(True, False, marks=pytest.mark.xfail(reason="not implemented")),
        (False, False),
        (False, True),
    ),
)
def test_collection_create_volume_should_update_event(anthology, pre_load, reset):
    if pre_load:
        anthology.events.load()  # otherwise we test creation, not updating

    collection = anthology.collections.get("2022.acl")
    collection.is_data_loaded = True
    volume = collection.create_volume(
        "keynotes",
        title=MarkupText.from_string("Keynotes from ACL 2022"),
        venue_ids=["acl"],
    )

    if reset:
        anthology.reset_indices()

    # New volume should be added to existing event
    assert "acl-2022" in anthology.events
    assert volume.full_id_tuple in anthology.events["acl-2022"].colocated_ids
    assert volume.full_id_tuple in anthology.events.reverse
    assert anthology.events.reverse[volume.full_id_tuple] == {"acl-2022"}


@pytest.mark.parametrize(
    "pre_load, reset",
    (
        (True, True),
        pytest.param(True, False, marks=pytest.mark.xfail(reason="not implemented")),
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
        venue_ids=["acl"],
    )

    if reset:
        anthology.reset_indices()

    # Nev volume should be added to existing venue
    assert volume.full_id_tuple in anthology.venues["acl"].item_ids


def test_collection_create_event(collection_index):
    collection = collection_index.get("L06")

    # For old-style ID collections, an ID must be explicitly given
    with pytest.raises(ValueError):
        _ = collection.create_event()

    event = collection.create_event(id="lrec-2006")
    assert event.id == "lrec-2006"

    # Trying to create yet another event in the same collection should raise
    with pytest.raises(ValueError):
        _ = collection.create_event(id="lrecagain-2006")


@pytest.mark.parametrize("pre_load", (True, False))
def test_collection_create_event_should_update_eventindex(pre_load, anthology):
    if pre_load:
        anthology.events.load()  # otherwise we test creation, not updating

    collection = anthology.collections.get("L06")
    event = collection.create_event(id="lrec-2006")

    if pre_load:
        # Volume should automatically have been added
        assert event.colocated_ids == [collection.get("1").full_id_tuple]
    else:
        # If event index wasn't loaded, it's not
        assert event.colocated_ids == []
