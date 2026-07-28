"""Tests for event metadata support in bin/ingest.py."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from bin.ingest import configure_event


def event_args(tmp_path, **overrides):
    values = {
        "event_title": None,
        "event_location": None,
        "event_dates": None,
        "event_website": None,
        "event_handbook": None,
        "event_files_dir": tmp_path,
        "dry_run": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_configure_event_does_nothing_without_metadata(tmp_path):
    collection = MagicMock()

    configure_event(collection, event_args(tmp_path))

    collection.get_event.assert_not_called()


def test_configure_event_updates_existing_event_and_copies_handbook(tmp_path):
    handbook = tmp_path / "source.pdf"
    handbook.write_bytes(b"handbook")
    event = SimpleNamespace(
        title=None,
        location=None,
        dates=None,
        links={"other": "preserved"},
    )
    collection = MagicMock(id="2026.acl")
    collection.get_event.return_value = event
    event_files_dir = tmp_path / "events"

    configure_event(
        collection,
        event_args(
            event_files_dir,
            event_title="64th Annual Meeting",
            event_location="San Diego, California, United States",
            event_dates="July 2–7, 2026",
            event_website="https://2026.aclweb.org",
            event_handbook=handbook,
        ),
    )

    destination = event_files_dir / "handbooks" / "acl" / "2026.acl.handbook.pdf"
    assert destination.read_bytes() == b"handbook"
    assert event.title == "64th Annual Meeting"
    assert event.location == "San Diego, California, United States"
    assert event.dates == "July 2–7, 2026"
    assert event.links["other"] == "preserved"
    assert event.links["website"].name == "https://2026.aclweb.org"
    assert event.links["handbook"].name == "2026.acl.handbook.pdf"
    assert event.links["handbook"].checksum is None


def test_configure_event_creates_event_and_supports_dry_run(tmp_path):
    handbook = tmp_path / "source.pdf"
    handbook.write_bytes(b"handbook")
    event = SimpleNamespace(links={})
    collection = MagicMock(id="2026.acl")
    collection.get_event.return_value = None
    collection.create_event.return_value = event
    event_files_dir = tmp_path / "events"

    configure_event(
        collection,
        event_args(
            event_files_dir,
            event_handbook=handbook,
            dry_run=True,
        ),
    )

    collection.create_event.assert_called_once_with()
    destination = event_files_dir / "handbooks" / "acl" / "2026.acl.handbook.pdf"
    assert not destination.exists()
    assert event.links["handbook"].checksum is None
