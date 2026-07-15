"""Tests for bin/create_hugo_data.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.create_hugo_data import export_homepage_stats, homepage_stats, paper_to_dict

from acl_anthology import Anthology, config


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
