"""Tests for bin/ingest_mitpress.py."""

import importlib.util
import sys
import pytest
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

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


@pytest.fixture
def anthology_with_preferred_author():
    canonical = INGEST_MITPRESS.Name("Barbara", "Di Eugenio")
    alias = INGEST_MITPRESS.Name("Barbara Di", "Eugenio")
    person = SimpleNamespace(
        canonical_name=canonical,
        is_explicit=True,
        disable_name_matching=False,
    )
    paper = SimpleNamespace(
        doi="10.1162/tacl.a.748",
        full_id="2026.tacl-1.78",
        authors=[INGEST_MITPRESS.NameSpec(canonical)],
    )
    collection = Mock()
    collection.papers.return_value = [paper]
    anthology = SimpleNamespace(
        collections={"2026.tacl": collection},
        people=SimpleNamespace(
            by_name={canonical: ["barbara-di-eugenio"], alias: ["barbara-di-eugenio"]},
            values=lambda: iter([person]),
        ),
    )
    return SimpleNamespace(
        anthology=anthology, canonical=canonical, paper=paper, collection=collection
    )


def test_normalize_author_specs_uses_canonical_split(anthology_with_preferred_author):
    state = anthology_with_preferred_author
    index = INGEST_MITPRESS.build_name_split_index(state.anthology)

    authors = INGEST_MITPRESS.normalize_author_specs(
        index, [{"first": "Barbara Di", "last": "Eugenio"}]
    )

    assert authors[0].name == state.canonical


def test_ingest_papers_does_not_replace_canonical_split_with_alias(
    tmp_path, monkeypatch, anthology_with_preferred_author
):
    state = anthology_with_preferred_author
    monkeypatch.setattr(INGEST_MITPRESS, "Anthology", Mock(return_value=state.anthology))
    download = Mock()
    monkeypatch.setattr(INGEST_MITPRESS, "maybe_download_pdf", download)
    args = SimpleNamespace(
        anthology_dir=str(tmp_path),
        pdfs_dir=str(tmp_path),
        venue="tacl",
        year=2026,
        dry_run=False,
    )

    report = INGEST_MITPRESS.ingest_papers(
        args,
        [
            {
                "doi": state.paper.doi,
                "authors": [{"first": "Barbara Di", "last": "Eugenio"}],
            }
        ],
    )

    assert report["existing"] == 1
    assert report["existing_authors_updated"] == 0
    assert state.paper.authors[0].name == state.canonical
    download.assert_not_called()


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


@pytest.mark.parametrize(
    "status, response_url",
    [
        (403, "https://direct.mit.edu/crawlprevention/governor"),
        (429, "https://direct.mit.edu/tacl/article-pdf/paper.pdf"),
        (200, "https://direct.mit.edu/crawlprevention/governor"),
    ],
)
@pytest.mark.parametrize("retry_after", [None, "invalid", "-5"])
def test_maybe_download_pdf_stops_on_publisher_block(
    tmp_path, monkeypatch, caplog, status, response_url, retry_after
):
    destination = tmp_path / "paper.pdf"
    destination.write_bytes(b"existing PDF")
    response = Mock(
        status_code=status,
        url=response_url,
        headers={} if retry_after is None else {"Retry-After": retry_after},
    )
    response.iter_content.return_value = [b"<html>Access blocked</html>"]
    if status >= 400:
        response.raise_for_status.side_effect = INGEST_MITPRESS.requests.HTTPError(
            f"HTTP {status}", response=response
        )
    request = MagicMock()
    request.return_value.__enter__.return_value = response
    monkeypatch.setattr(INGEST_MITPRESS.requests, "get", request)
    sleep = Mock()
    monkeypatch.setattr(INGEST_MITPRESS.time, "sleep", sleep)
    cleanup = Mock()
    monkeypatch.setattr(INGEST_MITPRESS, "maybe_remove_mitpress_watermark", cleanup)

    ok, _ = INGEST_MITPRESS.maybe_download_pdf(
        "10.1162/tacl.a.785", destination, dry_run=False
    )

    assert not ok
    request.assert_called_once()
    sleep.assert_not_called()
    cleanup.assert_not_called()
    assert destination.read_bytes() == b"existing PDF"
    assert list(tmp_path.iterdir()) == [destination]
    assert "Not retrying" in caplog.text
    if retry_after is not None:
        assert "Invalid Retry-After" in caplog.text


@pytest.mark.parametrize("header, expected", [("3600", 3600), ("0", 0), (" 120 ", 120)])
def test_retry_after_delay_seconds(header, expected):
    response = INGEST_MITPRESS.requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = header

    assert INGEST_MITPRESS.retry_after_delay(response) == expected


@pytest.mark.parametrize("seconds", [121, 0, -121])
def test_retry_after_delay_http_date(monkeypatch, seconds):
    now = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)
    header = format_datetime(now + timedelta(seconds=seconds), usegmt=True)
    response = Mock(headers={"Retry-After": header})
    monkeypatch.setattr(INGEST_MITPRESS.time, "time", lambda: now.timestamp())

    assert INGEST_MITPRESS.retry_after_delay(response) == max(0, seconds)


@pytest.mark.parametrize("header", ["", "invalid", "-1", "1.5"])
def test_retry_after_delay_rejects_invalid_header(header, caplog):
    response = Mock(headers={"Retry-After": header}, url="https://example.test/pdf")

    assert INGEST_MITPRESS.retry_after_delay(response) is None
    assert "Invalid Retry-After" in caplog.text


def test_retry_after_delay_missing_header():
    assert INGEST_MITPRESS.retry_after_delay(None) is None
    assert INGEST_MITPRESS.retry_after_delay(Mock(headers={})) is None


@pytest.mark.parametrize("status", [200, 403, 429, 503])
@pytest.mark.parametrize("date_header", [False, True])
def test_maybe_download_pdf_honors_retry_after(
    tmp_path, monkeypatch, status, date_header
):
    destination = tmp_path / "paper.pdf"
    destination.write_bytes(b"existing PDF")
    now = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)
    header = (
        format_datetime(now + timedelta(seconds=3600), usegmt=True)
        if date_header
        else "3600"
    )
    blocked = MagicMock(
        status_code=status,
        url=(
            "https://direct.mit.edu/crawlprevention/governor"
            if status in {200, 403}
            else "https://direct.mit.edu/tacl/article-pdf/paper.pdf"
        ),
        headers={"Retry-After": header},
    )
    blocked.__enter__.return_value = blocked
    blocked.raise_for_status.side_effect = INGEST_MITPRESS.requests.HTTPError(
        f"HTTP {status}", response=blocked
    )
    success = MagicMock(
        status_code=200,
        url="https://example.test/paper.pdf",
        headers={},
    )
    success.__enter__.return_value = success
    success.iter_content.return_value = [b"new PDF"]
    request = Mock(side_effect=[blocked, success])
    monkeypatch.setattr(INGEST_MITPRESS.requests, "get", request)
    monkeypatch.setattr(INGEST_MITPRESS.time, "time", lambda: now.timestamp())

    def wait(seconds):
        assert seconds == 3600
        assert request.call_count == 1
        assert destination.read_bytes() == b"existing PDF"

    sleep = Mock(side_effect=wait)
    monkeypatch.setattr(INGEST_MITPRESS.time, "sleep", sleep)
    monkeypatch.setattr(
        INGEST_MITPRESS, "maybe_remove_mitpress_watermark", Mock(return_value=1)
    )
    monkeypatch.setattr(
        INGEST_MITPRESS, "find_mitpress_watermark_pages", Mock(return_value=[])
    )

    ok, _ = INGEST_MITPRESS.maybe_download_pdf(
        "10.1162/tacl.a.785", destination, dry_run=False
    )

    assert ok
    assert request.call_count == 2
    sleep.assert_called_once_with(3600)
    assert destination.read_bytes() == b"new PDF"
    assert list(tmp_path.iterdir()) == [destination]


def test_maybe_download_pdf_retry_after_remains_bounded(tmp_path, monkeypatch):
    destination = tmp_path / "paper.pdf"
    destination.write_bytes(b"existing PDF")
    blocked = MagicMock(
        status_code=429,
        url="https://direct.mit.edu/crawlprevention/governor",
        headers={"Retry-After": "3600"},
    )
    blocked.__enter__.return_value = blocked
    request = Mock(return_value=blocked)
    monkeypatch.setattr(INGEST_MITPRESS.requests, "get", request)
    sleep = Mock()
    monkeypatch.setattr(INGEST_MITPRESS.time, "sleep", sleep)

    ok, _ = INGEST_MITPRESS.maybe_download_pdf(
        "10.1162/tacl.a.785", destination, dry_run=False
    )

    assert not ok
    assert request.call_count == INGEST_MITPRESS.PDF_DOWNLOAD_RETRIES
    assert sleep.call_count == INGEST_MITPRESS.PDF_DOWNLOAD_RETRIES - 1
    assert all(call.args == (3600,) for call in sleep.call_args_list)
    assert destination.read_bytes() == b"existing PDF"


@pytest.mark.parametrize("status", [429, 503])
@pytest.mark.parametrize("date_header", [False, True])
def test_crossref_request_json_honors_retry_after(monkeypatch, status, date_header):
    now = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)
    header = (
        format_datetime(now + timedelta(seconds=120), usegmt=True)
        if date_header
        else "120"
    )
    response = Mock(
        status_code=status,
        headers={"Retry-After": header},
        url=INGEST_MITPRESS.CROSSREF_API,
    )
    error = INGEST_MITPRESS.requests.HTTPError(f"HTTP {status}", response=response)
    success = Mock()
    success.json.return_value = {"message": {"items": []}}
    session = Mock()
    session.get.side_effect = [error, success]
    sleep = Mock()
    monkeypatch.setattr(INGEST_MITPRESS.time, "sleep", sleep)
    monkeypatch.setattr(INGEST_MITPRESS.time, "time", lambda: now.timestamp())

    payload = INGEST_MITPRESS.crossref_request_json(session, {})

    assert payload == {"message": {"items": []}}
    assert session.get.call_count == 2
    sleep.assert_called_once_with(120)


def test_crossref_request_json_invalid_retry_after_uses_backoff(monkeypatch, caplog):
    response = Mock(
        headers={"Retry-After": "invalid"},
        url=INGEST_MITPRESS.CROSSREF_API,
    )
    error = INGEST_MITPRESS.requests.HTTPError("HTTP 503", response=response)
    success = Mock()
    success.json.return_value = {"message": {}}
    session = Mock()
    session.get.side_effect = [error, success]
    sleep = Mock()
    monkeypatch.setattr(INGEST_MITPRESS.time, "sleep", sleep)

    assert INGEST_MITPRESS.crossref_request_json(session, {}) == {"message": {}}
    sleep.assert_called_once_with(2)
    assert "Invalid Retry-After" in caplog.text


def test_maybe_download_pdf_retries_transient_error_without_overwriting(
    tmp_path, monkeypatch
):
    destination = tmp_path / "paper.pdf"
    destination.write_bytes(b"existing PDF")
    staged_paths = []

    def download(_url, path):
        staged = Path(path)
        staged_paths.append(staged)
        assert destination.read_bytes() == b"existing PDF"
        staged.write_bytes(b"new PDF")
        if len(staged_paths) == 1:
            raise INGEST_MITPRESS.requests.ConnectionError("Connection interrupted")

    monkeypatch.setattr(INGEST_MITPRESS, "retrieve_url", download)
    monkeypatch.setattr(
        INGEST_MITPRESS, "maybe_remove_mitpress_watermark", Mock(return_value=1)
    )
    monkeypatch.setattr(
        INGEST_MITPRESS, "find_mitpress_watermark_pages", Mock(return_value=[])
    )
    sleep = Mock()
    monkeypatch.setattr(INGEST_MITPRESS.time, "sleep", sleep)

    ok, _ = INGEST_MITPRESS.maybe_download_pdf(
        "10.1162/tacl.a.785", destination, dry_run=False
    )

    assert ok
    assert len(staged_paths) == 2
    assert all(path != destination and not path.exists() for path in staged_paths)
    sleep.assert_called_once_with(INGEST_MITPRESS.PDF_DOWNLOAD_RETRY_BASE_DELAY_SEC)
    assert destination.read_bytes() == b"new PDF"
    assert destination.stat().st_mode & 0o777 == INGEST_MITPRESS.PDF_FILE_MODE
    assert list(tmp_path.iterdir()) == [destination]


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
        people=SimpleNamespace(by_name={}, values=lambda: iter(())),
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

    assert papers[0]["doi"] == "10.1162/tacl.x.779"
    assert "Crossref identifies DOI 10.1162/tacl.x.779" in caplog.text
    assert "as a correction/erratum for" in caplog.text
    assert '"Example paper" (DOI 10.1162/tacl.a.742)' in caplog.text
    assert "not automatically suppressed" in caplog.text


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
