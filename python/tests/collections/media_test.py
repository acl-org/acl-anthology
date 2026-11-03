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

from datetime import date

import pytest
from lxml import etree

from acl_anthology import Anthology
from acl_anthology.collections import Media
from acl_anthology.collections.types import MediaType, PaperType, VolumeType
from acl_anthology.files import AudioReference, VideoReference
from acl_anthology.people import Name, NameSpecification
from acl_anthology.text import MarkupText


@pytest.fixture
def media_volume(anthology):
    anthology.venues.create("recordings", acronym="REC", name="Fictional Recordings")
    collection = anthology.create_collection("2026.recordings")
    collection.create_event(title="Fictional Conference")
    return collection.create_volume(
        "media",
        title="Fictional Conference: Talks and Meetings",
        type=VolumeType.MEDIA,
        venue_ids=["recordings"],
        publisher="Fictional Language Society",
    )


@pytest.mark.parametrize("genre", list(MediaType))
def test_media_genres_have_citations_and_stable_ids(anthology, media_volume, genre):
    item = media_volume.create_media(
        title="Understanding invented languages",
        id="42",
        type=genre,
        authors=[NameSpecification(Name("Rhea", "Example"))],
        videos=[VideoReference("original-recording.mp4")],
    )
    assert anthology.get("2026.recordings-media.42") is item
    assert anthology.get_record_by_bibkey(item.bibkey) is item
    assert anthology.get_paper_by_bibkey(item.bibkey) is None
    assert list(anthology.media(item.full_id)) == [item]
    assert list(media_volume.media()) == [item]
    assert item in list(anthology.get_event("recordings-2026").media())
    assert item in list(item.authors[0].resolve().media())
    assert item.pdf is None
    assert item.is_media
    assert item.bibtype == "misc"
    assert item.to_bibtex().startswith(f"@misc{{{item.bibkey},")
    assert "inproceedings" not in item.to_bibtex()
    assert item.web_url in item.to_bibtex()
    assert item.web_url in item.to_citation()
    assert "Video recording" in item.to_citation()
    original_id = item.full_id
    item.videos = [VideoReference("https://example.org/replacement.webm")]
    assert item.full_id == original_id
    assert item.web_url == f"https://aclanthology.org/{original_id}/"


def test_podcast_roundtrip_and_citations(anthology, media_volume):
    item = media_volume.create_media(
        title=MarkupText.from_xml(
            etree.fromstring("<title>Explaining <fixed-case>NLP</fixed-case></title>")
        ),
        type=MediaType.PODCAST,
        authors=[NameSpecification(Name("Rhea", "Example"))],
        audios=[
            AudioReference("episode-7.mp3"),
            AudioReference("https://example.org/private.mp3", permission=False),
        ],
        publication_date=date(2026, 6, 12),
        duration=3600,
        episode="7",
        license="https://creativecommons.org/licenses/by/4.0/",
        abstract="An entirely fabricated podcast episode.",
    )
    citation = item.citeproc_dict
    assert citation["type"] == "broadcast"
    assert citation["issued"] == {"date-parts": [[2026, 6, 12]]}
    assert citation["number"] == "7"
    assert citation["medium"] == "Audio recording"
    assert citation["container-title"] == media_volume.title.as_text()
    assert citation["URL"] == item.web_url
    assert item.month == "June"
    bibtex = item.to_bibtex(with_abstract=True)
    assert 'number = "7"' in bibtex
    assert 'date = "2026-06-12"' in bibtex
    assert "Audio recording" in bibtex
    assert "Podcast episode 7. Audio recording. Released 2026-06-12" in bibtex
    assert "{NLP}" in bibtex
    assert "booktitle" not in bibtex
    assert "Podcast episode 7" in item.to_citation()
    assert "2026-06-12" in item.to_citation()
    parsed = Media.from_xml(media_volume, item.to_xml())
    assert parsed.type == item.type
    assert parsed.audios == item.audios
    assert parsed.publication_date == item.publication_date
    assert parsed.duration == item.duration
    assert parsed.episode == item.episode
    assert parsed.license == item.license
    anthology.save_all()
    anthology.get_collection("2026.recordings").validate_schema()
    reloaded = Anthology(anthology.datadir)
    restored = reloaded.get(item.full_id)
    assert restored.to_bibtex(with_abstract=True) == bibtex
    assert restored.audios == item.audios
    assert restored.is_media


def test_media_person_index_updates_and_orcid(anthology, media_volume):
    spec = NameSpecification(Name("Rhea", "Example"), orcid="0000-0000-0000-0001")
    item = media_volume.create_media(title="An invented keynote", authors=[spec])
    person = spec.resolve()
    assert person.orcid == "0000-0000-0000-0001"
    assert item.full_id_tuple in person.item_ids
    item.authors = [NameSpecification(Name("Another", "Speaker"))]
    assert item.full_id_tuple not in person.item_ids
    replacement = item.authors[0].resolve()
    assert item.full_id_tuple in replacement.item_ids
    assert list(replacement.media()) == [item]


def test_paper_with_video_is_not_standalone_media(anthology):
    volume = anthology.create_collection("2026.papers").create_volume(
        "main", title="Fictional Proceedings"
    )
    paper = volume.create_paper(title="A paper", videos=[VideoReference("paper.mp4")])
    assert paper.videos
    assert not paper.is_media
    assert paper.bibtype == "inproceedings"
    assert list(anthology.media(paper.full_id)) == []


def test_media_can_be_part_of_proceedings(anthology):
    volume = anthology.get_volume("2022.facl-long")
    item = volume.create_media(title="A panel", type=MediaType.PANEL)
    assert item.bibtype == "misc"
    assert item.csltype == "speech"
    assert "booktitle" not in item.to_bibtex()


def test_media_volume_defaults_and_invalid_genre(media_volume):
    with pytest.raises(ValueError, match="create_media"):
        media_volume.create_paper(title="A recording")
    with pytest.raises(ValueError):
        media_volume.create_media(title="Not a recording", type=PaperType.PAPER)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"publication_date": "2026-02-30"},
        {"publication_date": "2026-1-1"},
        {"duration": 0},
        {"duration": -1},
        {"duration": True},
        {"episode": ""},
        {"episode": " 7 "},
    ],
)
def test_media_metadata_is_validated(media_volume, kwargs):
    with pytest.raises(ValueError):
        media_volume.create_media(title="Invalid metadata", **kwargs)


def test_media_audio_types_are_validated(media_volume):
    with pytest.raises(TypeError):
        media_volume.create_media(title="Invalid audio", audios=["episode.mp3"])
    item = media_volume.create_media(title="Valid audio")
    with pytest.raises(TypeError):
        item.audios = [VideoReference("video.mp4")]


def test_media_release_year_can_differ_from_event_year(media_volume):
    item = media_volume.create_media(
        title="A recording released later",
        type=MediaType.PODCAST,
        publication_date="2027-01-15",
        episode="9",
    )
    assert item.parent.year == "2026"
    assert item.year == "2027"
    assert item.full_id.startswith("2026.recordings-media.")
    assert item.citeproc_dict["issued"]["date-parts"] == [[2027, 1, 15]]
    assert 'year = "2027"' in item.to_bibtex()
    assert "Podcast episode 9" in item.to_bibtex()


@pytest.mark.parametrize(
    "cls, tag", [(AudioReference, "audio"), (VideoReference, "video")]
)
@pytest.mark.parametrize("permission", [True, False])
def test_recording_reference_roundtrip(cls, tag, permission):
    ref = cls("original-file.mp3", permission=permission)
    assert ref.url == "https://aclanthology.org/original-file.mp3"
    xml = ref.to_xml()
    assert xml.tag == tag
    assert cls.from_xml(etree.fromstring(etree.tostring(xml))) == ref


@pytest.mark.parametrize("cls", [AudioReference, VideoReference])
def test_unavailable_recording_roundtrip(cls):
    ref = cls("unavailable.mp4", available=False)
    assert ref.permission
    assert ref.to_xml().get("available") == "false"
    restored = cls.from_xml(ref.to_xml())
    assert restored == ref
    assert not restored.available


def test_coauthors_can_exclude_media(anthology, media_volume):
    item = media_volume.create_media(
        title="A discussion",
        authors=[
            NameSpecification(Name("Rhea", "Example")),
            NameSpecification(Name("Another", "Speaker")),
        ],
    )
    person, collaborator = (spec.resolve() for spec in item.authors)
    assert anthology.people.find_coauthors_counter(person)[collaborator.id] == 1
    assert not anthology.people.find_coauthors_counter(person, include_media=False)


def test_media_csl_metadata_updates_after_corrections(media_volume):
    item = media_volume.create_media(
        title="Original title", type=MediaType.PODCAST, publication_date="2026-03-21"
    )
    assert item.citeproc_dict["issued"]["date-parts"] == [[2026, 3, 21]]
    item.title = "Corrected title"
    item.publication_date = "2026-04-02"
    assert item.citeproc_dict["title"] == "Corrected title"
    assert item.citeproc_dict["issued"]["date-parts"] == [[2026, 4, 2]]


def test_media_citation_escapes_text_and_preserves_title_markup(media_volume):
    media_volume.publisher = "Test & Co"
    item = media_volume.create_media(
        title=MarkupText.from_string("Inputs <outputs> & tokens"),
        type=MediaType.PODCAST,
        episode="S1<E2",
    )
    citation = item.to_citation()
    assert "<outputs>" not in citation
    assert "&lt;outputs&gt; &amp; tokens" in citation
    assert "S1&lt;E2" in citation
    assert "Test &amp; Co" in citation


@pytest.mark.parametrize("genre", [MediaType.KEYNOTE, MediaType.PODCAST])
def test_media_can_be_rendered_with_csl_style(media_volume, tmp_path, genre):
    style = tmp_path / "test.csl"
    style.write_text(
        '<style xmlns="http://purl.org/net/xbiblio/csl" version="1.0" class="in-text">'
        "<info><title>Media test</title><id>https://example.org/media-test</id>"
        "<updated>2026-01-01T00:00:00+00:00</updated></info>"
        '<citation><layout><text variable="title"/></layout></citation>'
        '<bibliography><layout><text variable="title"/>'
        '<date variable="issued" prefix=". "><date-part name="year"/></date>'
        "</layout></bibliography></style>"
    )
    item = media_volume.create_media(
        title="An invented recording", type=genre, publication_date="2026-03-21"
    )
    rendered = item.to_citation(style=str(style))
    assert "An invented recording" in rendered
    assert "2026" in rendered
    assert item.web_url in rendered
