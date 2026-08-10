"""Tests for bin/add_revision.py."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bin.add_revision import main


@pytest.mark.parametrize(
    ("anthology_id", "lookup_method"),
    [
        ("2026.example-1.0", "get_paper"),
        ("2026.example-1", "get_volume"),
    ],
)
def test_main_automatically_replaces_non_revision_targets(
    tmp_path: Path, anthology_id: str, lookup_method: str
) -> None:
    pdf_path = tmp_path / "revision.pdf"
    pdf_path.write_bytes(b"replacement")
    pdf_dir = tmp_path / "pdf"
    explanation = "Corrected the proceedings PDF."
    args = SimpleNamespace(
        anthology_id=anthology_id,
        path=str(pdf_path),
        explanation=explanation,
        issue=None,
        erratum=False,
        replace=False,
        date="2026-08-10",
        repo=None,
    )
    anthology = MagicMock()
    item = MagicMock()
    item.full_id = anthology_id
    item.collection.path = None
    item.pdf.download.side_effect = lambda path: Path(path).write_bytes(b"original")
    getattr(anthology, lookup_method).return_value = item

    with (
        patch("bin.add_revision.Anthology.from_within_repo", return_value=anthology),
        patch("bin.add_revision.validate_file_type"),
        patch("bin.add_revision.resolve_pdf_dir", return_value=pdf_dir),
    ):
        main(args)

    assert (pdf_dir / f"{anthology_id}.orig").read_bytes() == b"original"
    assert (pdf_dir / f"{anthology_id}.pdf").read_bytes() == b"replacement"
    assert (pdf_dir / f"{anthology_id}.README").read_text() == explanation + "\n"
    item.collection.save.assert_called_once_with()