# Copyright 2025 Marcel Bollmann <marcel@bollmann.me>
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
from acl_anthology.collections import BibkeyIndex
from acl_anthology.text import MarkupText
from lxml import etree


def test_bibkeyindex_load(anthology):
    index = BibkeyIndex(anthology.collections)
    assert not index.is_data_loaded
    was_verbose = anthology.verbose
    anthology.verbose = True
    index.load()
    anthology.verbose = was_verbose
    assert index.is_data_loaded


def test_bibkeys_indexing(anthology):
    index = anthology.collections.bibkeys
    index.load()
    assert index.is_data_loaded
    assert len(index) > 100
    assert "feng-etal-2022-dynamic" in index
    assert index.get("feng-etal-2022-dynamic").full_id_tuple == (
        "2022.facl",
        "long",
        "10",
    )
    assert "callahan-etal-2022-fabricated" in index
    assert index.get("callahan-etal-2022-fabricated").full_id_tuple == (
        "2022.natfake",
        "1",
        "5",
    )
    assert "fcl-1989-linguistics-15-number-4" in index
    assert index.get("fcl-1989-linguistics-15-number-4").full_id_tuple == (
        "Q89",
        "4",
        "0",
    )


def test_bibkeys_should_not_load_if_data_loaded(anthology):
    index = BibkeyIndex(anthology.collections)
    index.is_data_loaded = True
    assert "solheim-etal-2022-fastscore" not in index

    index.load()  # should be noop
    assert "solheim-etal-2022-fastscore" not in index


def test_bibkeys_index_paper(anthology):
    # We manually instance BibKeyIndex and set is_data_loaded=True to prevent automatic indexing
    index = BibkeyIndex(anthology.collections)
    index.is_data_loaded = True

    paper = anthology.get_paper("2022.facl-long.93")
    assert paper.bibkey == "solheim-etal-2022-fastscore"
    assert "solheim-etal-2022-fastscore" not in index

    # Indexing the paper should add it to the index
    index._index_paper(paper.bibkey, paper)
    assert "solheim-etal-2022-fastscore" in index
    assert index["solheim-etal-2022-fastscore"] is paper

    # Indexing the paper again should not change anything
    index._index_paper(paper.bibkey, paper)
    assert "solheim-etal-2022-fastscore" in index
    assert index["solheim-etal-2022-fastscore"] is paper

    # Indexing a different paper with the same bibkey should raise
    with pytest.raises(ValueError):
        paper2 = anthology.get_paper("2022.facl-long.100")
        index._index_paper(paper.bibkey, paper2)


def test_bibkeys_generate_bibkey_with_all_stopwords(anthology):
    index = anthology.collections.bibkeys
    paper = anthology.get_paper("2022.facl-long.9")
    paper.title = MarkupText.from_string("If and or")
    assert index.generate_bibkey(paper) == "ma-etal-2022-if"


@pytest.mark.parametrize("pre_load", (True, False))
def test_bibkeys_generate_bibkey_should_add_title_words(anthology, pre_load):
    index = anthology.collections.bibkeys
    if pre_load:  # should not make a functional difference
        index.load()

    # Generating a bibkey for an existing paper should result in a bibkey with another title words added
    paper = anthology.get_paper("2022.facl-long.10")
    assert paper.bibkey == "feng-etal-2022-dynamic"
    assert index.generate_bibkey(paper) == "feng-etal-2022-dynamic-schema"

    # Generating a bibkey for an existing paper should result in a bibkey with another title words added
    paper = anthology.get_paper("Q89-2003")
    assert paper.bibkey == "weisz-1989-cross"
    assert index.generate_bibkey(paper) == "weisz-1989-cross-continuum"


@pytest.mark.parametrize("pre_load", (True, False))
def test_bibkeys_generate_bibkey_should_increment_counter(anthology, pre_load):
    index = anthology.collections.bibkeys
    if pre_load:  # should not make a functional difference
        index.load()

    # Generating a bibkey when there are not enough title words should increment the counter
    paper = anthology.get_paper("Q89-4009")
    assert paper.bibkey == "nn-1989-advertisements-4"
    assert index.generate_bibkey(paper) == "nn-1989-advertisements-5"


def test_bibkeys_generate_bibkey_should_match_existing_bibkeys(anthology):
    # We manually instance BibKeyIndex and set is_data_loaded=True to prevent automatic indexing
    index = BibkeyIndex(anthology.collections)
    index.is_data_loaded = True

    # Now, we can check if the auto-generated bibkeys match the ones in our XML
    for paper in anthology.papers("2022.facl"):
        assert index.generate_bibkey(paper) == paper.bibkey
        # We need to index the paper so it is taken into account for future clashes
        index._index_paper(paper.bibkey, paper)


@pytest.mark.parametrize("pre_load", (True, False))
def test_bibkeys_refresh_bibkey_should_update(anthology, pre_load):
    index = anthology.collections.bibkeys
    if pre_load:  # should not make a functional difference
        index.load()

    # We pick a paper (here, frontmatter) with a bibkey not conforming to what
    # generate_bibkey() would produce
    paper = anthology.get_paper("2022.natfake-1.0")
    assert paper.bibkey == "natfake-2022-natural"
    assert "natfake-2022-natural" in index
    assert index["natfake-2022-natural"] is paper

    # Refreshing the bibkey should replace it with an automatically-generated version
    paper.refresh_bibkey()
    assert paper.bibkey == "natfake-2022-1"
    assert "natfake-2022-natural" not in index
    assert "natfake-2022-1" in index
    assert index["natfake-2022-1"] is paper

    # Setting the bibkey to a custom value should also replace it in the index
    paper.bibkey = "natfake-2022-frontmatter"
    assert paper.bibkey == "natfake-2022-frontmatter"
    assert "natfake-2022-1" not in index
    assert "natfake-2022-frontmatter" in index
    assert index["natfake-2022-frontmatter"] is paper


@pytest.mark.parametrize("pre_load", (True, False))
def test_bibkeys_refresh_bibkey_should_leave_unchanged(anthology, pre_load):
    index = anthology.collections.bibkeys
    if pre_load:  # should not make a functional difference
        index.load()

    # We pick a paper with a bibkey that doesn't need changing
    paper = anthology.get_paper("K06-1060")
    assert paper.bibkey == "corwin-etal-2006-fparseval"
    assert "corwin-etal-2006-fparseval" in index
    assert index["corwin-etal-2006-fparseval"] is paper

    # Refreshing the bibkey should not change it
    paper.refresh_bibkey()
    assert paper.bibkey == "corwin-etal-2006-fparseval"
    assert "corwin-etal-2006-fparseval" in index
    assert index["corwin-etal-2006-fparseval"] is paper


def test_bibkeys_should_not_allow_setting_duplicate_bibkeys(anthology):
    index = BibkeyIndex(anthology.collections)
    index.is_data_loaded = True

    paper_a = anthology.get_paper("2022.facl-long.1")
    paper_a.bibkey = "my-duplicate-bibkey"  # okay

    paper_b = anthology.get_paper("2022.facl-long.2")
    with pytest.raises(ValueError):
        paper_b.bibkey = "my-duplicate-bibkey"  # not okay


def test_bibkeys_should_perform_input_validation(anthology):
    index = BibkeyIndex(anthology.collections)
    index.is_data_loaded = True

    paper = anthology.get_paper("2022.facl-long.1")

    with pytest.raises(ValueError):
        paper.bibkey = "No-Capital-Letters"
    with pytest.raises(ValueError):
        paper.bibkey = "no-spurious-whitespace  "


def test_bibkeys_should_not_allow_loading_duplicate_bibkeys(anthology, shared_datadir):
    # Manipulate an XML file so that two papers have identical bibkeys
    filename = shared_datadir / "anthology" / "xml" / "2022.facl.xml"
    tree = etree.parse(filename)
    for paper_id in (5, 14):
        bibkey = tree.xpath(f"//volume[@id='long']/paper[@id='{paper_id}']/bibkey")[0]
        bibkey.text = "li-etal-2022-learning"
    with open(filename, "wb") as f:
        f.write(etree.tostring(tree, xml_declaration=True, encoding="UTF-8"))

    # Simply loading the bibkey index should raise an error now
    index = BibkeyIndex(anthology.collections)
    with pytest.raises(ValueError):
        index.load()
