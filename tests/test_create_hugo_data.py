"""Tests for bin/create_hugo_data.py."""

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.create_hugo_data import (
    AUTHOR_ID_FROM_NAME,
    AUTHOR_ID_FROM_NAME_UNVERIFIED,
    AUTHOR_INDEX_BUCKETS,
    build_author_search_index,
    compute_author_stats,
    compute_first_paper_year_histogram,
    explicitly_colocated_volume_ids,
    export_author_index,
    export_homepage_stats,
    fellows_to_dict,
    homepage_venue_group,
    homepage_venue_sort_key,
    homepage_stats,
    latest_owned_ingest_date,
    newly_ingested_years,
    paper_to_dict,
    publication_decades,
    venue_to_dict,
)

from acl_anthology import Anthology, config
from acl_anthology.collections.types import EventLink
from acl_anthology.constants import UNKNOWN_INGEST_DATE


@pytest.fixture(scope="module")
def anthology():
    return Anthology.from_within_repo()


def test_publication_decades_group_years_and_scale_per_author():
    decades = publication_decades(Counter({1998: 1, 2001: 2, 2004: 8}))

    assert [decade["label"] for decade in decades] == ["1990s", "2000s"]
    assert all(len(decade["years"]) == 10 for decade in decades)
    assert [year["year"] for year in decades[0]["years"]] == list(range(1990, 2000))
    assert {
        year["year"]: year["level"] for decade in decades for year in decade["years"]
    } == {
        **dict.fromkeys(range(1990, 1998), 0),
        1998: 1,
        1999: 0,
        2000: 0,
        2001: 1,
        2002: 0,
        2003: 0,
        2004: 4,
        **dict.fromkeys(range(2005, 2010), 0),
    }


def test_acl_fellows_are_complete_resolved_and_have_timelines(anthology):
    fellows_path = Path(__file__).parent.parent / "data" / "yaml" / "fellows.yaml"
    static_path = Path(__file__).parent.parent / "hugo" / "static"

    data = fellows_to_dict(anthology, fellows_path)
    fellows = data["people"]

    assert len(fellows) == 107
    assert {fellow["year"] for fellow in fellows} == set(range(2011, 2026))
    assert len({fellow["id"] for fellow in fellows}) == len(fellows)
    assert all(fellow["reason"].startswith("For ") for fellow in fellows)
    assert all(fellow["photo"].startswith("images/fellows/") for fellow in fellows)
    assert all(fellow["photo_source"].startswith("http") for fellow in fellows)
    for fellow in fellows:
        photo_path = static_path / fellow["photo"]
        assert photo_path.is_file()
        with Image.open(photo_path) as photo:
            assert photo.format == "WEBP"
            assert photo.size == (400, 600)
    assert all(
        fellow["timeline_available"] == ("/unverified" not in fellow["id"])
        for fellow in fellows
    )
    assert [fellow["year"] for fellow in fellows] == sorted(
        (fellow["year"] for fellow in fellows), reverse=True
    )

    timeline_fellows = [fellow for fellow in fellows if fellow["timeline_available"]]
    assert all(
        all(len(decade["years"]) == 10 for decade in fellow["publication_decades"])
        for fellow in timeline_fellows
    )
    assert all(
        all(
            year["level"] == 0 if year["count"] == 0 else 1 <= year["level"] <= 4
            for decade in fellow["publication_decades"]
            for year in decade["years"]
        )
        for fellow in timeline_fellows
    )
    assert all(
        max(
            year["level"]
            for decade in fellow["publication_decades"]
            for year in decade["years"]
        )
        == 4
        for fellow in timeline_fellows
    )
    assert all(
        "publication_decades" not in fellow
        for fellow in fellows
        if not fellow["timeline_available"]
    )


def test_lifetime_achievement_awards_are_complete_and_interspersed(anthology):
    data_path = Path(__file__).parent.parent / "data" / "yaml"
    data = fellows_to_dict(
        anthology,
        data_path / "fellows.yaml",
        data_path / "lifetime-achievement-awards.yaml",
    )
    fellows = data["people"]
    awards = data["lifetime_achievement_awards"]
    honorees = data["honorees"]

    assert len(fellows) == 107
    assert len(awards) == 24
    assert len(honorees) == 131
    assert {award["year"] for award in awards} == set(range(2002, 2026))
    assert all(award["honor"] == "lifetime-achievement-award" for award in awards)
    assert [honoree["year"] for honoree in honorees] == sorted(
        (honoree["year"] for honoree in honorees), reverse=True
    )
    for year in range(2011, 2026):
        year_honorees = [honoree for honoree in honorees if honoree["year"] == year]
        assert year_honorees[0]["honor"] == "lifetime-achievement-award"

    article_awards = [
        award
        for award in awards
        if award.get("talk_url", "").startswith("https://aclanthology.org/")
        and not award["talk_url"].endswith(".mp4")
    ]
    assert len(article_awards) == 20
    for award in article_awards:
        paper_id = urlparse(award["talk_url"]).path.strip("/")
        paper = anthology.get_paper(paper_id)
        assert paper is not None
        assert award["talk_title"] in str(paper.title)

    awards_by_year = {award["year"]: award for award in awards}
    assert awards_by_year[2014]["talk_url"] == (
        "https://aclanthology.org/2014.acl-lat.1.mp4"
    )
    assert awards_by_year[2025]["talk_url"].startswith("https://direct.mit.edu/")
    assert all("talk_url" not in awards_by_year[year] for year in (2002, 2003))
    assert awards_by_year[2018]["photo"] == "images/fellows/mark-steedman.webp"


def test_homepage_stats_are_computed_from_anthology(anthology):
    stats = homepage_stats(anthology)
    top_level_venues = [venue for venue in anthology.venues.values() if venue.is_toplevel]

    assert stats["paper_count"] == sum(1 for _ in anthology.papers())
    assert stats["author_count"] == len(anthology.people)
    assert stats["volume_count"] == sum(1 for _ in anthology.volumes())
    assert stats["venue_count"] == len(anthology.venues)
    assert stats["venue_year_count"] == sum(
        len({volume.year for volume in venue.volumes()}) for venue in top_level_venues
    )
    assert stats["oldest_year"] == min(volume.year for volume in anthology.volumes())
    assert stats["newest_year"] == max(volume.year for volume in anthology.volumes())


def test_homepage_stats_are_exported(anthology, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    export_homepage_stats(anthology, tmp_path, dryrun=False)

    with open(data_dir / "homepage.json") as f:
        assert json.load(f) == homepage_stats(anthology)


def test_author_index_data_supports_stats_and_token_lookup(tmp_path):
    people = {
        "ada-lovelace": {
            "full": "Ada Lovelace",
            "papers": ["paper-1"],
            "orcid": "0000-0000-0000-0001",
            "variant_entries": [
                {"full": "Augusta Ada King"},
                {"full": "Ada King, Countess of Lovelace"},
            ],
            "name_variants": ["埃达·洛夫莱斯"],
            "comment": "Analytical Engine Institute",
            "first_year": 2018,
        },
        "elodie-durand": {
            "full": "Élodie Durand",
            "papers": ["paper-2"],
            "first_year": 2019,
        },
        "wei-zhang/unverified": {
            "full": "Wei Zhang",
            "papers": ["paper-3", "paper-4"],
            "first_year": 2021,
        },
    }

    expected_stats = {
        "author_count": 3,
        "verified_author_count": 2,
        "unverified_author_count": 1,
        "orcid_author_count": 1,
        "first_paper_year_hist": [
            {"year": 2018, "count": 1, "verified_count": 1},
            {"year": 2019, "count": 1, "verified_count": 1},
            {"year": 2020, "count": 0, "verified_count": 0},
            {"year": 2021, "count": 1, "verified_count": 0},
        ],
    }
    assert compute_author_stats(people) == expected_stats

    index = build_author_search_index(people)
    ada_row = [
        "Ada Lovelace",
        0,  # ID rebuilt from the name by the browser
        1,
        "0000-0000-0000-0001",
        ["Augusta Ada King", "Ada King, Countess of Lovelace"],
        "Analytical Engine Institute",
        ["埃达·洛夫莱斯"],
    ]
    assert ada_row in index["a"]
    assert ada_row in index["k"]
    assert ada_row in index["l"]
    assert ada_row in index["other"]
    assert any(row[0] == "Élodie Durand" for row in index["e"])
    assert any(row[0] == "Wei Zhang" for row in index["z"])

    (tmp_path / "data").mkdir()
    stale_paper_index = tmp_path / "static" / "people" / "index" / "papers"
    stale_paper_index.mkdir(parents=True)
    (stale_paper_index / "old.json").write_text("[]")
    export_author_index(people, tmp_path)

    with open(tmp_path / "data" / "people_stats.json") as f:
        exported_stats = json.load(f)
    assert exported_stats == expected_stats
    index_dir = tmp_path / "static" / "people" / "index"
    assert {path.stem for path in index_dir.glob("*.json")} == set(AUTHOR_INDEX_BUCKETS)
    with open(index_dir / "l.json") as f:
        assert ada_row in json.load(f)
    assert not stale_paper_index.exists()


def test_author_index_includes_hyphenated_name_parts():
    people = {
        "aaron-galiano-jimenez": {
            "full": "Aarón Galiano-Jiménez",
            "papers": ["paper-1"],
            "variant_entries": [],
        }
    }

    assert any(
        row[0] == "Aarón Galiano-Jiménez"
        for row in build_author_search_index(people)["j"]
    )


def test_author_index_includes_undecorated_canonical_name_for_ranking():
    people = {
        "yang-liu-icsi": {
            "first": "Yang",
            "last": "Liu",
            "full": "Yang Liu (刘扬)",
            "papers": ["paper-1"],
            "variant_entries": [{"full": "刘扬"}],
            "name_variants": ["刘扬"],
        }
    }

    row = next(
        row
        for row in build_author_search_index(people)["y"]
        if row[0] == "Yang Liu (刘扬)"
    )
    assert row[1] == "yang-liu-icsi"
    assert row[7] == "Yang Liu"


def test_author_index_omits_ids_the_browser_can_rebuild():
    people = {
        "ada-lovelace": {"full": "Ada Lovelace", "papers": ["paper-1"]},
        "wei-zhang/unverified": {"full": "Wei Zhang", "papers": ["paper-2"]},
        # 'ø' survives NFKD, so this ID cannot be derived and is kept verbatim
        "anne-moller": {"full": "Anne Møller", "papers": ["paper-3"]},
    }

    rows = {row[0]: row for row in build_author_search_index(people)["a"]}
    assert rows["Ada Lovelace"][1] == AUTHOR_ID_FROM_NAME
    assert rows["Anne Møller"][1] == "anne-moller"
    zhang = next(row for row in build_author_search_index(people)["z"])
    assert zhang[1] == AUTHOR_ID_FROM_NAME_UNVERIFIED


def test_author_index_drops_trailing_empty_fields():
    people = {"ada-lovelace": {"full": "Ada Lovelace", "papers": ["paper-1"]}}

    (row,) = build_author_search_index(people)["a"]

    assert row == ["Ada Lovelace", AUTHOR_ID_FROM_NAME, 1]


def test_first_paper_year_histogram_fills_gaps_and_skips_authors_without_papers():
    people = {
        "alice-smith": {"first_year": 2005},
        "bob-jones/unverified": {"first_year": 2005},
        "carol-lee": {"first_year": 2008},
        "editor-only": {"full": "No Papers"},  # no first_year -> excluded
    }
    assert compute_first_paper_year_histogram(people) == [
        {"year": 2005, "count": 2, "verified_count": 1},
        {"year": 2006, "count": 0, "verified_count": 0},
        {"year": 2007, "count": 0, "verified_count": 0},
        {"year": 2008, "count": 1, "verified_count": 1},
    ]


def test_first_paper_year_histogram_is_empty_without_debut_years():
    assert (
        compute_first_paper_year_histogram({"editor-only": {"full": "No Papers"}}) == []
    )


def test_latest_owned_ingest_date_ignores_explicitly_colocated_volumes():
    own_id = ("parent-2026", "1", None)
    child_id = ("child-2026", "1", None)
    anthology = SimpleNamespace(
        events={
            "parent-2026": SimpleNamespace(
                colocated_ids={
                    own_id: EventLink.INFERRED,
                    child_id: EventLink.EXPLICIT,
                }
            )
        },
    )
    explicitly_colocated_ids = explicitly_colocated_volume_ids(anthology)
    own_volume = SimpleNamespace(full_id_tuple=own_id, ingest_date=date(2026, 6, 1))
    child_volume = SimpleNamespace(full_id_tuple=child_id, ingest_date=date(2026, 7, 1))

    assert explicitly_colocated_ids == {child_id}
    assert latest_owned_ingest_date(
        [own_volume, child_volume], explicitly_colocated_ids
    ) == date(2026, 6, 1)
    assert (
        latest_owned_ingest_date([child_volume], explicitly_colocated_ids)
        == UNKNOWN_INGEST_DATE
    )


def test_newly_ingested_years_uses_45_day_window():
    current_date = date(2026, 7, 30)
    volumes = [
        SimpleNamespace(year="2023", ingest_date=date(2026, 6, 14)),
        SimpleNamespace(year="2024", ingest_date=date(2026, 6, 15)),
        SimpleNamespace(year="2025", ingest_date=date(2026, 7, 31)),
        SimpleNamespace(year="2026", ingest_date=current_date),
    ]

    assert newly_ingested_years(volumes, current_date) == ["2024", "2026"]


def test_homepage_venue_groups_are_prioritized():
    assert homepage_venue_group("updated", ["2026"]) == 1
    assert homepage_venue_group("acl", []) == 2
    assert homepage_venue_group("other", []) == 3
    assert homepage_venue_group("ws", ["2026"]) == 4


def test_homepage_venue_sort_keys_follow_requested_order():
    flagships = ["acl", "aacl", "cl", "emnlp", "findings", "lrec", "naacl", "tacl"]

    assert (
        sorted(
            flagships,
            key=lambda venue_id: homepage_venue_sort_key(venue_id, venue_id.upper(), 2),
        )
        == flagships
    )
    assert homepage_venue_sort_key("starsem", "*SEM", 3) == "3:sem:starsem"


def test_venue_data_uses_latest_owned_volume_ingest_date(anthology):
    venue = anthology.venues["iwslt"]
    explicitly_colocated_ids = explicitly_colocated_volume_ids(anthology)
    data = venue_to_dict("iwslt", venue, explicitly_colocated_ids)

    assert (
        data["latest_ingest_date"]
        == max(
            volume.ingest_date
            for volume in venue.volumes()
            if volume.full_id_tuple not in explicitly_colocated_ids
        ).isoformat()
    )
    assert (
        data["latest_ingest_date"]
        < max(volume.ingest_date for volume in venue.volumes()).isoformat()
    )
    assert data["newly_ingested_years"] == newly_ingested_years(venue.volumes())


def test_venue_data_exports_workshop_type(anthology):
    explicitly_colocated_ids = explicitly_colocated_volume_ids(anthology)

    workshop = venue_to_dict(
        "textgraphs", anthology.venues["textgraphs"], explicitly_colocated_ids
    )
    other = venue_to_dict("bcs", anthology.venues["bcs"], explicitly_colocated_ids)

    assert workshop["type"] == "workshop"
    assert "type" not in other


def test_homepage_group_excludes_parent_event_updates(anthology):
    explicitly_colocated_ids = explicitly_colocated_volume_ids(anthology)
    current_date = date(2026, 7, 30)
    acl = venue_to_dict(
        "acl", anthology.venues["acl"], explicitly_colocated_ids, current_date
    )
    iwslt = venue_to_dict(
        "iwslt", anthology.venues["iwslt"], explicitly_colocated_ids, current_date
    )
    ws = venue_to_dict(
        "ws", anthology.venues["ws"], explicitly_colocated_ids, current_date
    )

    assert acl["homepage_group"] == 1
    assert iwslt["newly_ingested_years"] == ["2026"]
    assert iwslt["homepage_group"] == 3
    assert ws["homepage_group"] == 4


def test_external_paper_url_is_not_exported_as_pdf(anthology):
    data = paper_to_dict(anthology.get_paper("1998.amta-papers.1"))

    assert data["external"] == (
        "https://link.springer.com/chapter/10.1007/3-540-49478-2_1"
    )
    assert "pdf" not in data
    assert "thumbnail" not in data


def test_local_paper_url_is_exported_as_pdf(anthology):
    data = paper_to_dict(anthology.get_paper("2025.acl-long.1"))

    assert data["pdf"] == f"{config.url_prefix}/2025.acl-long.1.pdf"
    assert data["thumbnail"] == f"{config.url_prefix}/thumb/2025.acl-long.1.jpg"
    assert "external" not in data
