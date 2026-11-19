# Copyright 2026 ACL Anthology
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

from acl_anthology import Anthology
from acl_anthology.collections import (
    CollectionItem,
    Frontmatter,
    Media,
    MediaType,
    Paper,
)
from acl_anthology.files import AudioReference, VideoReference
from acl_anthology.people import Name, NameSpecification


@pytest.fixture
def volume(anthology):
    anthology.venues.create("itemtest", acronym="ITEM", name="Fictional Item Conference")
    return anthology.create_collection("2026.itemtest").create_volume(
        "main",
        title="Fictional proceedings",
        venue_ids=["itemtest"],
        editors=[NameSpecification(Name("Ellis", "Example"))],
    )


def test_identified_items_share_an_interface_not_a_paper_type(anthology, volume):
    paper = volume.create_paper(title="A paper")
    frontmatter = volume.create_frontmatter()
    media = volume.create_media(title="A keynote", type=MediaType.KEYNOTE)
    assert all(
        isinstance(item, CollectionItem) for item in (volume, paper, frontmatter, media)
    )
    assert all(
        not hasattr(item, "__dict__") for item in (volume, paper, frontmatter, media)
    )
    assert isinstance(paper, Paper)
    assert isinstance(frontmatter, Frontmatter) and not isinstance(frontmatter, Paper)
    assert isinstance(media, Media) and not isinstance(media, Paper)
    assert list(volume.papers()) == [paper]
    assert list(volume.media()) == [media]
    assert set(item.full_id for item in volume.records()) == {
        paper.full_id,
        frontmatter.full_id,
        media.full_id,
    }
    assert list(anthology.papers(volume.full_id)) == [paper]
    assert list(anthology.media(volume.full_id)) == [media]
    assert anthology.get_paper(media.full_id) is None
    assert anthology.get_paper(frontmatter.full_id) is None
    assert anthology.get_media(media.full_id) is media
    assert anthology.get_frontmatter(frontmatter.full_id) is frontmatter
    assert anthology.get_record_by_bibkey(media.bibkey) is media
    assert anthology.get_paper_by_bibkey(media.bibkey) is None


def test_media_has_its_own_xml_and_roundtrips(anthology, volume):
    item = volume.create_media(
        id="42",
        title="A fictional episode",
        type=MediaType.PODCAST,
        authors=[NameSpecification(Name("Ada", "Example"))],
        audios=[AudioReference("episode.mp3")],
        videos=[VideoReference("episode.mp4", available=False)],
        publication_date="2027-01-03",
        episode="S2E4",
        duration=3600,
    )
    assert item.to_xml().tag == "media"
    assert item.to_xml().get("type") == "podcast"
    assert item.bibtype == "misc"
    assert item.csltype == "broadcast"
    assert item.year == "2027"
    assert item.full_id == "2026.itemtest-main.42"
    anthology.save_all()
    item.collection.validate_schema()
    restored = Anthology(anthology.datadir).get_media(item.full_id)
    assert isinstance(restored, Media)
    assert restored.to_bibtex() == item.to_bibtex()
    assert restored.audios == item.audios
    assert restored.videos == item.videos


def test_frontmatter_is_a_restricted_record_with_inherited_metadata(volume):
    item = volume.create_frontmatter()
    assert item.id == "0"
    assert item.title == volume.title
    assert item.editors == volume.editors
    assert item.to_xml().tag == "frontmatter"
    assert item.bibtype == "proceedings"
    volume.title = "Corrected proceedings title"
    assert item.title == volume.title
    other = volume.collection.create_volume("other", title="Other proceedings")
    with pytest.raises(TypeError):
        other.create_frontmatter(authors=[NameSpecification(Name("Wrong", "Author"))])


def test_contributors_index_all_identified_types(anthology, volume):
    editor = volume.editors[0].resolve()
    assert volume in list(editor.anthology_items())
    frontmatter = volume.create_frontmatter()
    assert frontmatter in list(editor.anthology_items())
    media = volume.create_media(
        title="A talk",
        authors=[NameSpecification(Name("Ada", "Example"))],
    )
    person = media.authors[0].resolve()
    assert list(person.media()) == [media]
    assert list(person.papers()) == []
    assert media.get_namespec_for(person) is media.authors[0]
    media.authors = [NameSpecification(Name("Another", "Speaker"))]
    assert media.full_id_tuple not in person.item_ids
    replacement = media.authors[0].resolve()
    assert media.full_id_tuple in replacement.item_ids


def test_inherited_frontmatter_contributors_follow_volume_edits(anthology, volume):
    item = volume.create_frontmatter()
    original = volume.editors[0].resolve()
    volume.editors = [NameSpecification(Name("New", "Editor"))]
    assert volume.full_id_tuple not in original.item_ids
    assert item.full_id_tuple not in original.item_ids
    replacement = volume.editors[0].resolve()
    assert volume.full_id_tuple in replacement.item_ids
    assert item.full_id_tuple in replacement.item_ids
    volume.editors[0].name = Name("Changed", "Editor")
    assert item.full_id_tuple not in replacement.item_ids
    assert item.full_id_tuple in volume.editors[0].resolve().item_ids
