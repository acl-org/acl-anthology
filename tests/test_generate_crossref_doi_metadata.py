"""Regression tests for bin/generate_crossref_doi_metadata.py."""

import sys
from pathlib import Path

import pytest

# Ensure the bin directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.generate_crossref_doi_metadata import (
    classify_input,
    generate_crossref_xml,
    resolve_inputs,
)

from acl_anthology import Anthology

DATADIR = Path(__file__).resolve().parent.parent / "data"
GOLDEN_DIR = Path(__file__).resolve().parent / "data"
FIXED_BATCH_ID = 1000000000


@pytest.fixture(scope="module")
def anthology():
    return Anthology(datadir=DATADIR)


# -------------------------------------------------------------------
# classify_input tests
# -------------------------------------------------------------------


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("2024.emnlp-main", ("volume", "2024.emnlp-main")),
        ("W10-17", ("volume", "W10-17")),
        ("P19-1", ("volume", "P19-1")),
        ("N12-1", ("volume", "N12-1")),
        ("naacl-2012", ("event", "naacl-2012")),
        ("acl-2025", ("event", "acl-2025")),
        ("emnlp-2024", ("event", "emnlp-2024")),
    ],
)
def test_classify_input(identifier, expected):
    assert classify_input(identifier) == expected


def test_classify_input_invalid():
    with pytest.raises(SystemExit):
        classify_input("not-valid-at-all-123")


# -------------------------------------------------------------------
# Event resolution tests
# -------------------------------------------------------------------


def test_event_resolution_naacl_2012(anthology):
    volume_ids = resolve_inputs(anthology, ["naacl-2012"])
    expected = sorted(
        ["N12-1", "N12-2", "N12-3", "N12-4", "W12-18", "W12-19", "W12-25", "W12-27"]
    )
    assert volume_ids == expected


def test_volume_passthrough(anthology):
    volume_ids = resolve_inputs(anthology, ["W10-17"])
    assert volume_ids == ["W10-17"]


def test_mixed_input(anthology):
    """Volumes and events can be mixed; volumes from events are merged."""
    volume_ids = resolve_inputs(anthology, ["W10-17", "naacl-2012"])
    assert "W10-17" in volume_ids
    assert "N12-1" in volume_ids


# -------------------------------------------------------------------
# XML generation regression tests
# -------------------------------------------------------------------


def test_volume_W10_17(anthology):
    """Regression test: W10-17 output must match golden fixture."""
    xml_bytes = generate_crossref_xml(anthology, ["W10-17"], batch_id=FIXED_BATCH_ID)
    golden = (GOLDEN_DIR / "crossref_W10-17.xml").read_bytes()
    assert xml_bytes == golden


def test_event_naacl_2012(anthology):
    """Regression test: naacl-2012 event output must match golden fixture."""
    volume_ids = resolve_inputs(anthology, ["naacl-2012"])
    xml_bytes = generate_crossref_xml(anthology, volume_ids, batch_id=FIXED_BATCH_ID)
    golden = (GOLDEN_DIR / "crossref_naacl-2012.xml").read_bytes()
    assert xml_bytes == golden
