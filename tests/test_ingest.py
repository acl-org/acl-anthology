"""Tests for bin/ingest.py."""

import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from types import SimpleNamespace

from acl_anthology.text import MarkupText
from bin.ingest import (
    abstract_has_empty_markup,
    check_for_anonymous_pdf,
    configure_event,
    ensure_venue,
    read_meta,
    register_volume_with_sig,
)

DATADIR = Path(__file__).resolve().parent / "data"


def test_read_meta_accepts_multiple_spaces_between_key_and_value(tmp_path):
    meta_path = tmp_path / "meta"
    meta_path.write_text("booktitle  Proceedings of EAMT 2026 (Volume 1)\n")

    assert read_meta(str(meta_path))["booktitle"] == (
        "Proceedings of EAMT 2026 (Volume 1)"
    )


def test_ensure_venue_creates_without_saving_individual_venue():
    anthology = MagicMock()
    anthology.venues.__contains__.return_value = False
    venue = anthology.venues.create.return_value

    venue_slug = ensure_venue(
        anthology, "EVALITA", "Evaluation Campaign", is_conference=True
    )

    assert venue_slug == "evalita"
    anthology.venues.create.assert_called_once_with(
        id="evalita", acronym="EVALITA", name="Evaluation Campaign"
    )
    venue.save.assert_not_called()


def test_ensure_venue_requires_type_for_new_venue():
    anthology = MagicMock()
    anthology.venues.__contains__.return_value = False

    with pytest.raises(ValueError, match=r"requires one of -w, -j, or -c"):
        ensure_venue(anthology, "EVALITA", "Evaluation Campaign")

    anthology.venues.create.assert_not_called()


def test_ensure_venue_does_not_require_type_for_existing_venue():
    anthology = MagicMock()
    anthology.venues.__contains__.return_value = True

    assert ensure_venue(anthology, "EVALITA", "Evaluation Campaign") == "evalita"

    anthology.venues.create.assert_not_called()


def test_register_volume_with_sig_stores_sig_on_volume():
    anthology = SimpleNamespace(sigs={"sigdat": object()})
    volume = SimpleNamespace(full_id="2026.acl-main", sig_ids=())

    register_volume_with_sig(anthology, "SIGDAT", volume)
    register_volume_with_sig(anthology, "sigdat", volume)

    assert volume.sig_ids == ("sigdat",)


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


def test_abstract_paragraph_is_not_empty_markup():
    abstract = MarkupText.from_latex("First paragraph.\n\nSecond paragraph.")
    assert not abstract_has_empty_markup(abstract)


def test_abstract_empty_inline_markup_is_rejected():
    abstract = MarkupText.from_latex(r"Text with \textit{} empty markup")
    assert abstract_has_empty_markup(abstract)


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
