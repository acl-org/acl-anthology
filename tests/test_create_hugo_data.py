"""Tests for bin/create_hugo_data.py."""

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.create_hugo_data import (
    explicitly_colocated_volume_ids,
    export_homepage_stats,
    homepage_venue_group,
    homepage_venue_sort_key,
    homepage_stats,
    latest_owned_ingest_date,
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


def test_venue_data_classifies_workshops(anthology):
    explicitly_colocated_ids = explicitly_colocated_volume_ids(anthology)

    workshop = venue_to_dict("aaas", anthology.venues["aaas"], explicitly_colocated_ids)
    other = venue_to_dict("bcs", anthology.venues["bcs"], explicitly_colocated_ids)

    assert workshop["is_workshop"] is True
    assert other["is_workshop"] is False


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
