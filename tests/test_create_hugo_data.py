"""Tests for bin/create_hugo_data.py."""

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.create_hugo_data import (
    export_homepage_stats,
    homepage_stats,
    paper_to_dict,
    recent_top_level_events,
    subtract_months,
)

from acl_anthology import Anthology, config
from acl_anthology.collections.types import EventLink


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
    assert stats["oldest_year"] == "1952"
    assert stats["newest_year"] == max(volume.year for volume in anthology.volumes())


def test_homepage_stats_are_exported(anthology, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    export_homepage_stats(anthology, tmp_path, dryrun=False)

    with open(data_dir / "homepage.json") as f:
        assert json.load(f) == homepage_stats(anthology)


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
