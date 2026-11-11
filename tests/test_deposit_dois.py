"""Tests for bin/deposit_dois.py."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from bin import deposit_dois  # noqa: E402
from bin.deposit_dois import (  # noqa: E402
    DepositError,
    count_dois,
    deposit,
    encode_multipart,
    fetch_result,
    get_credentials,
    parse_result,
)
from bin.generate_crossref_doi_metadata import generate_crossref_xml  # noqa: E402

from acl_anthology import Anthology  # noqa: E402

RESULT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<doi_batch_diagnostic status="completed" sp="cs3.crossref.org">
  <submission_id>1234</submission_id>
  <batch_id>1000000000</batch_id>
  <batch_data>
    <record_count>3</record_count>
    <success_count>2</success_count>
    <warning_count>0</warning_count>
    <failure_count>1</failure_count>
  </batch_data>
</doi_batch_diagnostic>
"""


def make_response(body):
    response = MagicMock()
    response.read.return_value = body
    response.__enter__.return_value = response
    return response


def make_args(**kwargs):
    defaults = dict(
        identifiers=["W10-17"],
        dry_run=False,
        test=False,
        yes=False,
        wait=False,
        timeout=0,
        poll_interval=0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.fixture(scope="module")
def anthology():
    return Anthology.from_within_repo()


def test_count_dois(anthology):
    xml_bytes = generate_crossref_xml(anthology, ["W10-17"], batch_id=1)
    assert count_dois(xml_bytes) == xml_bytes.count(b"<doi>")
    assert count_dois(xml_bytes) > 0


def test_encode_multipart():
    body, content_type = encode_multipart(
        {"operation": "doMDUpload"}, "fname", "batch.xml", b"<xml/>"
    )
    boundary = content_type.split("boundary=")[1]
    assert content_type.startswith("multipart/form-data")
    assert b'name="operation"\r\n\r\ndoMDUpload\r\n' in body
    assert b'name="fname"; filename="batch.xml"' in body
    assert b"<xml/>" in body
    assert body.endswith(f"--{boundary}--\r\n".encode())


def test_deposit_posts_credentials_and_file():
    response = make_response(b"<h2>SUCCESS</h2>")
    with patch.object(deposit_dois, "urlopen", return_value=response) as urlopen:
        deposit("https://test.crossref.org", "role", "secret", "b.xml", b"<x/>")
    request = urlopen.call_args.args[0]
    assert request.full_url == "https://test.crossref.org/servlet/deposit"
    assert request.get_method() == "POST"
    assert b'name="login_id"\r\n\r\nrole\r\n' in request.data
    assert b'name="login_passwd"\r\n\r\nsecret\r\n' in request.data
    assert b'filename="b.xml"' in request.data


def test_deposit_rejects_unexpected_response():
    response = make_response(b"<h2>FAILURE</h2><p>Bad credentials</p>")
    with patch.object(deposit_dois, "urlopen", return_value=response):
        with pytest.raises(DepositError, match="Bad credentials"):
            deposit("https://test.crossref.org", "role", "pw", "b.xml", b"<x/>")


def test_fetch_result_uses_file_name():
    response = make_response(RESULT_XML)
    with patch.object(deposit_dois, "urlopen", return_value=response) as urlopen:
        assert fetch_result("https://doi.crossref.org", "u", "p", "b.xml") == RESULT_XML
    query = parse_qs(urlparse(urlopen.call_args.args[0]).query)
    assert query == {
        "usr": ["u"],
        "pwd": ["p"],
        "file_name": ["b.xml"],
        "type": ["result"],
    }


def test_parse_result():
    status, counts = parse_result(RESULT_XML)
    assert status == "completed"
    assert counts == {
        "record_count": 3,
        "success_count": 2,
        "warning_count": 0,
        "failure_count": 1,
    }


def test_parse_result_pending():
    status, counts = parse_result(b'<doi_batch_diagnostic status="queued"/>')
    assert status == "queued"
    assert counts == {}


def test_parse_result_non_xml():
    assert parse_result(b"not yet")[0] == "unknown_submission"


def test_get_credentials_from_environment(monkeypatch):
    monkeypatch.setenv("CROSSREF_USERNAME", "me@example.org/role")
    monkeypatch.setenv("CROSSREF_PASSWORD", "secret")
    assert get_credentials() == ("me@example.org/role", "secret")


def test_get_credentials_prompts(monkeypatch):
    monkeypatch.delenv("CROSSREF_USERNAME", raising=False)
    monkeypatch.delenv("CROSSREF_PASSWORD", raising=False)
    monkeypatch.setattr("builtins.input", lambda _: "role")
    monkeypatch.setattr(deposit_dois.getpass, "getpass", lambda _: "secret")
    assert get_credentials() == ("role", "secret")


def test_main_dry_run_does_not_deposit():
    with patch.object(deposit_dois, "deposit") as mocked_deposit:
        deposit_dois.main(make_args(dry_run=True))
    mocked_deposit.assert_not_called()


def test_main_production_requires_confirmation(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with patch.object(deposit_dois, "deposit") as mocked_deposit:
        deposit_dois.main(make_args())
    mocked_deposit.assert_not_called()


def test_main_rejects_unknown_volume():
    with pytest.raises(DepositError, match="not found"):
        deposit_dois.main(make_args(identifiers=["2099.nonexistent-1"]))


def test_main_deposits_and_waits(monkeypatch):
    monkeypatch.setenv("CROSSREF_USERNAME", "role")
    monkeypatch.setenv("CROSSREF_PASSWORD", "secret")
    completed = b"""<doi_batch_diagnostic status="completed"><batch_data>
        <failure_count>0</failure_count></batch_data></doi_batch_diagnostic>"""
    with (
        patch.object(deposit_dois, "deposit") as mocked_deposit,
        patch.object(
            deposit_dois,
            "fetch_result",
            side_effect=[b'<doi_batch_diagnostic status="queued"/>', completed],
        ),
        patch.object(deposit_dois.time, "sleep"),
    ):
        deposit_dois.main(make_args(test=True, wait=True, timeout=60))
    host, username, password, filename, xml_bytes = mocked_deposit.call_args.args
    assert host == deposit_dois.TEST_HOST
    assert (username, password) == ("role", "secret")
    assert filename.startswith("anthology_") and filename.endswith(".xml")
    assert count_dois(xml_bytes) > 0


def test_main_reports_failures(monkeypatch):
    monkeypatch.setenv("CROSSREF_USERNAME", "role")
    monkeypatch.setenv("CROSSREF_PASSWORD", "secret")
    with (
        patch.object(deposit_dois, "deposit"),
        patch.object(deposit_dois, "fetch_result", return_value=RESULT_XML),
    ):
        with pytest.raises(DepositError, match="did not complete"):
            deposit_dois.main(make_args(yes=True, wait=True))
