"""Tests for bin/add_dois.py."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import shutil

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.generate_crossref_doi_metadata import classify_input, resolve_inputs, DOI_PREFIX
from bin.add_dois import (
    add_doi_to_item,
    process_volume,
    DOI_URL_PREFIX,
)

from acl_anthology import Anthology

DATADIR = Path(__file__).resolve().parent.parent / "data"


# -------------------------------------------------------------------
# classify_input tests (same logic as generate_crossref_doi_metadata)
# -------------------------------------------------------------------


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("2024.emnlp-main", ("volume", "2024.emnlp-main")),
        ("W10-17", ("volume", "W10-17")),
        ("naacl-2012", ("event", "naacl-2012")),
    ],
)
def test_classify_input(identifier, expected):
    assert classify_input(identifier) == expected


def test_classify_input_invalid():
    with pytest.raises(SystemExit):
        classify_input("not-valid-at-all-123")


# -------------------------------------------------------------------
# add_doi_to_item tests (mocked HTTP)
# -------------------------------------------------------------------


def test_add_doi_skips_existing():
    """If item already has a DOI and force=False, it should skip."""
    item = SimpleNamespace(doi="10.18653/v1/existing")
    result = add_doi_to_item(item, "W10-1701", force=False)
    assert result is False
    assert item.doi == "10.18653/v1/existing"


def test_add_doi_force_overwrites():
    """If item already has a DOI but force=True and URL resolves, overwrite."""
    item = SimpleNamespace(doi="10.18653/v1/old")
    mock_response = MagicMock(status_code=200)
    with patch("bin.add_dois.test_url_code", return_value=mock_response):
        result = add_doi_to_item(item, "W10-1701", force=True)
    assert result is True
    assert item.doi == f"{DOI_PREFIX}W10-1701"


def test_add_doi_success():
    """If item has no DOI and URL resolves, add it."""
    item = SimpleNamespace(doi=None)
    mock_response = MagicMock(status_code=200)
    with patch("bin.add_dois.test_url_code", return_value=mock_response):
        result = add_doi_to_item(item, "W10-1701")
    assert result is True
    assert item.doi == f"{DOI_PREFIX}W10-1701"


def test_add_doi_404():
    """If DOI URL returns 404, don't add."""
    item = SimpleNamespace(doi=None)
    mock_response = MagicMock(status_code=404)
    with patch("bin.add_dois.test_url_code", return_value=mock_response):
        result = add_doi_to_item(item, "W10-1701")
    assert result is False
    assert item.doi is None


def test_add_doi_429_then_success():
    """On 429, retry after pause; succeed on second attempt."""
    item = SimpleNamespace(doi=None)
    resp_429 = MagicMock(status_code=429, headers={"Retry-After": "0"})
    resp_200 = MagicMock(status_code=200)
    with patch("bin.add_dois.test_url_code", side_effect=[resp_429, resp_200]):
        with patch("bin.add_dois.sleep"):
            result = add_doi_to_item(item, "W10-1701")
    assert result is True
    assert item.doi == f"{DOI_PREFIX}W10-1701"


# -------------------------------------------------------------------
# process_volume integration test (mocked HTTP, temp data dir)
# -------------------------------------------------------------------


@pytest.fixture
def temp_anthology(tmp_path):
    """Create a temporary anthology with a copy of W10.xml for write testing."""
    data_copy = tmp_path / "data"
    # Copy just the needed XML and YAML files
    shutil.copytree(DATADIR / "xml", data_copy / "xml")
    shutil.copytree(DATADIR / "yaml", data_copy / "yaml")
    return Anthology(datadir=data_copy)


def test_process_volume_adds_dois(temp_anthology):
    """process_volume should set DOIs on volume and papers when URLs resolve."""
    mock_response = MagicMock(status_code=200)
    with (
        patch("bin.add_dois.test_url_code", return_value=mock_response),
        patch("bin.add_dois.sleep"),
    ):
        num_added = process_volume(temp_anthology, "W10-17")

    # W10-17 has 64 papers (including frontmatter) + 1 volume-level DOI = 65
    assert num_added == 65

    # Verify DOIs are set on the objects
    volume = temp_anthology.get_volume("W10-17")
    assert volume.doi == f"{DOI_PREFIX}W10-17"
    for paper in volume.papers():
        assert paper.doi == f"{DOI_PREFIX}{paper.full_id}"


def test_process_volume_nonexistent(temp_anthology):
    """process_volume should exit if volume doesn't exist."""
    with pytest.raises(SystemExit):
        process_volume(temp_anthology, "Z99-99")
