"""Tests for bin/create_hugo_data.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.create_hugo_data import export_homepage_stats, homepage_stats

from acl_anthology import Anthology


@pytest.fixture(scope="module")
def anthology():
    return Anthology.from_within_repo()


def test_homepage_stats_are_computed_from_anthology(anthology):
    stats = homepage_stats(anthology)
    top_level_venues = [venue for venue in anthology.venues.values() if venue.is_toplevel]

    assert stats["paper_count"] == sum(1 for _ in anthology.papers())
    assert stats["volume_count"] == sum(1 for _ in anthology.volumes())
    assert stats["venue_count"] == len(top_level_venues)
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
