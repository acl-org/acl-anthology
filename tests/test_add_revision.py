"""Tests for bin/add_revision.py."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bin.add_revision import main, normalize_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026.example-1.2", "2026.example-1.2"),
        ("2026.example-1.2/", "2026.example-1.2"),
        (
            "[2026.example-1.2](https://aclanthology.org/2026.example-1.2/)",
            "2026.example-1.2",
        ),
    ],
)
def test_normalize_id(value: str, expected: str) -> None:
    assert normalize_id(value) == expected


def test_main_uses_erratum_type_from_issue(tmp_path: Path) -> None:
    anthology_id = "2026.example-1.2"
    pdf_path = tmp_path / "erratum.pdf"
    pdf_path.write_bytes(b"erratum")
    args = SimpleNamespace(
        anthology_id=None,
        path=str(pdf_path),
        explanation=None,
        issue=123,
        erratum=False,
        replace=False,
        date="2026-08-12",
        repo=None,
    )
    issue = SimpleNamespace(
        body=(
            "### Anthology ID\n\n"
            f"[{anthology_id}](https://aclanthology.org/{anthology_id}/)\n\n"
            "### Type of Change\n\nErratum\n\n"
            "### Brief Description of Changes\n\nCorrects Table 2."
        ),
        title="Paper Erratum",
        html_url="https://github.com/acl-org/acl-anthology/issues/123",
    )
    github_repo = MagicMock()
    github_repo.get_issue.return_value = issue
    anthology = MagicMock()
    paper = MagicMock()
    paper.revisions = ()
    paper.errata = ()
    anthology.get_paper.return_value = paper

    with (
        patch("bin.add_revision.Anthology.from_within_repo", return_value=anthology),
        patch("bin.add_revision._get_github_repo", return_value=github_repo),
        patch("bin.add_revision.input", return_value=""),
        patch("bin.add_revision.validate_file_type"),
        patch("bin.add_revision.PDFReference.from_file") as from_file,
        patch("bin.add_revision.add_revision", return_value=None) as add_revision,
    ):
        main(args)

    from_file.return_value.checksum = "new-checksum"
    add_revision.assert_called_once_with(
        anthology,
        anthology_id,
        pdf_path,
        "Corrects Table 2.",
        change_type="erratum",
        date="2026-08-12",
    )


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
