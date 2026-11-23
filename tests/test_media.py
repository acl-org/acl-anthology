"""End-to-end tests for media ingestion, migration, exports, and Hugo pages."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

from lxml import html
import msgspec
import pytest

from acl_anthology import Anthology, config
from acl_anthology.collections import Talk
from acl_anthology.collections.paper import PaperDeletionNotice
from acl_anthology.collections.types import MediaType, VolumeType
from acl_anthology.files import AudioReference, URLReference, VideoReference
from acl_anthology.people import Name, NameSpecification

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bin.author_stats import compute_authorship_stats
from bin.create_hugo_data import (
    author_stats,
    export_anthology,
    record_to_dict,
    recording_to_dict,
)
from bin.add_dois import process_volume
from bin.generate_crossref_doi_metadata import generate_crossref_xml, resolve_inputs
from bin.ingest_media import MediaManifest, ingest_media
from bin.oneoff.migrate_talks import migrate_talks

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def anthology(tmp_path):
    data = tmp_path / "source-data"
    (data / "xml").mkdir(parents=True)
    (data / "json").mkdir()
    shutil.copyfile(
        ROOT / "python/acl_anthology/data/schema.rnc", data / "xml/schema.rnc"
    )
    for index in ("people", "venues", "sigs"):
        (data / f"json/{index}.json").write_text("{}\n")
    anthology = Anthology(data)
    anthology.venues.create("recordings", acronym="REC", name="Fictional Recordings")
    return anthology


@pytest.fixture
def manifest():
    return {
        "collection": "2026.recordings",
        "volume": "episodes",
        "title": "Fictional Podcast",
        "venue": "recordings",
        "publisher": "Fictional Media Society",
        "items": [
            {
                "id": "7",
                "title": "An invented NLP conversation",
                "type": "podcast",
                "creators": [{"first": "Rhea", "last": "Example"}],
                "audios": [{"href": "episode-7.mp3", "permission": True}],
                "publication_date": "2026-03-21",
                "episode": "7",
                "duration": 3600,
                "abstract": "An entirely fabricated episode for testing.",
                "license": "https://creativecommons.org/licenses/by/4.0/",
                "links": [
                    {"type": "transcript", "url": "https://example.org/transcript"}
                ],
            }
        ],
    }


def decode_manifest(data):
    return msgspec.json.decode(msgspec.json.encode(data), type=MediaManifest)


def test_ingest_media_persists_ids_and_metadata(anthology, manifest):
    item = ingest_media(anthology, decode_manifest(manifest))[0]
    assert item.full_id == "2026.recordings-episodes.7"
    assert item.type == MediaType.PODCAST
    assert item.audios[0].url == f"{config.url_prefix}/episode-7.mp3"
    assert "<fixed-case>NLP</fixed-case>" in item.title.as_xml()
    assert item.publication_date == "2026-03-21"
    assert item.duration == 3600
    assert item.episode == "7"
    assert item.urls[0][0] == "transcript"
    assert item.authors[0].resolve().id == "rhea-example/unverified"
    assert not list((anthology.datadir / "xml").glob("*.xml"))
    anthology.save_all()
    anthology.get_collection(manifest["collection"]).validate_schema()
    reloaded = Anthology(anthology.datadir)
    restored = reloaded.get(item.full_id)
    assert restored.to_bibtex() == item.to_bibtex()
    assert restored.audios == item.audios


def test_ingest_media_appends_without_reassigning_ids(anthology, manifest):
    original = ingest_media(anthology, decode_manifest(manifest))[0]
    manifest["items"][0]["id"] = "23"
    manifest["items"][0]["title"] = "Another invented episode"
    later = ingest_media(anthology, decode_manifest(manifest))[0]
    assert original.full_id == "2026.recordings-episodes.7"
    assert later.full_id == "2026.recordings-episodes.23"
    assert original.bibkey != later.bibkey
    with pytest.raises(ValueError, match="already exists"):
        ingest_media(anthology, decode_manifest(manifest))


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda data: data.update(venue="unknown"), "Unknown venue"),
        (lambda data: data.update(event="recordings-1900"), "Unknown event"),
        (lambda data: data["items"].append(data["items"][0].copy()), "Duplicate"),
        (lambda data: data["items"][0].update(type="paper"), "Invalid enum value"),
        (lambda data: data["items"][0].update(id="0"), "Invalid media item ID"),
        (lambda data: data["items"][0].update(audios=[]), "no recording"),
        (lambda data: data["items"][0].update(publication_date="2026-02-30"), "day"),
    ],
)
def test_ingest_rejects_bad_manifests_without_writing(
    anthology, manifest, change, message
):
    change(manifest)
    with pytest.raises(ValueError, match=message):
        ingest_media(anthology, decode_manifest(manifest))
    assert not list((anthology.datadir / "xml").glob("*.xml"))


def test_ingest_requires_explicit_recording_permission(manifest):
    del manifest["items"][0]["audios"][0]["permission"]
    with pytest.raises(msgspec.ValidationError, match="permission"):
        decode_manifest(manifest)


def test_ingest_rejects_unknown_manifest_fields(manifest):
    manifest["items"][0]["episdoe"] = "7"
    with pytest.raises(msgspec.ValidationError, match="episdoe"):
        decode_manifest(manifest)


def test_legacy_migration_preserves_recordings_and_people(anthology):
    collection = anthology.create_collection("2026.recordings")
    collection.create_event(
        title="Fictional Conference",
        talks=[
            Talk(
                title="Keynote: Invented NLP languages",
                speakers=[
                    NameSpecification(Name("Rhea", "Example")),
                    NameSpecification(Name("Rhea", "Example")),
                ],
                attachments={"video": URLReference("old-keynote-filename.mp4")},
            ),
            Talk(
                title="Business Meeting",
                attachments={"audio": URLReference("old-meeting-filename.mp3")},
            ),
        ],
    )
    video_url = collection.event.talks[0].attachments["video"].url
    audio_url = collection.event.talks[1].attachments["audio"].url
    items = migrate_talks(anthology)
    assert [item.full_id for item in items] == [
        "2026.recordings-media.1",
        "2026.recordings-media.2",
    ]
    assert items[0].type == MediaType.KEYNOTE
    assert items[1].type == MediaType.MEETING
    assert items[0].videos[0].url == video_url
    assert items[1].audios[0].url == audio_url
    assert items[0].authors[0].resolve().id == "rhea-example/unverified"
    assert len(items[0].authors) == 1
    assert "<fixed-case>NLP</fixed-case>" in items[0].title.as_xml()
    assert collection.event.talks == []
    assert set(item.full_id for item in collection.event.media()) == {
        item.full_id for item in items
    }
    anthology.save_all()
    collection.validate_schema()
    reloaded = Anthology(anthology.datadir)
    assert migrate_talks(reloaded) == []
    assert reloaded.get(items[0].full_id).to_bibtex() == items[0].to_bibtex()


def test_migration_preflights_volume_collisions(anthology):
    collection = anthology.create_collection("2026.recordings")
    event = collection.create_event(talks=[Talk(title="A talk")])
    collection.create_volume("media", title="Already exists", type=VolumeType.MEDIA)
    with pytest.raises(ValueError, match="already exists"):
        migrate_talks(anthology)
    assert len(event.talks) == 1
    assert not list(anthology.media())


def test_media_only_event_has_media_without_fake_paper_volumes(
    anthology, manifest, tmp_path
):
    item = ingest_media(anthology, decode_manifest(manifest))[0]
    target = tmp_path / "export"
    export_anthology(anthology, target)
    event = json.loads((target / "data/events.json").read_text())["recordings-2026"]
    assert event["volumes"] == []
    assert event["volume_count"] == 0
    assert event["paper_count"] == 0
    assert event["media_count"] == 1
    assert event["media"] == [item.full_id]


@pytest.mark.parametrize(
    "url, kind, expected",
    [
        (
            "https://example.org/file.webm?download=1",
            "video",
            {"mime_type": "video/webm"},
        ),
        ("https://example.org/file.mp3", "audio", {"mime_type": "audio/mpeg"}),
        (
            "https://www.youtube.com/watch?v=abcdefghijk",
            "video",
            {"embed_url": "https://www.youtube-nocookie.com/embed/abcdefghijk"},
        ),
        (
            "https://youtu.be/abcdefghijk",
            "video",
            {"embed_url": "https://www.youtube-nocookie.com/embed/abcdefghijk"},
        ),
        (
            "https://vimeo.com/123456",
            "video",
            {"embed_url": "https://player.vimeo.com/video/123456"},
        ),
        ("https://example.org/watch", "video", {}),
        ("https://youtube.com.example.org/watch?v=abcdefghijk", "video", {}),
        ("https://www.youtube.com/watch?v=invalid", "video", {}),
    ],
)
def test_recording_players_are_format_and_provider_aware(url, kind, expected):
    reference = VideoReference(url) if kind == "video" else AudioReference(url)
    assert recording_to_dict(reference, kind) == {"url": url, "kind": kind, **expected}


@pytest.fixture
def exported_site(anthology, manifest, tmp_path):
    podcast = ingest_media(anthology, decode_manifest(manifest))[0]
    collection = anthology.get_collection(manifest["collection"])
    collection.create_event(title="Fictional Conference")
    media = collection.create_volume(
        "media",
        title="Fictional Talks and Meetings",
        type=VolumeType.MEDIA,
        venue_ids=["recordings"],
    )
    keynote = media.create_media(
        title="A fabricated keynote",
        type=MediaType.KEYNOTE,
        authors=[NameSpecification(Name("Rhea", "Example"))],
        videos=[VideoReference("keynote.mp4")],
    )
    restricted = media.create_media(
        title="A restricted meeting",
        type=MediaType.MEETING,
        audios=[AudioReference("PRIVATE-SENTINEL.mp3", permission=False)],
    )
    proceedings = collection.create_volume(
        "main",
        title="Fictional Proceedings",
        venue_ids=["recordings"],
        editors=[NameSpecification(Name("Ellis", "Example"))],
    )
    paper = proceedings.create_paper(
        title="A fabricated paper",
        authors=[NameSpecification(Name("Rhea", "Example"))],
    )
    site = tmp_path / "site"
    shutil.copytree(
        ROOT / "hugo",
        site,
        ignore=shutil.ignore_patterns(
            "resources", "public", "website", ".hugo_build.lock"
        ),
    )
    export_anthology(anthology, site, clean=True)
    return site, anthology, podcast, keynote, restricted, paper


def test_media_exports_and_paper_metrics_are_separate(exported_site):
    site, anthology, podcast, keynote, restricted, paper = exported_site
    homepage = json.loads((site / "data/homepage.json").read_text())
    assert homepage["paper_count"] == 1
    assert homepage["media_count"] == 3
    assert homepage["volume_count"] == 1
    stats = author_stats(anthology.volumes())
    assert stats["paper_count"] == 1
    assert stats["media_count"] == 3
    assert compute_authorship_stats(anthology)["years"] == [
        {"year": 2026, "authorships": [0, 0, 0, 1], "authors": [0, 0, 0, 1]}
    ]
    people = json.loads((site / "data/people.json").read_text())
    person = people["rhea-example/unverified"]
    assert person["papers"] == [paper.full_id]
    assert set(person["media"]) == {podcast.full_id, keynote.full_id}
    editor = people["ellis-example/unverified"]
    assert editor["papers"] == []
    assert editor["volumes"] == [paper.parent.full_id]
    event = json.loads((site / "data/events.json").read_text())["recordings-2026"]
    assert event["volumes"] == [paper.parent.full_id]
    assert set(event["media"]) == {podcast.full_id, keynote.full_id, restricted.full_id}
    assert event["media_count"] == 3
    volumes = json.loads((site / "data/volumes.json").read_text())
    assert volumes[podcast.parent.full_id]["papers"] == []
    assert volumes[podcast.parent.full_id]["media"] == [podcast.full_id]
    data = record_to_dict(podcast)
    assert json.loads(data["csl_json"])["type"] == "broadcast"
    assert data["schema_org"]["datePublished"] == "2026-03-21"
    assert data["schema_org"]["duration"] == "PT3600S"
    assert data["recordings"][0]["mime_type"] == "audio/mpeg"
    restricted_data = record_to_dict(restricted)
    assert "PRIVATE-SENTINEL" not in json.dumps(restricted_data)
    assert restricted_data["recordings"] == []
    assert (
        podcast.to_bibtex()
        in (site / f"data-export/volumes/{podcast.parent.full_id}.bib").read_text()
    )


def test_removed_media_do_not_expose_recordings(anthology, manifest):
    item = ingest_media(anthology, decode_manifest(manifest))[0]
    item.deletion = PaperDeletionNotice("removed", "Withdrawn", "2026-03-22")
    data = record_to_dict(item)
    assert data["recordings"] == []
    assert item.audios[0].url not in json.dumps(data)


def test_unavailable_recordings_retain_permission_but_are_not_embedded(
    anthology, manifest
):
    manifest["items"][0]["audios"][0]["available"] = False
    item = ingest_media(anthology, decode_manifest(manifest))[0]
    assert item.audios[0].permission
    assert not item.audios[0].available
    assert "episode-7.mp3" not in json.dumps(record_to_dict(item))
    assert item.web_url in item.to_bibtex()


@pytest.fixture
def rendered_site(exported_site):
    if not shutil.which("hugo"):
        pytest.skip("Hugo is required for the media rendering integration test")
    site, *items = exported_site
    result = subprocess.run(
        [
            "hugo",
            "--source",
            str(site),
            "--destination",
            str(site / "public"),
            "--baseURL",
            "http://localhost:8765/",
            "--environment",
            "development",
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return site / "public", items


def test_media_pages_render_with_players_citations_and_discovery(rendered_site):
    public, (_, podcast, keynote, restricted, paper) = rendered_site
    page = html.parse(public / podcast.full_id / "index.html")
    assert page.xpath("//audio/source/@src") == [podcast.audios[0].url]
    assert page.xpath("//audio/source/@type") == ["audio/mpeg"]
    assert not page.xpath('//*[@id="metadataModal"]')
    assert not page.xpath('//meta[@name="citation_conference_title"]')
    assert page.xpath('//meta[@name="citation_publication_date"]/@content') == [
        "2026-03-21"
    ]
    assert page.xpath('//*[@id="citeBibtexContent"]')[0].text.startswith("@misc{")
    assert (
        json.loads(page.xpath('//*[@id="citeCSLContent"]')[0].text)["type"] == "broadcast"
    )
    assert (
        json.loads(page.xpath('//script[@type="application/ld+json"]')[0].text)["@type"]
        == "PodcastEpisode"
    )
    assert page.xpath('//a[contains(@href, "/people/rhea-example/unverified/")]')
    correction_url = page.xpath(
        '//a[@aria-label="Suggest a correction for this recording"]/@href'
    )[0]
    assert parse_qs(urlsplit(correction_url).query)["title"] == [
        f"Media correction: {podcast.full_id}"
    ]
    video_page = html.parse(public / keynote.full_id / "index.html")
    assert video_page.xpath("//video/source/@src") == [keynote.videos[0].url]
    restricted_page = (public / restricted.full_id / "index.html").read_text()
    assert "PRIVATE-SENTINEL" not in restricted_page
    assert "No recording is currently available" in restricted_page
    ordinary_page = html.parse(public / paper.full_id / "index.html")
    assert ordinary_page.xpath('//*[@id="metadataModal"]')
    assert ordinary_page.xpath('//meta[@name="citation_conference_title"]')
    for path in (
        public / "media/index.html",
        public / "events/recordings-2026/index.html",
        public / "people/rhea-example/unverified/index.html",
        public / "volumes" / podcast.parent.full_id / "index.html",
    ):
        document = html.parse(path)
        assert document.xpath(f'//a[@href="/{podcast.full_id}/"]'), path
    editor_page = html.parse(public / "people/ellis-example/unverified/index.html")
    assert editor_page.xpath('//h3[text()="Edited volumes"]')
    assert editor_page.xpath(f'//a[@href="/volumes/{paper.parent.full_id}/"]')
    result = subprocess.run(
        [sys.executable, str(public / "cgi-bin/extract_citation.cgi")],
        cwd=public / "cgi-bin",
        env={
            **os.environ,
            "QUERY_STRING": f"anthology_id={podcast.full_id}&format=bib",
        },
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Content-Type: text/plain" in result.stdout
    assert podcast.to_bibtex(with_abstract=False) in result.stdout


def test_media_citations_convert_to_mods_and_endnote(exported_site, monkeypatch):
    from bin import create_extra_bib

    bib2xml = shutil.which("bib2xml")
    xml2end = shutil.which("xml2end")
    if not bib2xml or not xml2end:
        pytest.skip("bibutils is required for MODS and Endnote conversion")
    monkeypatch.setattr(create_extra_bib, "BIB2XML", bib2xml, raising=False)
    monkeypatch.setattr(create_extra_bib, "XML2END", xml2end, raising=False)
    site, _, podcast, *_ = exported_site
    collection_file = site / f"data/records/{podcast.collection_id}.json"
    create_extra_bib.convert_collection_file(collection_file)
    data = json.loads(collection_file.read_text())[podcast.full_id]
    assert podcast.title.as_text() in data["mods"]
    assert podcast.web_url in data["mods"]
    assert podcast.title.as_text() in data["endf"]
    assert podcast.web_url in data["endf"]
    assert "Audio recording" in data["mods"]
    volume_file = site / f"data-export/volumes/{podcast.parent.full_id}.bib"
    create_extra_bib.convert_volume_bib_file(volume_file)
    assert volume_file.with_suffix(".xml").is_file()
    assert volume_file.with_suffix(".enw").is_file()


def test_conference_doi_automation_skips_media(exported_site, monkeypatch, caplog):
    _, anthology, podcast, keynote, _, paper = exported_site
    monkeypatch.setattr(
        "bin.add_dois.add_doi_to_item",
        lambda *args, **kwargs: pytest.fail("Media must not receive conference DOIs"),
    )
    assert process_volume(anthology, podcast.parent.full_id) == 0
    with caplog.at_level("INFO"):
        with pytest.raises(ValueError, match="No proceedings volumes"):
            generate_crossref_xml(
                anthology, [podcast.parent.full_id, keynote.parent.full_id], batch_id=1
            )
    assert "Skipping media volume" in caplog.text
    with pytest.raises(SystemExit):
        resolve_inputs(anthology, [podcast.parent.full_id])
    assert resolve_inputs(anthology, ["recordings-2026"]) == [paper.parent.full_id]
