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
    author_career_stats,
    author_search_index,
    author_stats,
    career_year_histogram,
    explicitly_colocated_volume_ids,
    export_author_index,
    export_affiliation_map,
    export_homepage_stats,
    first_paper_year_histogram,
    homepage_stats,
    homepage_venue_group,
    homepage_venue_sort_key,
    latest_owned_ingest_date,
    longest_publishing_authors,
    newly_ingested_years,
    paper_to_dict,
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


def test_affiliation_map_aggregates_by_ror_id_not_coordinates(monkeypatch):
    coordinates = {
        "lat": 40.71427,
        "lon": -74.00597,
        "sector": "academic",
        "coordinate_source": "ror-geonames",
    }
    geocache = {
        "Columbia University": {
            **coordinates,
            "ror_id": "https://ror.org/columbia",
        },
        "Columbia University in the City of New York": {
            **coordinates,
            "ror_id": "https://ror.org/columbia",
        },
        "New York University": {
            **coordinates,
            "ror_id": "https://ror.org/nyu",
        },
    }
    monkeypatch.setattr(
        "bin.create_hugo_data.load_affiliation_geocache", lambda: geocache
    )

    def paper(*affiliations):
        return SimpleNamespace(
            authors=[SimpleNamespace(affiliation=value) for value in affiliations]
        )

    anthology = SimpleNamespace(
        papers=lambda: iter(
            [
                paper(
                    "Columbia University",
                    "Columbia University in the City of New York",
                ),
                paper("New York University"),
                paper("Columbia University", "New York University"),
            ]
        )
    )

    data = export_affiliation_map(anthology, builddir=None, dryrun=True)
    points = {point["label"]: point for point in data["points"]}

    assert set(points) == {"Columbia University", "New York University"}
    assert points["Columbia University"]["count"] == 2
    assert points["Columbia University"]["aliases"] == 2
    assert points["New York University"]["count"] == 2
    assert points["Columbia University"]["coordinate_source"] == "ror-geonames"
    assert data["located_points"] == 2
    assert data["sector_totals"]["academic"] == 4


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
            "last_year": 2018,
            "peak_year": 2018,
            "active_year_count": 1,
        },
        "elodie-durand": {
            "full": "Élodie Durand",
            "papers": ["paper-2"],
            "first_year": 2019,
            "last_year": 2020,
            "peak_year": 2020,
            "active_year_count": 2,
        },
        "wei-zhang/unverified": {
            "full": "Wei Zhang",
            "papers": ["paper-3", "paper-4"],
            "first_year": 2021,
            "last_year": 2021,
            "peak_year": 2021,
            "active_year_count": 1,
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
        "career_year_hists": {
            "first": [
                {"year": 2018, "count": 1},
                {"year": 2019, "count": 1},
                {"year": 2020, "count": 0},
                {"year": 2021, "count": 1},
            ],
            "last": [
                {"year": 2018, "count": 1},
                {"year": 2019, "count": 0},
                {"year": 2020, "count": 1},
                {"year": 2021, "count": 1},
            ],
            "peak": [
                {"year": 2018, "count": 1},
                {"year": 2019, "count": 0},
                {"year": 2020, "count": 1},
                {"year": 2021, "count": 1},
            ],
        },
        "longest_publishing_authors": [
            {"id": "elodie-durand", "name": "Élodie Durand", "active_year_count": 2},
            {"id": "ada-lovelace", "name": "Ada Lovelace", "active_year_count": 1},
            {
                "id": "wei-zhang/unverified",
                "name": "Wei Zhang",
                "active_year_count": 1,
            },
        ],
    }
    assert author_stats(people) == expected_stats

    index = author_search_index(people)
    ada_row = [
        "Ada Lovelace",
        "ada-lovelace",
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
        row[0] == "Aarón Galiano-Jiménez" for row in author_search_index(people)["j"]
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
        row for row in author_search_index(people)["y"] if row[1] == "yang-liu-icsi"
    )
    assert row[7] == "Yang Liu"


def test_first_paper_year_histogram_fills_gaps_and_skips_authors_without_papers():
    people = {
        "alice-smith": {"first_year": 2005},
        "bob-jones/unverified": {"first_year": 2005},
        "carol-lee": {"first_year": 2008},
        "editor-only": {"full": "No Papers"},  # no first_year -> excluded
    }
    assert first_paper_year_histogram(people) == [
        {"year": 2005, "count": 2, "verified_count": 1},
        {"year": 2006, "count": 0, "verified_count": 0},
        {"year": 2007, "count": 0, "verified_count": 0},
        {"year": 2008, "count": 1, "verified_count": 1},
    ]


def test_first_paper_year_histogram_is_empty_without_debut_years():
    assert first_paper_year_histogram({"editor-only": {"full": "No Papers"}}) == []


def test_author_career_stats_uses_later_middle_peak_year_for_ties():
    papers = [
        SimpleNamespace(year=year)
        for year in ("2001", "2002", "2002", "2005", "2005", "2008", "unknown")
    ]

    assert author_career_stats(papers) == {
        "first_year": 2001,
        "last_year": 2008,
        "peak_year": 2005,
        "active_year_count": 4,
    }


def test_career_year_histogram_returns_continuous_annual_counts():
    people = {
        "a": {"peak_year": 1998},
        "b": {"peak_year": 2012},
        "b2": {"peak_year": 2012},
        "c": {"peak_year": 2021},
        "d": {"peak_year": 2023},
    }

    histogram = career_year_histogram(people, "peak_year")

    assert histogram[0] == {"year": 1998, "count": 1}
    assert histogram[-1] == {"year": 2023, "count": 1}
    assert histogram[2012 - 1998] == {"year": 2012, "count": 2}
    assert histogram[2022 - 1998] == {"year": 2022, "count": 0}


def test_longest_publishing_authors_includes_ties_at_limit():
    people = {
        f"author-{number}": {
            "full": f"Author {number:03}",
            "active_year_count": 102 - number,
        }
        for number in range(1, 102)
    }
    people["author-101"]["active_year_count"] = 2

    leaders = longest_publishing_authors(people, limit=100)

    assert len(leaders) == 101
    assert leaders[-1]["active_year_count"] == 2


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
