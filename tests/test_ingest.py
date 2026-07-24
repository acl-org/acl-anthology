"""Tests for event metadata support in bin/ingest.py."""

import sys
import logging
import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from bin.ingest import configure_event, check_for_anonymous_pdf  # noqa: E402


DATADIR = Path(__file__).resolve().parent / "data"


# PDFs that still carry an "Anonymous ... submission" header and should be
# flagged by check_for_anonymous_pdf. The supplementary attachments were
# uploaded without de-anonymization, unlike their published main papers.
ANONYMOUS_PDFS = [
    "W18-6417.pdf",
    "2020.conll-1.8.OptionalSupplementaryMaterial.pdf",
    "D18-1202.Attachment.pdf",
    "2020.conll-1.33.OptionalSupplementaryMaterial.pdf",
]

# Properly published (de-anonymized) PDFs that should not be flagged.
CLEAN_PDFS = [
    "W18-6418.pdf",
    "2020.conll-1.8.pdf",
    "D18-1202.pdf",
    "2020.conll-1.33.pdf",
]


@pytest.mark.parametrize("filename", ANONYMOUS_PDFS)
def test_check_for_anonymous_pdf_flags_anonymous(filename, caplog):
    """A PDF containing an "Anonymous ... submission" line should be flagged."""
    pdf_path = DATADIR / filename
    with caplog.at_level(logging.WARNING):
        check_for_anonymous_pdf(str(pdf_path))
    assert any("Potentially anonymous PDF" in record.message for record in caplog.records)


@pytest.mark.parametrize("filename", CLEAN_PDFS)
def test_check_for_anonymous_pdf_accepts_clean(filename, caplog):
    """A properly de-anonymized PDF should not be flagged."""
    pdf_path = DATADIR / filename
    with caplog.at_level(logging.WARNING):
        check_for_anonymous_pdf(str(pdf_path))
    assert not any(
        "Potentially anonymous PDF" in record.message for record in caplog.records
    )


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
