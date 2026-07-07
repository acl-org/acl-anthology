"""Tests for bin/ingest.py."""

import logging
from pathlib import Path

import pytest

from bin.ingest import check_for_anonymous_pdf  # noqa: E402

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
