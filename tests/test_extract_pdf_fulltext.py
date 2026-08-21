import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from acl_anthology.files import PDFReference


SCRIPT_PATH = Path(__file__).parents[1] / "bin" / "grobid" / "extract_pdf_fulltext.py"
SPEC = importlib.util.spec_from_file_location("extract_pdf_fulltext", SCRIPT_PATH)
assert SPEC and SPEC.loader
extract_pdf_fulltext = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = extract_pdf_fulltext
SPEC.loader.exec_module(extract_pdf_fulltext)


TEI = b"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="en">
  <teiHeader>
    <encodingDesc>
      <appInfo><application ident="GROBID" version="0.9.0"/></appInfo>
    </encodingDesc>
    <fileDesc>
      <titleStmt><title type="main">A Useful Paper</title></titleStmt>
      <sourceDesc>
        <biblStruct>
          <analytic>
            <title level="a" type="main">A Useful Paper</title>
            <author>
              <persName>
                <forename type="first">Ada</forename>
                <surname>Lovelace</surname>
              </persName>
              <idno type="ORCID">0000-0001-2345-6789</idno>
              <email>ada@example.org</email>
              <affiliation key="aff0">
                <orgName type="institution">Example University</orgName>
                <note type="raw_affiliation">Example University, Nowhere</note>
              </affiliation>
            </author>
            <author>
              <persName><surname>Babbage</surname></persName>
            </author>
          </analytic>
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <abstract>
        <div><p>We describe a useful thing.</p><p>It works well.</p></div>
      </abstract>
      <textClass><keywords><term>parsing</term><term>evaluation</term></keywords></textClass>
    </profileDesc>
  </teiHeader>
  <text xml:lang="en">
    <body>
      <div xmlns="http://www.tei-c.org/ns/1.0">
        <head n="1">Introduction</head>
        <p>Full text search needs   normalized text.</p>
        <p>Inline <ref type="bibr" target="#b0">(Babbage, 1837)</ref> citations are kept.</p>
      </div>
      <div xmlns="http://www.tei-c.org/ns/1.0">
        <head n="2">Method</head>
        <p>We use GROBID.</p>
      </div>
      <div xmlns="http://www.tei-c.org/ns/1.0">
        <head>Empty section</head>
      </div>
    </body>
    <back>
      <div type="acknowledgement">
        <div><head>Acknowledgements</head><p>Thanks to everyone.</p></div>
      </div>
      <div type="references">
        <listBibl>
          <biblStruct xml:id="b0">
            <analytic>
              <title level="a" type="main">On the Analytical Engine</title>
              <author><persName><surname>Babbage</surname></persName></author>
              <idno type="DOI">10.0000/example</idno>
            </analytic>
            <monogr>
              <title level="j">Journal of Engines</title>
              <imprint><date type="published" when="1837">1837</date></imprint>
            </monogr>
          </biblStruct>
        </listBibl>
      </div>
    </back>
  </text>
</TEI>
"""


def test_parse_fulltext_tei_header():
    parsed = extract_pdf_fulltext.parse_fulltext_tei(TEI)
    assert parsed["title"] == "A Useful Paper"
    assert parsed["abstract"] == "We describe a useful thing. It works well."
    assert parsed["keywords"] == ["parsing", "evaluation"]
    assert parsed["grobid_version"] == "0.9.0"


def test_parse_fulltext_tei_authors():
    authors = extract_pdf_fulltext.parse_fulltext_tei(TEI)["authors"]
    assert [author["name"] for author in authors] == ["Ada Lovelace", "Babbage"]
    assert authors[0]["affiliations"] == ["Example University, Nowhere"]
    assert authors[0]["orcid"] == "0000-0001-2345-6789"
    assert authors[0]["email"] == "ada@example.org"
    assert "affiliations" not in authors[1]


def test_parse_fulltext_tei_sections():
    parsed = extract_pdf_fulltext.parse_fulltext_tei(TEI)
    sections = parsed["sections"]
    assert [section["head"] for section in sections] == [
        "Introduction",
        "Method",
        "Empty section",
    ]
    assert sections[0]["n"] == "1"
    assert sections[0]["paragraphs"][0] == "Full text search needs normalized text."
    assert "(Babbage, 1837)" in sections[0]["paragraphs"][1]
    assert "paragraphs" not in sections[2]
    assert parsed["back_sections"][0]["paragraphs"] == ["Thanks to everyone."]


def test_parse_fulltext_tei_references_and_stats():
    parsed = extract_pdf_fulltext.parse_fulltext_tei(TEI)
    assert parsed["references"] == [
        {
            "title": "On the Analytical Engine",
            "authors": ["Babbage"],
            "venue": "Journal of Engines",
            "year": "1837",
            "doi": "10.0000/example",
        }
    ]
    assert parsed["stats"]["sections"] == 4
    assert parsed["stats"]["paragraphs"] == 4
    assert parsed["stats"]["references"] == 1
    assert parsed["stats"]["body_characters"] > 0


def test_parse_fulltext_tei_without_body():
    minimal = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0">
      <teiHeader><fileDesc><titleStmt><title type="main">Bare</title></titleStmt>
      </fileDesc></teiHeader><text><body/></text></TEI>"""
    parsed = extract_pdf_fulltext.parse_fulltext_tei(minimal)
    assert parsed["title"] == "Bare"
    assert "sections" not in parsed
    assert parsed["stats"]["sections"] == 0


def make_paper(collection_id, name, checksum="deadbeef"):
    return SimpleNamespace(
        full_id=f"{collection_id}.1",
        collection_id=collection_id,
        pdf=PDFReference(name=name, checksum=checksum),
    )


def test_canonical_pdf_path_new_style():
    paper = make_paper("2025.acl", "2025.acl-long.1")
    path = extract_pdf_fulltext.canonical_pdf_path(Path("/files/pdf"), paper)
    assert path == Path("/files/pdf/acl/2025.acl-long.1.pdf")


def test_canonical_pdf_path_old_style():
    paper = make_paper("P19", "P19-1001")
    path = extract_pdf_fulltext.canonical_pdf_path(Path("/files/pdf"), paper)
    assert path == Path("/files/pdf/P/P19/P19-1001.pdf")


def test_output_path_mirrors_new_style_tree():
    pdf_path = Path("/files/pdf/acl/2025.acl-long.1.pdf")
    roots = (Path("/files/pdf"), Path("/files/grobid"))
    path = extract_pdf_fulltext.output_path(pdf_path, *roots)
    assert path == Path("/files/grobid/acl/2025.acl-long.1.json")


def test_output_path_mirrors_old_style_tree():
    pdf_path = Path("/files/pdf/W/W00/W00-1323.pdf")
    roots = (Path("/files/pdf"), Path("/files/grobid"))
    path = extract_pdf_fulltext.output_path(pdf_path, *roots)
    assert path == Path("/files/grobid/W/W00/W00-1323.json")


def current_result(source):
    return {
        "schema_version": extract_pdf_fulltext.SCHEMA_VERSION,
        "status": "success",
        "source": source,
        "extractor": {"options": extract_pdf_fulltext.GROBID_REQUEST_OPTIONS},
    }


SOURCE = {"reference": "2025.acl-long.1", "checksum": "deadbeef", "size": 4096}


def test_result_is_current_accepts_matching_result():
    assert extract_pdf_fulltext.result_is_current(current_result(SOURCE), SOURCE)


def test_result_is_current_rejects_changed_pdf():
    for key, value in (("checksum", "cafebabe"), ("size", 8192)):
        result = current_result({**SOURCE, key: value})
        assert not extract_pdf_fulltext.result_is_current(result, SOURCE)


def test_result_is_current_rejects_old_schema_and_options():
    stale_schema = current_result(SOURCE) | {"schema_version": 0}
    assert not extract_pdf_fulltext.result_is_current(stale_schema, SOURCE)
    stale_options = current_result(SOURCE) | {"extractor": {"options": {}}}
    assert not extract_pdf_fulltext.result_is_current(stale_options, SOURCE)


def test_result_is_current_rejects_incomplete_status():
    result = current_result(SOURCE) | {"status": "transient-error"}
    assert not extract_pdf_fulltext.result_is_current(result, SOURCE)


def test_grobid_endpoint_uses_fulltext_service():
    endpoint = extract_pdf_fulltext.grobid_endpoint("http://localhost:8070/")
    assert endpoint == "http://localhost:8070/api/processFulltextDocument"


def test_parse_version_accepts_json_and_plain_text():
    assert extract_pdf_fulltext.parse_version('{"version":"0.9.0","revision":"x"}\n') == (
        "0.9.0"
    )
    assert extract_pdf_fulltext.parse_version("  0.8.1 ") == "0.8.1"
    assert extract_pdf_fulltext.parse_version("") == "unknown"
    assert extract_pdf_fulltext.parse_version('{"revision":"x"}') == '{"revision":"x"}'


def test_error_summary_includes_grobid_message():
    response = SimpleNamespace(status_code=500, text="[NO_BLOCKS]\n  no text found\n")
    summary = extract_pdf_fulltext.error_summary(response)
    assert summary == "HTTP 500: [NO_BLOCKS] no text found"
    assert extract_pdf_fulltext.error_summary(
        SimpleNamespace(status_code=400, text="")
    ) == ("HTTP 400")


def test_single_paper_requires_exactly_one_match():
    paper = make_paper("2025.acl", "2025.acl-long.1")
    assert extract_pdf_fulltext.single_paper([paper], ["2025.acl-long.1"]) == [paper]
    for papers in ([], [paper, paper]):
        with pytest.raises(ValueError, match="matching one paper"):
            extract_pdf_fulltext.single_paper(papers, ["2025.acl-long"])


def test_atomic_write_json_replaces_file(tmp_path):
    path = tmp_path / "nested" / "paper.json"
    extract_pdf_fulltext.atomic_write_json(path, {"status": "success"})
    extract_pdf_fulltext.atomic_write_json(path, {"status": "no-content"})
    assert extract_pdf_fulltext.load_json(path) == {"status": "no-content"}
    assert list(path.parent.iterdir()) == [path]


def test_atomic_write_json_is_world_readable(tmp_path):
    path = tmp_path / "paper.json"
    extract_pdf_fulltext.atomic_write_json(path, {"status": "success"})
    assert path.stat().st_mode & 0o777 == 0o644


def test_load_json_returns_none_for_broken_file(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    assert extract_pdf_fulltext.load_json(path) is None
    assert extract_pdf_fulltext.load_json(tmp_path / "absent.json") is None
