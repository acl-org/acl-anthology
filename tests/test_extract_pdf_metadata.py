import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from acl_anthology.files import PDFReference


SCRIPT_PATH = Path(__file__).parents[1] / "bin" / "extract_pdf_metadata.py"
SPEC = importlib.util.spec_from_file_location("extract_pdf_metadata", SCRIPT_PATH)
assert SPEC and SPEC.loader
extract_pdf_metadata = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = extract_pdf_metadata
SPEC.loader.exec_module(extract_pdf_metadata)


TEI = b"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="en">
  <teiHeader>
    <encodingDesc>
      <appInfo><application ident="GROBID" version="0.9.0"/></appInfo>
    </encodingDesc>
    <fileDesc>
      <titleStmt><title type="main">A Useful Paper</title></titleStmt>
      <publicationStmt>
        <availability><licence>CC BY 4.0</licence></availability>
      </publicationStmt>
      <sourceDesc>
        <biblStruct type="article">
          <analytic>
            <title level="a" type="main">A Useful Paper</title>
            <author role="corresp">
              <persName>
                <forename type="first">Ada</forename>
                <forename type="middle">M.</forename>
                <surname>Lovelace</surname>
              </persName>
              <idno type="ORCID">0000-0001-2345-6789</idno>
              <email>ada@example.org</email>
              <affiliation key="aff0">
                <marker>1</marker>
                <orgName type="department">Computing</orgName>
                <orgName type="institution" key="https://ror.org/example">Analytical Engine Institute</orgName>
                <address>
                  <settlement>London</settlement>
                  <country key="GB">United Kingdom</country>
                </address>
                <note type="raw_affiliation">Computing, Analytical Engine Institute, London</note>
              </affiliation>
            </author>
            <author>
              <persName><forename type="first">Charles</forename><surname>Babbage</surname></persName>
              <affiliation ref="#aff0"/>
            </author>
            <idno type="DOI">10.1000/example</idno>
          </analytic>
          <monogr>
            <title level="j">Journal of Useful Results</title>
            <imprint><publisher>Example Press</publisher><date type="published" when="2026-07-18"/></imprint>
          </monogr>
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <abstract><p>This is the abstract.</p></abstract>
      <textClass><keywords><term>metadata</term><term>affiliations</term></keywords></textClass>
      <langUsage><language ident="en">English</language></langUsage>
    </profileDesc>
  </teiHeader>
</TEI>
"""


def fake_paper(collection_id, full_id, pdf_name):
    return SimpleNamespace(
        collection_id=collection_id,
        full_id=full_id,
        full_id_tuple=(collection_id, "main", "1"),
        pdf=PDFReference(pdf_name, "abcdef12"),
    )


def test_parse_grobid_tei_preserves_author_affiliation_links_and_header_metadata():
    result = extract_pdf_metadata.parse_grobid_tei(TEI)

    assert result["title"] == "A Useful Paper"
    assert result["abstract"] == "This is the abstract."
    assert result["keywords"] == ["metadata", "affiliations"]
    assert result["document_type"] == "article"
    assert result["grobid_application"] == {"ident": "GROBID", "version": "0.9.0"}
    assert result["authors"][0] == {
        "index": 0,
        "name": "Ada M. Lovelace",
        "forenames": [
            {"text": "Ada", "type": "first"},
            {"text": "M.", "type": "middle"},
        ],
        "surnames": ["Lovelace"],
        "identifiers": [{"text": "0000-0001-2345-6789", "attributes": {"type": "ORCID"}}],
        "emails": ["ada@example.org"],
        "affiliation_ids": ["aff0"],
        "attributes": {"role": "corresp"},
    }
    assert result["authors"][1]["affiliation_ids"] == ["aff0"]
    assert len(result["affiliations"]) == 1
    affiliation = result["affiliations"][0]
    assert affiliation["id"] == "aff0"
    assert affiliation["raw"] == "Computing, Analytical Engine Institute, London"
    assert affiliation["organizations"][1] == {
        "name": "Analytical Engine Institute",
        "type": "institution",
        "key": "https://ror.org/example",
    }
    assert affiliation["address"]["country"] == {
        "text": "United Kingdom",
        "key": "GB",
    }
    assert result["identifiers"] == [
        {"text": "10.1000/example", "attributes": {"type": "DOI"}}
    ]
    assert result["journal_titles"][0]["text"] == "Journal of Useful Results"


def test_canonical_pdf_path_handles_modern_and_legacy_layouts(tmp_path):
    modern = fake_paper("2026.acl", "2026.acl-main.1", "2026.acl-main.1")
    legacy = fake_paper("W18", "W18-0001", "W18-0001")

    assert extract_pdf_metadata.canonical_pdf_path(tmp_path, modern) == (
        tmp_path / "acl" / "2026.acl-main.1.pdf"
    )
    assert extract_pdf_metadata.canonical_pdf_path(tmp_path, legacy) == (
        tmp_path / "W" / "W18" / "W18-0001.pdf"
    )


def test_cached_result_requires_matching_pdf_schema_options_and_tei(tmp_path):
    source = {"reference": "2026.acl-main.1", "checksum": "abcdef12"}
    result = {
        "schema_version": extract_pdf_metadata.SCHEMA_VERSION,
        "status": "success",
        "source": dict(source),
        "extractor": {"options": extract_pdf_metadata.GROBID_REQUEST_OPTIONS},
    }
    tei_path = tmp_path / "paper.tei.xml"
    tei_path.write_bytes(TEI)

    assert extract_pdf_metadata.cached_result_is_current(
        result, source, save_tei=True, tei_path=tei_path
    )
    assert not extract_pdf_metadata.cached_result_is_current(
        result,
        {**source, "checksum": "changed"},
        save_tei=True,
        tei_path=tei_path,
    )
    tei_path.unlink()
    assert not extract_pdf_metadata.cached_result_is_current(
        result, source, save_tei=True, tei_path=tei_path
    )
    assert extract_pdf_metadata.cached_result_is_current(
        result, source, save_tei=False, tei_path=tei_path
    )


def test_cached_tei_requires_matching_pdf_and_request_options(tmp_path):
    source = {"reference": "2026.acl-main.1", "checksum": "abcdef12"}
    result = {
        "schema_version": 0,
        "status": "success",
        "source": dict(source),
        "extractor": {"options": extract_pdf_metadata.GROBID_REQUEST_OPTIONS},
    }
    tei_path = tmp_path / "paper.tei.xml"
    tei_path.write_bytes(TEI)

    assert extract_pdf_metadata.cached_tei_is_current(result, source, tei_path)
    assert not extract_pdf_metadata.cached_tei_is_current(
        result, {**source, "checksum": "changed"}, tei_path
    )
    result["extractor"]["options"] = {"consolidateHeader": "1"}
    assert not extract_pdf_metadata.cached_tei_is_current(result, source, tei_path)


def test_select_papers_unions_years_ids_and_events_without_duplicates():
    paper_2025 = SimpleNamespace(full_id="2025.test-main.1", year="2025")
    paper_2026 = SimpleNamespace(full_id="2026.test-main.1", year="2026")
    workshop_2026 = SimpleNamespace(full_id="2026.workshop-1.1", year="2026")
    main_volume = SimpleNamespace(
        full_id_tuple=("2026.test", "main", None),
        papers=lambda: iter([paper_2026]),
    )
    workshop_volume = SimpleNamespace(
        full_id_tuple=("2026.workshop", "1", None),
        papers=lambda: iter([workshop_2026]),
    )
    collection = SimpleNamespace(volumes=lambda: iter([main_volume]))
    event = SimpleNamespace(
        collection=collection,
        volumes=lambda: iter([main_volume, workshop_volume]),
    )
    all_papers = [paper_2025, paper_2026, workshop_2026]
    anthology = SimpleNamespace(
        papers=lambda anthology_id=None: iter(
            all_papers
            if anthology_id is None
            else {"2025.test-main.1": [paper_2025]}[anthology_id]
        ),
        get_event=lambda anthology_id: (event if anthology_id == "test-2026" else None),
        get=lambda anthology_id: (
            paper_2025 if anthology_id == "2025.test-main.1" else None
        ),
    )

    selected = extract_pdf_metadata.select_papers(
        anthology,
        ["2026", "2025.test-main.1", "test-2026"],
    )

    assert [paper.full_id for paper in selected] == [
        "2026.test-main.1",
        "2026.workshop-1.1",
        "2025.test-main.1",
    ]


def test_select_papers_rejects_unknown_id_before_returning_work():
    anthology = SimpleNamespace(
        papers=lambda anthology_id=None: iter(()),
        get_event=lambda anthology_id: None,
        get=lambda anthology_id: None,
    )

    try:
        extract_pdf_metadata.select_papers(anthology, ["unknown-2026"])
    except ValueError as exception:
        assert "unknown-2026" in str(exception)
    else:
        raise AssertionError("Unknown selection should fail")


def test_select_papers_reports_malformed_publication_id_as_unknown_selector():
    def reject_malformed_id(anthology_id):
        raise ValueError(f"could not parse {anthology_id}")

    anthology = SimpleNamespace(
        papers=lambda anthology_id=None: iter(()),
        get_event=lambda anthology_id: None,
        get=reject_malformed_id,
    )

    try:
        extract_pdf_metadata.select_papers(anthology, ["definitely-not-an-anthology-id"])
    except ValueError as exception:
        assert str(exception) == (
            "Anthology ID or event 'definitely-not-an-anthology-id' was not found"
        )
    else:
        raise AssertionError("Malformed selection should fail clearly")


def test_parser_requires_positional_selector_and_infers_no_option_domain():
    parser = extract_pdf_metadata.build_parser()

    args = parser.parse_intermixed_args(["2010", "-j", "4", "P10-1001", "acl-2010"])

    assert args.selectors == ["2010", "P10-1001", "acl-2010"]
    assert args.jobs == 4


class FakeResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.content = content
        self.text = content.decode()


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def post(self, *args, **kwargs):
        self.calls += 1
        return next(self.responses)


def test_request_grobid_retries_busy_service(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    session = FakeSession([FakeResponse(503), FakeResponse(200, TEI)])
    waits = []

    response = extract_pdf_metadata.request_grobid(
        pdf,
        "http://grobid:8070",
        timeout=30,
        retries=2,
        session=session,
        sleep=waits.append,
    )

    assert response.status_code == 200
    assert session.calls == 2
    assert waits == [2]


def test_process_job_removes_downloaded_pdf_but_keeps_cache(tmp_path, monkeypatch):
    class DownloadablePDF:
        def download(self, path, timeout):
            Path(path).write_bytes(b"%PDF-1.4 downloaded")

    downloaded_pdf = tmp_path / "temporary" / "paper.pdf"
    json_path = tmp_path / "cache" / "paper.json"
    tei_path = tmp_path / "cache" / "paper.tei.xml"
    job = extract_pdf_metadata.PaperJob(
        paper_id="2026.test-main.1",
        pdf=DownloadablePDF(),
        pdf_path=downloaded_pdf,
        json_path=json_path,
        tei_path=tei_path,
        anthology_metadata={"paper_id": "2026.test-main.1"},
        source_metadata={"reference": "2026.test-main.1", "checksum": "abc"},
        action="request",
        temporary_pdf=True,
        save_tei=True,
        grobid_url="http://grobid:8070",
        grobid_version="0.9.0",
        timeout=30,
        retries=0,
    )
    monkeypatch.setattr(
        extract_pdf_metadata,
        "request_grobid",
        lambda *args, **kwargs: FakeResponse(200, TEI),
    )

    result = extract_pdf_metadata.process_job(job)

    assert result.status == "success"
    assert not downloaded_pdf.exists()
    assert json_path.is_file()
    assert tei_path.read_bytes() == TEI


def test_process_job_without_tei_removes_previous_raw_response(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 local")
    json_path = tmp_path / "cache" / "paper.json"
    tei_path = tmp_path / "cache" / "paper.tei.xml"
    tei_path.parent.mkdir(parents=True)
    tei_path.write_bytes(b"old TEI")
    job = extract_pdf_metadata.PaperJob(
        paper_id="2026.test-main.1",
        pdf=PDFReference("2026.test-main.1", "abc"),
        pdf_path=pdf_path,
        json_path=json_path,
        tei_path=tei_path,
        anthology_metadata={"paper_id": "2026.test-main.1"},
        source_metadata={"reference": "2026.test-main.1", "checksum": "abc"},
        action="request",
        temporary_pdf=False,
        save_tei=False,
        grobid_url="http://grobid:8070",
        grobid_version="0.9.0",
        timeout=30,
        retries=0,
    )
    monkeypatch.setattr(
        extract_pdf_metadata,
        "request_grobid",
        lambda *args, **kwargs: FakeResponse(200, TEI),
    )

    result = extract_pdf_metadata.process_job(job)

    assert result.status == "success"
    assert json_path.is_file()
    assert not tei_path.exists()


def test_transient_request_removes_previous_completion_marker(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 local")
    json_path = tmp_path / "cache" / "paper.json"
    json_path.parent.mkdir(parents=True)
    json_path.write_text('{"status": "success"}\n')
    job = extract_pdf_metadata.PaperJob(
        paper_id="2026.test-main.1",
        pdf=PDFReference("2026.test-main.1", "abc"),
        pdf_path=pdf_path,
        json_path=json_path,
        tei_path=tmp_path / "cache" / "paper.tei.xml",
        anthology_metadata={"paper_id": "2026.test-main.1"},
        source_metadata={"reference": "2026.test-main.1", "checksum": "abc"},
        action="request",
        temporary_pdf=False,
        save_tei=True,
        grobid_url="http://grobid:8070",
        grobid_version="0.9.0",
        timeout=30,
        retries=0,
    )

    def fail_request(*args, **kwargs):
        raise extract_pdf_metadata.requests.ConnectionError("service unavailable")

    monkeypatch.setattr(extract_pdf_metadata, "request_grobid", fail_request)

    result = extract_pdf_metadata.process_job(job)

    assert result.status == "transient-error"
    assert not json_path.exists()
