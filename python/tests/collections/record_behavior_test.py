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

import datetime

from lxml import etree
import pytest

from acl_anthology.collections import (
    DeletionNotice,
    Frontmatter,
    Media,
    MediaType,
    Paper,
    PaperType,
    VolumeType,
)
from acl_anthology.collections.paper import PaperRevision
from acl_anthology.constants import NO_BIBKEY
from acl_anthology.exceptions import AnthologyDuplicateIDError, AnthologyXMLError
from acl_anthology.files import (
    AttachmentReference,
    AudioReference,
    PDFReference,
    URLReference,
    VideoReference,
)
from acl_anthology.people import Name, NameSpecification


@pytest.fixture
def volume(anthology):
    anthology.venues.create("behavior", acronym="BEH", name="Fictional Conference")
    return anthology.create_collection("2026.behavior").create_volume(
        "main",
        title="Fictional proceedings",
        venue_ids=["behavior"],
        publisher="Fictional Publisher",
        address="Test City",
        month="July",
        editors=[NameSpecification(Name("Ellis", "Example"))],
    )


@pytest.mark.parametrize(
    "selector", [None, "collection", "volume", "paper", "frontmatter", "media", "missing"]
)
def test_item_selection_includes_the_requested_container_and_records(
    anthology, volume, selector
):
    paper = volume.create_paper(title="A paper")
    frontmatter = volume.create_frontmatter()
    media = volume.create_media(title="A talk")
    selectors = {
        None: None,
        "collection": volume.collection_id,
        "volume": volume.full_id,
        "paper": paper.full_id,
        "frontmatter": frontmatter.full_id,
        "media": media.full_id,
        "missing": "2026.absent-main.1",
    }
    actual = {item.full_id for item in anthology.items(selectors[selector])}
    if selector is None:
        assert {
            volume.full_id,
            paper.full_id,
            frontmatter.full_id,
            media.full_id,
        } <= actual
    elif selector in ("collection", "volume"):
        assert actual == {
            volume.full_id,
            paper.full_id,
            frontmatter.full_id,
            media.full_id,
        }
    elif selector == "missing":
        assert actual == set()
    else:
        assert actual == {selectors[selector]}


def test_generic_optional_metadata_and_inherited_publication_views(volume):
    media = volume.create_media(title="A bare recording", type=MediaType.MEDIA)
    frontmatter = volume.create_frontmatter()
    assert frontmatter.authors == ()
    assert frontmatter.abstract is None
    assert frontmatter.deletion is None
    assert frontmatter.note is None
    assert frontmatter.language is None
    assert frontmatter.language_name is None
    assert frontmatter.videos == frontmatter.audios == ()
    assert frontmatter.awards == frontmatter.errata == ()
    assert media.pdf is None and media.thumbnail is None
    assert media.pages is None
    assert media.awards == media.errata == media.revisions == ()
    assert media.address == "Test City"
    assert media.publisher == "Fictional Publisher"
    assert media.month == "July" and media.year == "2026"
    assert media.venue_ids == ("behavior",)
    assert media.journal_title is media.journal_volume is media.journal_issue is None
    assert media.media_format == "Recording" and media.type_label == "Media recording"
    assert media.csltype == "speech"
    media.ingest_date = datetime.date(2026, 7, 12)
    assert media.ingest_date == datetime.date(2026, 7, 12)
    assert media.get_events()[0].id == "behavior-2026"
    assert volume.name_spec_item_ids == (volume.full_id_tuple, frontmatter.full_id_tuple)


def test_frontmatter_supported_fields_roundtrip_without_becoming_a_paper(volume):
    item = volume.create_frontmatter(
        pdf=PDFReference("", checksum="0123abcd"),
        pages="i-ii",
        doi="10.1234/fictional",
        ingest_date="2026-07-12",
        urls=[
            ("website", URLReference("https://example.org/frontmatter")),
            ("", URLReference("https://example.org/untyped")),
        ],
        attachments=[("slides", AttachmentReference("slides.zip", checksum="abcd0123"))],
        revisions=[
            PaperRevision(
                "1", "Corrected", PDFReference("", checksum="abcd0123"), "2026-07-13"
            )
        ],
    )
    xml = item.to_xml()
    restored = Frontmatter.from_xml(volume, xml)
    assert not isinstance(restored, Paper)
    assert restored.pdf == item.pdf
    assert restored.pages == "i-ii" and restored.doi == item.doi
    assert restored.ingest_date == item.ingest_date
    assert restored.attachments == item.attachments and restored.urls == item.urls
    assert restored.revisions == item.revisions
    assert etree.tostring(restored.to_xml()) == etree.tostring(xml)
    assert restored.csltype == "book"
    with pytest.raises(AnthologyXMLError):
        Frontmatter.from_xml(
            volume, etree.fromstring("<frontmatter><unexpected/></frontmatter>")
        )
    bare = Frontmatter(parent=volume, bibkey=NO_BIBKEY)
    with pytest.raises(ValueError, match="without bibkey"):
        bare.to_xml()
    with pytest.raises(ValueError, match="without bibkey"):
        bare.to_bibtex()


def test_frontmatter_journal_and_invalid_media_container(volume):
    volume.type = VolumeType.JOURNAL
    volume.journal_title = "Fictional Journal"
    volume.journal_volume = "7"
    volume.journal_issue = "2"
    item = volume.create_frontmatter()
    assert item.bibtype == "book"
    assert item.citeproc_dict["container-title"] == "Fictional Journal"
    assert item.citeproc_dict["volume"] == "7"
    volume.type = VolumeType.MEDIA
    with pytest.raises(ValueError, match="frontmatter"):
        item.bibtype
    with pytest.raises(ValueError, match="frontmatter"):
        volume.create_frontmatter()


def test_media_optional_fields_editors_and_takedown_roundtrip(anthology, volume):
    item = volume.create_media(
        title="A fictional recording",
        type=MediaType.MEDIA,
        authors=[NameSpecification(Name("Ada", "Example"))],
        editors=[NameSpecification(Name("Initial", "Editor"))],
        audios=[AudioReference("recording.mp3")],
        videos=[VideoReference("recording.mp4")],
        month="August",
        ingest_date="2026-08-12",
        abstract="A fictional abstract.",
        language="eng",
        doi="10.1234/recording",
        license="https://example.org/license",
        note="A curated note.",
        attachments=[("slides", AttachmentReference("slides.zip", checksum="0123abcd"))],
        urls=[
            ("source", URLReference("https://example.org/source")),
            ("", URLReference("https://example.org/other")),
        ],
        deletion=DeletionNotice("removed", "Unavailable", "2026-08-13"),
    )
    assert item.csltype == "motion_picture" and item.month == "August"
    assert item.media_format == "Audio and video recording"
    previous = item.editors[0].resolve()
    item.editors = [NameSpecification(Name("New", "Editor"))]
    assert item.full_id_tuple not in previous.item_ids
    assert item.full_id_tuple in item.editors[0].resolve().item_ids
    xml = item.to_xml()
    restored = Media.from_xml(volume, xml)
    assert restored.type == item.type and restored.editors == item.editors
    assert restored.urls == item.urls and restored.attachments == item.attachments
    assert restored.deletion == item.deletion and restored.is_deleted
    assert restored.language_name == "English"
    assert restored.to_bibtex(with_abstract=True) == item.to_bibtex(with_abstract=True)
    assert etree.tostring(restored.to_xml()) == etree.tostring(xml)
    for root in ("paper", "media"):
        with pytest.raises(AnthologyXMLError):
            Media.from_xml(volume, etree.fromstring(f"<{root}><unexpected/></{root}>"))
    bare = Media(id="91", parent=volume, bibkey=NO_BIBKEY, title="A bare item")
    with pytest.raises(ValueError, match="without bibkey"):
        bare.to_xml()
    for id_ in ("0", "-1", "abc", "１２"):
        with pytest.raises(ValueError):
            volume.create_media(id=id_, title="Invalid ID")


def test_legacy_frontmatter_factory_and_duplicate_record_errors(volume):
    assert volume.name_spec_item_ids == (volume.full_id_tuple,)
    with pytest.raises(ValueError, match="authors"):
        volume.create_paper(
            title="Front", id="0", authors=[NameSpecification(Name("Wrong", "Author"))]
        )
    with pytest.raises(ValueError, match="contributors"):
        volume.create_paper(
            title="Front",
            type=PaperType.FRONTMATTER,
            editors=[NameSpecification(Name("Wrong", "Editor"))],
        )
    frontmatter = volume.create_paper(
        title=volume.title, type=PaperType.FRONTMATTER, editors=volume.editors
    )
    assert isinstance(frontmatter, Frontmatter)
    paper = volume.create_paper(
        id="2", title="A paper", audios=[AudioReference("paper.mp3")]
    )
    restored = Paper.from_xml(volume, paper.to_xml())
    assert isinstance(restored, Paper) and restored.audios == paper.audios
    with pytest.raises(AnthologyXMLError):
        Paper.from_xml(volume, etree.fromstring("<media/>"))
    with pytest.raises(AnthologyXMLError):
        Paper.from_xml(volume, etree.fromstring('<paper id="3"><unexpected/></paper>'))
    with pytest.raises(AnthologyDuplicateIDError):
        volume.create_media(id="2", title="Duplicate")
    with pytest.raises(AnthologyDuplicateIDError):
        volume._add_record_from_xml(paper.to_xml())


def test_volume_only_coeditor_links_can_be_excluded(anthology, volume):
    volume.editors += (NameSpecification(Name("Another", "Editor")),)
    editor, colleague = (spec.resolve() for spec in volume.editors)
    assert anthology.people.find_coauthors_counter(editor)[colleague.id] == 1
    assert not anthology.people.find_coauthors_counter(editor, include_volumes=False)
