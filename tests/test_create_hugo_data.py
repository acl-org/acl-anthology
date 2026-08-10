"""Tests for bin/create_hugo_data.py."""

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.create_hugo_data import (
    AUTHOR_INDEX_BUCKETS,
    author_search_index,
    author_stats,
    explicitly_colocated_volume_ids,
    export_author_index,
    export_homepage_stats,
    first_paper_year_histogram,
    homepage_venue_group,
    homepage_venue_sort_key,
    homepage_stats,
    latest_owned_ingest_date,
    newly_ingested_years,
    paper_search_bucket_keys,
    paper_search_index,
    paper_to_dict,
    recent_top_level_events,
    subtract_months,
    venue_to_dict,
)

from acl_anthology import Anthology, config
from acl_anthology.collections.types import EventLink
from acl_anthology.constants import UNKNOWN_INGEST_DATE


@pytest.fixture(scope="module")
def anthology():
    return Anthology.from_within_repo()


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
            "variant_entries": [{"full": "Augusta Ada King"}],
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
            {"year": 2018, "count": 1},
            {"year": 2019, "count": 1},
            {"year": 2020, "count": 0},
            {"year": 2021, "count": 1},
        ],
    }
    assert author_stats(people) == expected_stats

    index = author_search_index(people)
    ada_row = [
        "Ada Lovelace",
        "ada-lovelace",
        1,
        "0000-0000-0000-0001",
        "Augusta Ada King",
    ]
    assert ada_row in index["a"]
    assert ada_row in index["k"]
    assert ada_row in index["l"]
    assert ada_row in index["other"]
    assert any(row[0] == "Élodie Durand" for row in index["e"])
    assert any(row[0] == "Wei Zhang" for row in index["z"])

    paper_person = SimpleNamespace(id="ada-lovelace")
    paper = SimpleNamespace(
        is_frontmatter=False,
        title=SimpleNamespace(as_text=lambda: "Neural Parsing"),
        full_id="2026.acl-long.1",
        year="2026",
        authors=[
            SimpleNamespace(
                name=SimpleNamespace(as_full=lambda: "Ada Lovelace"),
                resolve=lambda: paper_person,
            )
        ],
    )
    paper_index = paper_search_index([paper], people)

    (tmp_path / "data").mkdir()
    export_author_index(people, tmp_path, [paper])

    with open(tmp_path / "data" / "people_stats.json") as f:
        exported_stats = json.load(f)
    assert exported_stats.pop("paper_search_bucket_counts") == {
        bucket: len(rows) for bucket, rows in paper_index.items()
    }
    assert exported_stats.pop("search_bucket_counts") == {
        bucket: len(rows) for bucket, rows in index.items()
    }
    assert exported_stats == expected_stats
    index_dir = tmp_path / "static" / "people" / "index"
    assert {path.stem for path in index_dir.glob("*.json")} == set(AUTHOR_INDEX_BUCKETS)
    with open(index_dir / "l.json") as f:
        assert ada_row in json.load(f)
    assert {path.stem for path in (index_dir / "papers").glob("*.json")} == set(
        paper_index
    )
    with open(index_dir / "papers" / "neu.json") as f:
        assert json.load(f) == paper_index["neu"]


def test_paper_search_index_supports_titles_authors_and_variants():
    def name(value, person_id):
        person = SimpleNamespace(id=person_id)
        return SimpleNamespace(
            name=SimpleNamespace(as_full=lambda: value),
            resolve=lambda: person,
        )

    def title(value):
        return SimpleNamespace(as_text=lambda: value)

    papers = [
        SimpleNamespace(
            is_frontmatter=False,
            title=title("Neural Parsing for Klingon"),
            full_id="2026.acl-long.1",
            year="2026",
            authors=[name("A. Lovelace", "ada-lovelace")],
        ),
        SimpleNamespace(
            is_frontmatter=True,
            title=title("Proceedings of the Test Conference"),
            full_id="2026.acl-long.0",
            year="2026",
            authors=[],
        ),
    ]
    people = {
        "ada-lovelace": {
            "full": "Ada Lovelace",
            "orcid": "0000-0000-0000-0001",
            "variant_entries": [{"full": "Augusta Ada King"}],
        }
    }

    index = paper_search_index(papers, people)
    row = [
        "Neural Parsing for Klingon",
        "2026.acl-long.1",
        "2026",
        "A. Lovelace",
        "0000-0000-0000-0001 Ada Lovelace Augusta Ada King",
    ]
    for bucket in ("for", "kli", "neu", "par"):
        assert row in index[bucket]
    assert set(index) == {"for", "kli", "neu", "par"}
    assert all(
        all(entry[1] != "2026.acl-long.0" for entry in rows) for rows in index.values()
    )


def test_paper_search_bucket_keys_normalize_accents_and_non_ascii_tokens():
    assert paper_search_bucket_keys("Évaluation of 3D 中文") == {
        "3d",
        "eva",
        "of",
        "other",
    }


def test_first_paper_year_histogram_fills_gaps_and_skips_authors_without_papers():
    people = {
        "a": {"first_year": 2005},
        "b": {"first_year": 2005},
        "c": {"first_year": 2008},
        "editor-only": {"full": "No Papers"},  # no first_year -> excluded
    }
    assert first_paper_year_histogram(people) == [
        {"year": 2005, "count": 2},
        {"year": 2006, "count": 0},
        {"year": 2007, "count": 0},
        {"year": 2008, "count": 1},
    ]


def test_first_paper_year_histogram_is_empty_without_debut_years():
    assert first_paper_year_histogram({"editor-only": {"full": "No Papers"}}) == []


def test_subtract_months_clamps_to_end_of_month():
    assert subtract_months(date(2026, 5, 31), 3) == date(2026, 2, 28)


def test_recent_top_level_events_use_three_month_cutoff():
    def event(event_id, ingest_date, colocated_ids=None):
        volume_id = (event_id, "1", None)
        volume = SimpleNamespace(ingest_date=ingest_date)
        return SimpleNamespace(
            id=event_id,
            colocated_ids=colocated_ids or {volume_id: EventLink.INFERRED},
            volumes=lambda: iter([volume]),
        )

    parent = event(
        "parent-2026",
        date(2026, 7, 14),
        {
            ("parent-2026", "1", None): EventLink.INFERRED,
            ("child-2026", "1", None): EventLink.EXPLICIT,
        },
    )

    anthology = SimpleNamespace(
        events={
            "new-2026": event("new-2026", date(2026, 7, 14)),
            "cutoff-2025": event("cutoff-2025", date(2026, 4, 15)),
            "old-2024": event("old-2024", date(2026, 4, 14)),
            "future-2027": event("future-2027", date(2026, 7, 16)),
            "ws-2026": event("ws-2026", date(2026, 7, 14)),
            "parent-2026": parent,
            "child-2026": event("child-2026", date(2026, 7, 14)),
        },
        venues={
            "new": SimpleNamespace(acronym="NEW", is_toplevel=True),
            "cutoff": SimpleNamespace(acronym="CUT", is_toplevel=True),
            "old": SimpleNamespace(acronym="OLD", is_toplevel=True),
            "future": SimpleNamespace(acronym="FUT", is_toplevel=True),
            "ws": SimpleNamespace(acronym="WS", is_toplevel=True),
            "parent": SimpleNamespace(acronym="PARENT", is_toplevel=True),
            "child": SimpleNamespace(acronym="CHILD", is_toplevel=True),
        },
    )

    assert recent_top_level_events(anthology, date(2026, 7, 15)) == [
        {
            "id": "parent-2026",
            "label": "PARENT 2026",
            "ingest_date": "2026-07-14",
        },
        {"id": "new-2026", "label": "NEW 2026", "ingest_date": "2026-07-14"},
        {
            "id": "cutoff-2025",
            "label": "CUT 2025",
            "ingest_date": "2026-04-15",
        },
    ]


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
