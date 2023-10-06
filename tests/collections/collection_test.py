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

import pytest
from lxml import etree
from pathlib import Path

from acl_anthology import Anthology
from acl_anthology.collections import Collection, CollectionIndex


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


def test_collection_load(collection_index, datadir):
    infile = datadir / "xml" / "2022.acl.xml"
    collection = Collection("2022.acl", parent=collection_index, path=infile)
    collection.load()
    assert collection.is_data_loaded
    assert len(list(collection.volumes())) == 5
    # 774 <paper> + 5 <frontmatter>
    assert len(list(collection.papers())) == 779
    assert collection.get_event() is not None


@pytest.mark.skip()
def test_collection_roundtrip_save(collection_index, datadir, tmp_path):
    infile = datadir / "xml" / "2022.acl.xml"
    outfile = tmp_path / "2022.acl.xml"
    # Load & save collection
    collection = Collection("2022.acl", parent=collection_index, path=infile)
    collection.load()
    collection.save(path=outfile)
    # Compare
    assert outfile.is_file()
    with open(infile, "r") as f, open(outfile, "r") as g:
        expected = etree.parse(f)
        generated = etree.parse(g)
    # TODO: how to compare two etrees in a way that conforms to our schema?
    assert generated == expected
