"""Tests for bin/ingest_mitpress.py."""

import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "ingest_mitpress.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("ingest_mitpress", SCRIPT)
INGEST_MITPRESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INGEST_MITPRESS)


def test_ensure_volume_updates_existing_volume_ingest_date():
    existing_volume = SimpleNamespace(ingest_date=None)
    collection = Mock()
    collection.get.return_value = existing_volume
    ingest_date = date(2026, 9, 8)

    volume = INGEST_MITPRESS.ensure_volume(collection, "tacl", 2026, "1", {}, ingest_date)

    assert volume is existing_volume
    assert volume.ingest_date == ingest_date
    collection.create_volume.assert_not_called()


def test_ensure_volume_sets_new_volume_ingest_date():
    collection = Mock()
    collection.get.return_value = None
    ingest_date = date(2026, 9, 8)
    paper = {
        "booktitle": "Computational Linguistics, Volume 52, Issue 2 - June 2026",
        "month": "June",
        "journal_volume": "52",
        "journal_issue": "2",
    }

    INGEST_MITPRESS.ensure_volume(collection, "cl", 2026, "2", paper, ingest_date)

    collection.create_volume.assert_called_once_with(
        "2",
        title=paper["booktitle"],
        type="journal",
        year="2026",
        month="June",
        publisher="MIT Press",
        address="Cambridge, MA",
        venue_ids=["cl"],
        journal_volume="52",
        journal_issue="2",
        ingest_date=ingest_date,
    )
