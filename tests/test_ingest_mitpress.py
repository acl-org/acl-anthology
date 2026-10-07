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


def test_normalize_author_specs_uses_anthology_name_split():
    incoming_name = INGEST_MITPRESS.Name("Arnab Sen", "Sharma")
    name_split_index = {(incoming_name.slugify(), 2): {1}}

    authors = INGEST_MITPRESS.normalize_author_specs(
        name_split_index, [{"first": "Arnab Sen", "last": "Sharma"}]
    )

    assert authors[0].name == INGEST_MITPRESS.Name("Arnab", "Sen Sharma")


def test_normalize_author_specs_keeps_unknown_name_split():
    authors = INGEST_MITPRESS.normalize_author_specs(
        {}, [{"first": "New", "last": "Author"}]
    )

    assert authors[0].name == INGEST_MITPRESS.Name("New", "Author")


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


def test_remove_margin_watermark_streams_removes_encoded_artifact(tmp_path, monkeypatch):
    article_stream = Mock()
    article_stream.get_object.return_value = article_stream
    article_stream.get_data.return_value = b"BT (Article text) Tj ET"
    watermark_stream = Mock()
    watermark_stream.get_object.return_value = watermark_stream
    watermark_stream.get_data.return_value = (
        b"q\n/Artifact << /Type /Watermark /Subtype /Watermark >> BDC\n"
        b"BT /Xi0 6 Tf (\x00'\x00R\x00Z\x00Q\x00O\x00R\x00D\x00G\x00H\x00G) Tj ET\n"
        b"EMC\nQ\n"
    )
    page = {"/Contents": [article_stream, watermark_stream]}
    reader = SimpleNamespace(pages=[page])
    writer = Mock()
    monkeypatch.setattr(INGEST_MITPRESS, "PdfReader", Mock(return_value=reader))
    monkeypatch.setattr(INGEST_MITPRESS, "PdfWriter", Mock(return_value=writer))

    destination = tmp_path / "clean.pdf"
    removed = INGEST_MITPRESS.remove_margin_watermark_streams(
        tmp_path / "source.pdf", destination
    )

    assert removed == 1
    assert page[INGEST_MITPRESS.NameObject("/Contents")] is article_stream
    writer.add_page.assert_called_once_with(page)
    writer.write.assert_called_once()


def test_find_mitpress_watermark_pages_handles_zero_width_spaces(monkeypatch):
    clean_page = Mock()
    clean_page.extract_text.return_value = "Article text"
    clean_page.get.return_value = None
    watermarked_page = Mock()
    watermarked_page.extract_text.return_value = (
        "Downloaded from www.\u200bmitpressjournals.\u200borg/\u200bdoi/\u200bpdf/"
    )
    watermarked_page.get.return_value = None
    reader = SimpleNamespace(pages=[clean_page, watermarked_page])
    monkeypatch.setattr(INGEST_MITPRESS, "PdfReader", Mock(return_value=reader))

    assert INGEST_MITPRESS.find_mitpress_watermark_pages(Path("paper.pdf")) == [2]


def test_maybe_download_pdf_fails_when_no_watermark_is_removed(tmp_path, monkeypatch):
    destination = tmp_path / "paper.pdf"
    monkeypatch.setattr(
        INGEST_MITPRESS,
        "retrieve_url",
        lambda _url, path: Path(path).write_bytes(b"%PDF-1.7"),
    )
    monkeypatch.setattr(
        INGEST_MITPRESS, "maybe_remove_mitpress_watermark", Mock(return_value=0)
    )
    monkeypatch.setattr(INGEST_MITPRESS, "PDF_DOWNLOAD_RETRIES", 1)

    ok, _ = INGEST_MITPRESS.maybe_download_pdf(
        "10.1162/coli.a.605", destination, dry_run=False
    )

    assert not ok
    assert not destination.exists()


def test_maybe_download_pdf_fails_when_verification_finds_watermark(
    tmp_path, monkeypatch
):
    destination = tmp_path / "paper.pdf"
    monkeypatch.setattr(
        INGEST_MITPRESS,
        "retrieve_url",
        lambda _url, path: Path(path).write_bytes(b"%PDF-1.7"),
    )
    monkeypatch.setattr(
        INGEST_MITPRESS, "maybe_remove_mitpress_watermark", Mock(return_value=1)
    )
    monkeypatch.setattr(
        INGEST_MITPRESS, "find_mitpress_watermark_pages", Mock(return_value=[3])
    )
    monkeypatch.setattr(INGEST_MITPRESS, "PDF_DOWNLOAD_RETRIES", 1)

    ok, _ = INGEST_MITPRESS.maybe_download_pdf(
        "10.1162/coli.a.605", destination, dry_run=False
    )

    assert not ok
    assert not destination.exists()


def test_ingest_papers_does_not_download_pdf_for_existing_paper(tmp_path, monkeypatch):
    existing_paper = SimpleNamespace(
        doi="10.1162/coli.a.605",
        authors=[],
        full_id="2026.cl-2.1",
        pdf=None,
    )
    collection = Mock()
    collection.papers.return_value = [existing_paper]
    anthology = SimpleNamespace(
        collections={"2026.cl": collection},
        people=SimpleNamespace(by_name={}),
    )
    monkeypatch.setattr(INGEST_MITPRESS, "Anthology", Mock(return_value=anthology))
    download_pdf = Mock(return_value=(True, "https://example.test/paper.pdf"))
    monkeypatch.setattr(INGEST_MITPRESS, "maybe_download_pdf", download_pdf)
    from_file = Mock()
    monkeypatch.setattr(INGEST_MITPRESS.PDFReference, "from_file", from_file)
    args = SimpleNamespace(
        anthology_dir=str(tmp_path),
        pdfs_dir=str(tmp_path),
        venue="cl",
        year=2026,
        dry_run=False,
    )

    report = INGEST_MITPRESS.ingest_papers(
        args, [{"doi": "10.1162/coli.a.605", "authors": []}]
    )

    download_pdf.assert_not_called()
    from_file.assert_not_called()
    assert existing_paper.pdf is None
    assert report["existing"] == 1
    assert report["new"] == 0
    collection.save.assert_called_once_with()


def test_main_defaults_to_current_year_for_both_venues(monkeypatch):
    args = INGEST_MITPRESS.build_parser().parse_args([])
    discovered_venues = []
    ingested_venues = []
    monkeypatch.setattr(
        INGEST_MITPRESS,
        "discover_papers",
        lambda venue_args: discovered_venues.append(venue_args.venue) or [],
    )
    monkeypatch.setattr(
        INGEST_MITPRESS,
        "ingest_papers",
        lambda venue_args, papers: ingested_venues.append(venue_args.venue) or {},
    )
    monkeypatch.setattr(INGEST_MITPRESS, "write_report", Mock())

    INGEST_MITPRESS.main(args)

    assert args.year == date.today().year
    assert args.venue is None
    assert discovered_venues == ["cl", "tacl"]
    assert ingested_venues == ["cl", "tacl"]


def test_main_respects_explicit_venue_and_year(monkeypatch):
    args = INGEST_MITPRESS.build_parser().parse_args(
        ["--venue", "tacl", "--year", "2025"]
    )
    discovered = []
    monkeypatch.setattr(
        INGEST_MITPRESS,
        "discover_papers",
        lambda venue_args: discovered.append((venue_args.venue, venue_args.year)) or [],
    )
    monkeypatch.setattr(INGEST_MITPRESS, "ingest_papers", lambda *_args: {})
    monkeypatch.setattr(INGEST_MITPRESS, "write_report", Mock())

    INGEST_MITPRESS.main(args)

    assert discovered == [("tacl", 2025)]
