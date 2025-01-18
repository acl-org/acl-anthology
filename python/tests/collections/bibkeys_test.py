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
from acl_anthology import constants
from acl_anthology.collections import BibkeyIndex


def test_bibkeys_indexing(anthology):
    index = anthology.collections.bibkeys
    index.load()
    assert index.is_data_loaded
    assert len(index) > 850
    assert "feng-etal-2022-dynamic" in index
    assert index.get("feng-etal-2022-dynamic").full_id_tuple == ("2022.acl", "long", "10")
    assert "gubelmann-etal-2022-philosophically" in index
    assert index.get("gubelmann-etal-2022-philosophically").full_id_tuple == (
        "2022.naloma",
        "1",
        "5",
    )
    assert "cl-1989-linguistics-15-number-4" in index
    assert index.get("cl-1989-linguistics-15-number-4").full_id_tuple == ("J89", "4", "0")


def test_bibkeys_index_paper(anthology):
    # We manually instance BibKeyIndex and set is_data_loaded=True to prevent automatic indexing
    index = BibkeyIndex(anthology.collections)
    index.is_data_loaded = True

    paper = anthology.get_paper("2022.acl-long.93")
    assert paper.bibkey == "kamal-eddine-etal-2022-frugalscore"
    assert "kamal-eddine-etal-2022-frugalscore" not in index

    # Indexing the paper should add it to the index
    index._index_paper(paper.bibkey, paper)
    assert "kamal-eddine-etal-2022-frugalscore" in index
    assert index["kamal-eddine-etal-2022-frugalscore"] is paper

    # Indexing the paper again should not change anything
    index._index_paper(paper.bibkey, paper)
    assert "kamal-eddine-etal-2022-frugalscore" in index
    assert index["kamal-eddine-etal-2022-frugalscore"] is paper

    # Indexing a different paper with the same bibkey should raise
    with pytest.raises(ValueError):
        paper2 = anthology.get_paper("2022.acl-long.100")
        index._index_paper(paper.bibkey, paper2)


def test_bibkeys_generate_bibkey_should_add_title_words(anthology):
    index = anthology.collections.bibkeys
    index.load()

    # Generating a bibkey for an existing paper should result in a bibkey with another title words added
    paper = anthology.get_paper("2022.acl-long.10")
    assert paper.bibkey == "feng-etal-2022-dynamic"
    assert index.generate_bibkey(paper) == "feng-etal-2022-dynamic-schema"

    # Generating a bibkey for an existing paper should result in a bibkey with another title words added
    paper = anthology.get_paper("J89-2003")
    assert paper.bibkey == "davis-1989-cross"
    assert index.generate_bibkey(paper) == "davis-1989-cross-vowel"


def test_bibkeys_generate_bibkey_should_increment_counter(anthology):
    index = anthology.collections.bibkeys
    index.load()

    # Generating a bibkey when there are not enough title words should increment the counter
    paper = anthology.get_paper("J89-4009")
    assert paper.bibkey == "nn-1989-advertisements-4"
    assert index.generate_bibkey(paper) == "nn-1989-advertisements-5"


def test_bibkeys_generate_bibkey_should_match_existing_bibkeys(anthology):
    # We manually instance BibKeyIndex and set is_data_loaded=True to prevent automatic indexing
    index = BibkeyIndex(anthology.collections)
    index.is_data_loaded = True

    # Now, we can check if the auto-generated bibkeys match the ones in our XML
    for paper in anthology.papers("2022.acl"):
        assert index.generate_bibkey(paper) == paper.bibkey
        # We need to index the paper so it is taken into account for future clashes
        index._index_paper(paper.bibkey, paper)


def test_bibkeys_refresh_bibkey_should_update(anthology):
    index = anthology.collections.bibkeys
    index.load()

    # We pick a paper (here, frontmatter) with a bibkey not conforming to what
    # generate_bibkey() would produce
    paper = anthology.get_paper("2022.naloma-1.0")
    assert paper.bibkey == "naloma-2022-natural"
    assert "naloma-2022-natural" in index
    assert index["naloma-2022-natural"] is paper

    # Setting the bibkey to NO_BIBKEY should replace it with an automatically-generated version
    paper.bibkey = constants.NO_BIBKEY  # NOTE: use paper.refresh_bibkey() in practice
    assert paper.bibkey == "naloma-2022-1"
    assert "naloma-2022-natural" not in index
    assert "naloma-2022-1" in index
    assert index["naloma-2022-1"] is paper

    # Setting the bibkey to a custom value should also replace it in the index
    paper.bibkey = "naloma-2022-frontmatter"
    assert paper.bibkey == "naloma-2022-frontmatter"
    assert "naloma-2022-1" not in index
    assert "naloma-2022-frontmatter" in index
    assert index["naloma-2022-frontmatter"] is paper


def test_bibkeys_refresh_bibkey_should_leave_unchanged(anthology):
    index = anthology.collections.bibkeys
    index.load()

    # We pick a paper with a bibkey that doesn't need changing
    paper = anthology.get_paper("L06-1060")
    assert paper.bibkey == "roark-etal-2006-sparseval"
    assert "roark-etal-2006-sparseval" in index
    assert index["roark-etal-2006-sparseval"] is paper

    # Refreshing the bibkey should not change it
    paper.bibkey = constants.NO_BIBKEY  # NOTE: use paper.refresh_bibkey() in practice
    assert paper.bibkey == "roark-etal-2006-sparseval"
    assert "roark-etal-2006-sparseval" in index
    assert index["roark-etal-2006-sparseval"] is paper
