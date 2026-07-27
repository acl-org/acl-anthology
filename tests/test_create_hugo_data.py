"""Tests for bin/create_hugo_data.py."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.create_hugo_data import author_peak_year, fellows_to_dict, paper_to_dict

from acl_anthology import Anthology, config


@pytest.fixture(scope="module")
def anthology():
    return Anthology.from_within_repo()


def test_author_peak_year_prefers_later_year_for_median_tie():
    papers = [
        SimpleNamespace(year=year)
        for year in ("2001", "2001", "2004", "2004", "not-a-year")
    ]

    assert author_peak_year(papers) == 2004


def test_acl_fellows_are_complete_resolved_and_share_timeline_scale(anthology):
    fellows_path = Path(__file__).parent.parent / "data" / "yaml" / "fellows.yaml"

    data = fellows_to_dict(anthology, fellows_path)
    fellows = data["people"]
    timeline = data["timeline"]

    assert len(fellows) == 107
    assert {fellow["year"] for fellow in fellows} == set(range(2011, 2026))
    assert len({fellow["id"] for fellow in fellows}) == len(fellows)
    assert all(fellow["reason"].startswith("For ") for fellow in fellows)
    assert all(
        fellow["timeline_available"] == ("/unverified" not in fellow["id"])
        for fellow in fellows
    )
    assert all(
        (fellow["peak_year"] is not None) == fellow["timeline_available"]
        for fellow in fellows
    )
    assert [fellow["year"] for fellow in fellows] == sorted(
        (fellow["year"] for fellow in fellows), reverse=True
    )

    timeline_fellows = [fellow for fellow in fellows if fellow["timeline_available"]]
    publication_lengths = {len(fellow["publications"]) for fellow in timeline_fellows}
    assert publication_lengths == {timeline["last_year"] - timeline["first_year"] + 1}
    assert all(
        fellow["publications"][0]["year"] == timeline["first_year"]
        and fellow["publications"][-1]["year"] == timeline["last_year"]
        for fellow in timeline_fellows
    )
    assert all(
        "publications" not in fellow
        for fellow in fellows
        if not fellow["timeline_available"]
    )
    assert timeline["max_count"] == max(
        publication["count"]
        for fellow in timeline_fellows
        for publication in fellow["publications"]
    )


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
