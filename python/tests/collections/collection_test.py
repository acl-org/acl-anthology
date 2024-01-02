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
from acl_anthology.collections import Collection, CollectionIndex
from acl_anthology.utils import xml


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
    collection = Collection("empty", parent=collection_index, path=Path("."))
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
