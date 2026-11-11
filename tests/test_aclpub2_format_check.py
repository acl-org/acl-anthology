"""Tests for bin/aclpub2_format_check.py."""

from types import SimpleNamespace

import pytest
import yaml

from bin.aclpub2_format_check import main


def test_rejects_duplicated_article_in_book_title(tmp_path, caplog):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (tmp_path / "watermarked_pdfs").mkdir()
    (tmp_path / "watermarked_pdfs" / "0.pdf").touch()
    (inputs / "papers.yml").write_text("[]\n")
    (inputs / "conference_details.yml").write_text(
        yaml.safe_dump(
            {
                "anthology_venue_id": "test",
                "volume_name": "main",
                "book_title": "Proceedings of the The Test Workshop",
                "event_name": "Test Workshop",
                "start_date": "2026-01-01",
                "location": "Test City",
                "editors": [],
                "publisher": "Association for Computational Linguistics",
            }
        )
    )

    with pytest.raises(SystemExit):
        main(SimpleNamespace(import_dir=tmp_path, verbose=False))

    assert "contains duplicated 'the'" in caplog.text
