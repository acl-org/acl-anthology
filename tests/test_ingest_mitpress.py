"""Tests for bin/ingest_mitpress.py."""

import importlib.util
import sys
import pytest
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
        save_all=Mock(),
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
    anthology.save_all.assert_called_once_with()


@pytest.fixture
def erratum_ingestion(tmp_path, monkeypatch):
    target = SimpleNamespace(
        doi="10.1162/tacl.a.742",
        full_id="2026.tacl-1.72",
        authors=[],
        errata=(),
    )
    collection = Mock()
    collection.papers.return_value = [target]
    anthology = SimpleNamespace(
        collections={"2026.tacl": collection},
        people=SimpleNamespace(by_name={}),
        papers=lambda: iter([target]),
        save_all=Mock(),
    )
    monkeypatch.setattr(INGEST_MITPRESS, "Anthology", Mock(return_value=anthology))
    download = Mock(return_value=(True, "https://example.test/erratum.pdf"))
    monkeypatch.setattr(INGEST_MITPRESS, "maybe_download_pdf", download)
    monkeypatch.setattr(
        INGEST_MITPRESS.PDFReference,
        "from_file",
        lambda path: INGEST_MITPRESS.PDFReference(Path(path).stem, checksum="12345678"),
    )
    args = SimpleNamespace(
        anthology_dir=str(tmp_path),
        pdfs_dir=str(tmp_path),
        venue="tacl",
        year=2026,
        dry_run=False,
    )
    return SimpleNamespace(
        target=target,
        collection=collection,
        anthology=anthology,
        download=download,
        args=args,
        notice={
            "doi": "10.1162/tacl.x.779",
            "correction_targets": ["10.1162/tacl.a.742"],
        },
    )


def test_ingest_papers_attaches_correction_once(erratum_ingestion):
    state = erratum_ingestion

    first = INGEST_MITPRESS.ingest_papers(state.args, [state.notice])
    second = INGEST_MITPRESS.ingest_papers(state.args, [state.notice])

    assert first["new"] == second["new"] == 0
    assert first["errata_attached"] == 1
    assert second["errata_attached"] == 0
    assert second["existing_errata"] == 1
    assert len(state.target.errata) == 1
    erratum = state.target.errata[0]
    assert erratum.id == "1"
    assert erratum.doi == "10.1162/tacl.x.779"
    assert erratum.pdf.name == "2026.tacl-1.72e1"
    state.download.assert_called_once_with(
        "10.1162/tacl.x.779",
        Path(state.args.pdfs_dir) / "pdf/tacl/2026.tacl-1.72e1.pdf",
        False,
    )
    state.collection.create_volume.assert_not_called()
    state.collection.save.assert_not_called()
    assert state.anthology.save_all.call_count == 2


def test_ingest_papers_correction_can_target_new_paper(erratum_ingestion):
    state = erratum_ingestion
    state.collection.papers.return_value = []
    state.target.title = INGEST_MITPRESS.MarkupText.from_string("Example paper")
    volume = Mock(full_id="2026.tacl-1")
    volume.generate_paper_id.return_value = "72"
    volume.create_paper.return_value = state.target
    state.collection.get.return_value = volume
    original = {
        "doi": state.target.doi,
        "title": "Example paper",
        "authors": [],
        "issue_id": "1",
        "journal_volume": "14",
        "booktitle": "Example journal",
    }

    report = INGEST_MITPRESS.ingest_papers(state.args, [state.notice, original])

    assert report["new"] == 1
    assert report["errata_attached"] == 1
    assert state.target.errata[0].doi == state.notice["doi"]
    assert state.download.call_count == 2


def test_ingest_papers_correction_dry_run(erratum_ingestion):
    state = erratum_ingestion
    state.args.dry_run = True

    report = INGEST_MITPRESS.ingest_papers(state.args, [state.notice])

    assert report["new"] == 0
    assert report["errata_attached"] == 1
    assert state.target.errata == ()
    state.anthology.save_all.assert_not_called()
    assert state.download.call_args.args[2] is True


def test_ingest_papers_correction_can_target_another_collection(erratum_ingestion):
    state = erratum_ingestion
    state.target.full_id = "2025.tacl-1.72"
    state.collection.papers.return_value = []

    report = INGEST_MITPRESS.ingest_papers(state.args, [state.notice])

    assert report["errata_attached"] == 1
    assert state.target.errata[0].pdf.name == "2025.tacl-1.72e1"
    state.anthology.save_all.assert_called_once_with()


def test_ingest_papers_correction_uses_legacy_pdf_directory(erratum_ingestion):
    state = erratum_ingestion
    state.target.full_id = "Q19-1001"

    INGEST_MITPRESS.ingest_papers(state.args, [state.notice])

    state.download.assert_called_once_with(
        state.notice["doi"],
        Path(state.args.pdfs_dir) / "pdf/Q/Q19/Q19-1001e1.pdf",
        False,
    )


def test_ingest_papers_correction_download_failure_does_not_save(erratum_ingestion):
    state = erratum_ingestion
    state.download.return_value = (False, "https://example.test/erratum.pdf")

    with pytest.raises(RuntimeError, match="PDF download failed for correction DOI"):
        INGEST_MITPRESS.ingest_papers(state.args, [state.notice])

    assert state.target.errata == ()
    state.anthology.save_all.assert_not_called()


@pytest.mark.parametrize("targets", [[], ["10.1162/tacl.a.missing"]])
def test_ingest_papers_correction_requires_target(erratum_ingestion, targets):
    state = erratum_ingestion
    state.notice["correction_targets"] = targets

    with pytest.raises(RuntimeError, match="target DOI"):
        INGEST_MITPRESS.ingest_papers(state.args, [state.notice])

    state.download.assert_not_called()
    state.anthology.save_all.assert_not_called()
    state.collection.create_volume.assert_not_called()


def test_ingest_papers_correction_refuses_ambiguous_legacy_errata(erratum_ingestion):
    state = erratum_ingestion
    state.target.errata = (
        INGEST_MITPRESS.PaperErratum(
            id="1",
            pdf=INGEST_MITPRESS.PDFReference("2026.tacl-1.72e1", checksum="12345678"),
        ),
    )

    with pytest.raises(RuntimeError, match="existing errata have no DOI"):
        INGEST_MITPRESS.ingest_papers(state.args, [state.notice])

    state.download.assert_not_called()
    state.anthology.save_all.assert_not_called()


def test_ingest_papers_correction_preserves_existing_erratum_ids(erratum_ingestion):
    state = erratum_ingestion
    state.target.errata = (
        INGEST_MITPRESS.PaperErratum(
            id="2",
            pdf=INGEST_MITPRESS.PDFReference("2026.tacl-1.72e2", checksum="12345678"),
            doi="10.1162/tacl.x.previous",
        ),
    )

    report = INGEST_MITPRESS.ingest_papers(state.args, [state.notice])

    assert report["errata_attached"] == 1
    assert [erratum.id for erratum in state.target.errata] == ["2", "3"]
    assert state.target.errata[1].pdf.name == "2026.tacl-1.72e3"


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


def test_discover_crossref_items_requests_update_to_metadata(monkeypatch):
    item = {
        "DOI": "10.1162/tacl.x.779",
        "title": ["Erratum: Example paper"],
        "container-title": [
            INGEST_MITPRESS.VENUE_CONFIG[INGEST_MITPRESS.TACL]["journal_title"]
        ],
        "ISSN": ["2307-387X"],
        "published-print": {"date-parts": [[2026, 7, 31]]},
        "volume": "14",
        "update-to": [
            {"DOI": "10.1162/tacl.a.742", "type": "correction", "label": "Correction"}
        ],
    }
    request = Mock(return_value={"message": {"items": [item]}})
    monkeypatch.setattr(INGEST_MITPRESS, "crossref_request_json", request)

    results = INGEST_MITPRESS.discover_crossref_items("tacl", 2026, None)

    assert results == [item]
    assert "update-to" in request.call_args.args[1]["select"]


def test_discover_papers_warns_for_crossref_correction(monkeypatch, caplog):
    correction = {
        "DOI": "10.1162/tacl.x.779",
        "title": ["Erratum: Example paper"],
        "volume": "14",
        "update-to": [
            {"DOI": "10.1162/tacl.a.742", "type": "correction", "label": "Correction"}
        ],
    }
    target = {
        "DOI": "10.1162/tacl.a.742",
        "title": ["Example paper"],
    }
    monkeypatch.setattr(
        INGEST_MITPRESS,
        "discover_crossref_items",
        Mock(return_value=[correction, target]),
    )

    papers = INGEST_MITPRESS.discover_papers(
        SimpleNamespace(venue="tacl", year=2026, volume=None)
    )

    assert papers == [
        {
            "doi": "10.1162/tacl.x.779",
            "correction_targets": ["10.1162/tacl.a.742"],
        }
    ]
    assert "Crossref identifies DOI 10.1162/tacl.x.779" in caplog.text
    assert "as a correction/erratum for" in caplog.text
    assert '"Example paper" (DOI 10.1162/tacl.a.742)' in caplog.text
    assert "attached as an erratum, not ingested standalone" in caplog.text


def test_discover_papers_warns_for_revision_and_identifies_target(monkeypatch, caplog):
    revision = {
        "DOI": "10.1162/tacl.a.900",
        "title": ["Revised: Example paper"],
        "volume": "14",
        "update-to": [
            {"DOI": "10.1162/tacl.a.742", "type": "new-version", "label": "New version"}
        ],
    }
    target = {
        "DOI": "10.1162/tacl.a.742",
        "title": ["Example paper"],
    }
    monkeypatch.setattr(
        INGEST_MITPRESS,
        "discover_crossref_items",
        Mock(return_value=[revision, target]),
    )

    papers = INGEST_MITPRESS.discover_papers(
        SimpleNamespace(venue="tacl", year=2026, volume=None)
    )

    assert papers[0]["doi"] == "10.1162/tacl.a.900"
    assert "as a revision/new-version update" in caplog.text
    assert '"Example paper" (DOI 10.1162/tacl.a.742)' in caplog.text
    assert "attach it to the target paper" in caplog.text
