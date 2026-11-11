"""Tests for bin/add_dois.py."""

from datetime import datetime, timezone
from io import StringIO
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import shutil

import pytest
import requests
from rich.console import Console
from rich.logging import RichHandler

from bin.generate_crossref_doi_metadata import classify_input, DOI_PREFIX
from bin.add_dois import (
    add_doi_to_item,
    main,
    process_volume,
    retry_delay,
    test_url_code as check_url,
)

from acl_anthology import Anthology

DATADIR = Path(__file__).resolve().parent.parent / "data"


# -------------------------------------------------------------------
# classify_input tests (same logic as generate_crossref_doi_metadata)
# -------------------------------------------------------------------


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("2024.emnlp-main", ("volume", "2024.emnlp-main")),
        ("W10-17", ("volume", "W10-17")),
        ("naacl-2012", ("event", "naacl-2012")),
    ],
)
def test_classify_input(identifier, expected):
    assert classify_input(identifier) == expected


def test_classify_input_invalid():
    with pytest.raises(SystemExit):
        classify_input("not-valid-at-all-123")


# -------------------------------------------------------------------
# add_doi_to_item tests (mocked HTTP)
# -------------------------------------------------------------------


def test_add_doi_skips_existing():
    """If item already has a DOI and force=False, it should skip."""
    item = SimpleNamespace(doi="10.18653/v1/existing")
    result = add_doi_to_item(item, "W10-1701", force=False)
    assert result is False
    assert item.doi == "10.18653/v1/existing"


def test_add_doi_force_overwrites():
    """If item already has a DOI but force=True and URL resolves, overwrite."""
    item = SimpleNamespace(doi="10.18653/v1/old")
    mock_response = MagicMock(status_code=200)
    with patch("bin.add_dois.test_url_code", return_value=mock_response):
        result = add_doi_to_item(item, "W10-1701", force=True)
    assert result is True
    assert item.doi == f"{DOI_PREFIX}W10-1701"


def test_add_doi_success():
    """If item has no DOI and URL resolves, add it."""
    item = SimpleNamespace(doi=None)
    mock_response = MagicMock(status_code=200)
    with patch("bin.add_dois.test_url_code", return_value=mock_response):
        result = add_doi_to_item(item, "W10-1701")
    assert result is True
    assert item.doi == f"{DOI_PREFIX}W10-1701"


@pytest.mark.parametrize(
    "prefix, expected",
    [
        ("v1/", "10.18653/v1/W10-1701"),
        ("10.18653/v1/", "10.18653/v1/W10-1701"),
        ("10.1234/custom/", "10.1234/custom/W10-1701"),
        ("", "10.18653/W10-1701"),
    ],
)
def test_add_doi_prefix(prefix, expected):
    item = SimpleNamespace(doi=None)
    with patch(
        "bin.add_dois.test_url_code", return_value=MagicMock(status_code=200)
    ) as check:
        assert add_doi_to_item(item, "W10-1701", doi_prefix=prefix) is True
    check.assert_called_once_with(f"https://doi.org/{expected}")
    assert item.doi == expected


def test_add_doi_404():
    """If DOI URL returns 404, don't add."""
    item = SimpleNamespace(doi=None)
    mock_response = requests.Response()
    mock_response.status_code = 404
    with (
        patch("bin.add_dois.test_url_code", return_value=mock_response),
        patch("bin.add_dois.sleep"),
    ):
        result = add_doi_to_item(item, "W10-1701")
    assert result is False
    assert item.doi is None


def test_checks_resolver_without_following_redirects():
    with patch("bin.add_dois.requests.head") as head:
        assert check_url("https://doi.org/10.18653/W10-1701") is head.return_value
    head.assert_called_once_with(
        "https://doi.org/10.18653/W10-1701",
        headers={"user-agent": "acl-anthology/0.0.1"},
        allow_redirects=False,
        timeout=30,
    )


@pytest.mark.parametrize("status_code", [301, 302, 303, 307, 308])
def test_add_doi_accepts_resolver_redirect(status_code):
    """A registered DOI need not depend on the landing page's availability."""
    item = SimpleNamespace(doi=None)
    response = requests.Response()
    response.status_code = status_code
    response.headers["Location"] = "https://aclanthology.org/W10-1701/"
    with patch("bin.add_dois.test_url_code", return_value=response) as check:
        assert add_doi_to_item(item, "W10-1701") is True
    assert item.doi == f"{DOI_PREFIX}W10-1701"
    check.assert_called_once()


@pytest.mark.parametrize(
    "failure",
    [
        requests.Timeout("resolver timed out"),
        requests.ConnectionError("connection reset"),
        404,
        503,
        429,
    ],
)
def test_add_doi_retries_with_backoff(failure):
    item = SimpleNamespace(doi=None)
    if isinstance(failure, int):
        response = requests.Response()
        response.status_code = failure
        failure = response
    success = MagicMock(status_code=200)
    with (
        patch("bin.add_dois.test_url_code", side_effect=[failure, failure, success]),
        patch("bin.add_dois.sleep") as sleep,
    ):
        assert add_doi_to_item(item, "W10-1701") is True
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]
    assert item.doi == f"{DOI_PREFIX}W10-1701"


def test_add_doi_records_exhausted_failure():
    item = SimpleNamespace(doi=None)
    failures = {}
    with (
        patch(
            "bin.add_dois.test_url_code",
            side_effect=requests.Timeout("resolver timed out"),
        ) as check,
        patch("bin.add_dois.sleep") as sleep,
    ):
        assert add_doi_to_item(item, "W10-1701", failures=failures) is False
    assert check.call_count == 5
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2, 4, 8]
    assert failures == {f"https://doi.org/{DOI_PREFIX}W10-1701": "resolver timed out"}
    assert item.doi is None


@pytest.mark.parametrize(
    "header, expected", [(None, 2), ("0", 2), ("12", 12), ("bad", 2)]
)
def test_retry_delay_handles_missing_or_invalid_headers(header, expected, caplog):
    response = requests.Response()
    if header is not None:
        response.headers["Retry-After"] = header
    assert retry_delay(response, attempt=1) == expected
    if header == "bad":
        assert "Invalid Retry-After" in caplog.text


def test_retry_delay_handles_http_date():
    response = requests.Response()
    response.headers["Retry-After"] = "Mon, 02 Nov 2026 16:00:10 GMT"
    with patch("bin.add_dois.datetime") as clock:
        clock.now.return_value = datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc)
        assert retry_delay(response, attempt=0) == 10
        clock.now.return_value = datetime(2026, 11, 2, 16, 0, 20, tzinfo=timezone.utc)
        assert retry_delay(response, attempt=0) == 1


def test_add_doi_rejects_redirect_without_location():
    item = SimpleNamespace(doi=None)
    failures = {}
    response = requests.Response()
    response.status_code = 302
    with (
        patch("bin.add_dois.test_url_code", return_value=response),
        patch("bin.add_dois.sleep"),
    ):
        assert add_doi_to_item(item, "W10-1701", failures=failures) is False
    assert item.doi is None
    assert "redirect without a Location header" in next(iter(failures.values()))


def test_add_doi_failed_force_keeps_existing_doi():
    item = SimpleNamespace(doi="10.18653/existing")
    failures = {}
    with (
        patch("bin.add_dois.test_url_code", side_effect=requests.Timeout("timed out")),
        patch("bin.add_dois.sleep"),
    ):
        assert add_doi_to_item(item, "W10-1701", force=True, failures=failures) is False
    assert item.doi == "10.18653/existing"
    assert failures


def test_add_doi_does_not_hide_programming_errors():
    item = SimpleNamespace(doi=None)
    with patch("bin.add_dois.test_url_code", side_effect=ValueError("bug")):
        with pytest.raises(ValueError, match="bug"):
            add_doi_to_item(item, "W10-1701")


def test_add_doi_429_then_success():
    """On 429, retry after pause; succeed on second attempt."""
    item = SimpleNamespace(doi=None)
    resp_429 = MagicMock(status_code=429, headers={"Retry-After": "0"})
    resp_200 = MagicMock(status_code=200)
    with patch("bin.add_dois.test_url_code", side_effect=[resp_429, resp_200]):
        with patch("bin.add_dois.sleep"):
            result = add_doi_to_item(item, "W10-1701")
    assert result is True
    assert item.doi == f"{DOI_PREFIX}W10-1701"


def test_main_reports_failures_after_all_volumes(caplog):
    volumes = {}
    for volume_id in ["W10-17", "W10-18"]:
        volumes[volume_id] = SimpleNamespace(
            doi=None,
            title=volume_id,
            papers=lambda: [],
            parent=SimpleNamespace(save=MagicMock(), id="W10"),
        )
    anthology = SimpleNamespace(get_volume=volumes.get)
    args = SimpleNamespace(identifiers=list(volumes), prefix=DOI_PREFIX, force=False)
    missing = requests.Response()
    missing.status_code = 404
    caplog.set_level("INFO", logger="bin.add_dois")
    with (
        patch("bin.add_dois.Anthology.from_within_repo", return_value=anthology),
        patch(
            "bin.add_dois.test_url_code",
            side_effect=[missing] * 5 + [MagicMock(status_code=200)],
        ),
        patch("bin.add_dois.sleep"),
    ):
        assert main(args) == 1

    assert volumes["W10-17"].doi is None
    assert volumes["W10-18"].doi == f"{DOI_PREFIX}W10-18"
    for volume in volumes.values():
        volume.parent.save.assert_called_once()
    summary, failure = caplog.records[-2:]
    assert "1 DOI(s) failed" in summary.message
    assert summary.markup is True
    assert "[bold red]" in summary.message
    assert f"https://doi.org/{DOI_PREFIX}W10-17" in failure.message
    assert "HTTP 404" in failure.message


def test_main_failure_summary_is_red():
    stream = StringIO()
    handler = RichHandler(
        console=Console(file=stream, force_terminal=True, color_system="standard"),
        show_time=False,
        show_level=False,
        show_path=False,
    )
    logger = logging.getLogger("bin.add_dois")
    logger.addHandler(handler)

    def fail_volume(*args, failures, **kwargs):
        failures["https://doi.org/10.18653/W10-17"] = "HTTP 503"
        return 0

    args = SimpleNamespace(identifiers=["W10-17"], prefix=DOI_PREFIX, force=False)
    try:
        with (
            patch("bin.add_dois.Anthology.from_within_repo"),
            patch("bin.add_dois.process_volume", side_effect=fail_volume),
        ):
            assert main(args) == 1
    finally:
        logger.removeHandler(handler)
        handler.close()
    assert "\x1b[1;31m1 DOI(s) failed:" in stream.getvalue()
    assert "[bold red]" not in stream.getvalue()


def test_main_existing_dois_are_not_failures(caplog):
    volume = SimpleNamespace(
        doi="10.18653/existing",
        title="Existing",
        papers=lambda: [],
        parent=SimpleNamespace(save=MagicMock(), id="W10"),
    )
    anthology = SimpleNamespace(get_volume=lambda _: volume)
    args = SimpleNamespace(identifiers=["W10-17"], prefix=DOI_PREFIX, force=False)
    caplog.set_level("INFO", logger="bin.add_dois")
    with (
        patch("bin.add_dois.Anthology.from_within_repo", return_value=anthology),
        patch("bin.add_dois.test_url_code") as check,
    ):
        assert main(args) == 0
    check.assert_not_called()
    assert "0 added, 0 failed" in caplog.records[-1].message


# -------------------------------------------------------------------
# process_volume integration test (mocked HTTP, temp data dir)
# -------------------------------------------------------------------


@pytest.fixture
def temp_anthology(tmp_path):
    """Create a temporary anthology with a copy of W10.xml for write testing."""
    data_copy = tmp_path / "data"
    # Copy just the needed XML and JSON files
    shutil.copytree(DATADIR / "xml", data_copy / "xml")
    shutil.copytree(DATADIR / "json", data_copy / "json")
    return Anthology(datadir=data_copy)


@pytest.mark.parametrize("prefix", [DOI_PREFIX, "v1/"])
def test_process_volume_adds_dois(temp_anthology, prefix):
    """process_volume should set DOIs on volume and papers when URLs resolve."""
    mock_response = MagicMock(status_code=200)
    with (
        patch("bin.add_dois.test_url_code", return_value=mock_response),
        patch("bin.add_dois.sleep"),
    ):
        num_added = process_volume(temp_anthology, "W10-17", doi_prefix=prefix)

    # W10-17 has 64 papers (including frontmatter) + 1 volume-level DOI = 65
    assert num_added == 65
    expected_prefix = DOI_PREFIX if prefix == DOI_PREFIX else f"{DOI_PREFIX}v1/"

    # Verify DOIs are set on the objects
    volume = temp_anthology.get_volume("W10-17")
    assert volume.doi == f"{expected_prefix}W10-17"
    for paper in volume.papers():
        assert paper.doi == f"{expected_prefix}{paper.full_id}"

    saved = Anthology(datadir=temp_anthology.datadir)
    assert saved.get_volume("W10-17").doi == f"{expected_prefix}W10-17"
    for paper in saved.get_volume("W10-17").papers():
        assert paper.doi == f"{expected_prefix}{paper.full_id}"


def test_process_volume_saves_successes_and_records_paper_failures(temp_anthology):
    volume = temp_anthology.get_volume("W10-17")
    papers = list(volume.papers())
    papers[0].doi = "10.18653/existing"
    failed_doi = f"{DOI_PREFIX}{papers[1].full_id}"
    failures = {}

    def check(url):
        response = requests.Response()
        response.status_code = 503 if url == f"https://doi.org/{failed_doi}" else 200
        return response

    with (
        patch("bin.add_dois.test_url_code", side_effect=check),
        patch("bin.add_dois.sleep"),
    ):
        assert process_volume(temp_anthology, "W10-17", failures=failures) == 63

    assert failures == {f"https://doi.org/{failed_doi}": "HTTP 503"}
    saved = Anthology(datadir=temp_anthology.datadir)
    saved_volume = saved.get_volume("W10-17")
    assert saved_volume.doi == f"{DOI_PREFIX}W10-17"
    saved_papers = list(saved_volume.papers())
    assert saved_papers[0].doi == "10.18653/existing"
    assert saved_papers[1].doi is None
    for paper in saved_papers[2:]:
        assert paper.doi == f"{DOI_PREFIX}{paper.full_id}"


def test_process_volume_nonexistent(temp_anthology):
    """process_volume should exit if volume doesn't exist."""
    with pytest.raises(SystemExit):
        process_volume(temp_anthology, "Z99-99")
