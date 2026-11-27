import csv
import importlib.util
import io
from http.client import IncompleteRead
import json
from pathlib import Path
import shutil
import sys
from urllib.error import HTTPError

import pytest


SCRIPTS = Path(__file__).parents[1] / ".github/skills/ingest-videos/scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = load_script("common")
server = load_script("server")
metadata = load_script("metadata")


def test_title_normalization_preserves_significant_digits():
    assert common.normalize("Caf\u00e9: LLM-2026") == common.normalize(
        "Cafe \u2014 llm 2026"
    )
    assert common.normalize("LLM-2025") != common.normalize("LLM-2026")


def test_sheet_rejects_duplicate_lectures_and_external_urls(tmp_path):
    path = tmp_path / "sheet.csv"
    fields = ["Title", "Paper number", "video", "Frontend URI"]
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for title in ("First", "Second"):
            writer.writerow(
                {
                    "Title": title,
                    "Paper number": title,
                    "video": "yes",
                    "Frontend URI": "https://underline.io/lecture/123-example",
                }
            )
    with pytest.raises(ValueError, match="Duplicate lecture"):
        common.sheet_records(path)
    path.write_text(path.read_text().replace("underline.io", "example.com"))
    with pytest.raises(ValueError, match="Invalid lecture URL"):
        common.sheet_records(path)


def test_hls_selects_highest_resolution_and_validates_complete_source(monkeypatch):
    master = (
        "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000,RESOLUTION=640x360\nsmall.m3u8\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=3000,RESOLUTION=1920x1080\nlarge.m3u8\n"
    )
    media = "#EXTM3U\n#EXTINF:2.5,\nchunk.ts\n#EXT-X-ENDLIST\n"
    monkeypatch.setattr(
        server,
        "fetch",
        lambda url, hosts: (master if url.endswith("master.m3u8") else media).encode(),
    )
    result = server.rendition("https://assets.underline.io/master.m3u8")
    assert result["height"] == 1080
    assert result["expected_duration"] == 2.5
    assert result["url"] == "https://assets.underline.io/large.m3u8"


@pytest.mark.parametrize(
    "media",
    [
        "#EXTM3U\n#EXTINF:2,\nchunk.ts\n",
        "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128\n#EXTINF:2,\nchunk.ts\n#EXT-X-ENDLIST\n",
        "#EXTM3U\n#EXTINF:2,\nfile:///etc/passwd\n#EXT-X-ENDLIST\n",
        "#EXTM3U\n#EXTINF:2,\nhttps://example.com/chunk.ts\n#EXT-X-ENDLIST\n",
    ],
)
def test_hls_rejects_live_encrypted_or_unapproved_segments(media, monkeypatch):
    master = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000,RESOLUTION=640x360\nmedia.m3u8\n"
    monkeypatch.setattr(
        server,
        "fetch",
        lambda url, hosts: (master if url.endswith("master.m3u8") else media).encode(),
    )
    with pytest.raises(ValueError):
        server.rendition("https://assets.underline.io/master.m3u8")


def test_catalog_rejects_another_lecture_and_does_not_use_related_videos(
    tmp_path, monkeypatch
):
    row = {"lecture_id": "123", "sheet_row": "2"}
    data = {
        "data": {
            "id": "456",
            "attributes": {
                "published": True,
                "package": "free",
                "playlist": "related.m3u8",
            },
        }
    }
    monkeypatch.setattr(
        server, "fetch", lambda *args, **kwargs: json.dumps(data).encode()
    )
    with pytest.raises(ValueError, match="another lecture"):
        server.catalog_record(row, tmp_path)


def recording(source, lecture_id="123"):
    return {
        "status": "verified",
        "lecture_id": lecture_id,
        "paper_id": "2026.test-1.1",
        "sheet": {"lecture_id": lecture_id},
        "publication_allowed": True,
        "source_path": str(source),
        "source_fingerprint": common.fingerprint(source),
        "sha256": common.digest(source),
        "existing_videos": [],
    }


def test_placement_never_overwrites_and_deduplicates_same_recording(tmp_path):
    report = tmp_path / "report"
    staging = tmp_path / "staging"
    videos = tmp_path / "videos"
    for path in (report, staging, videos, videos / "test"):
        path.mkdir()
    occupied = videos / "test/2026.test-1.1.mp4"
    occupied.write_bytes(b"older recording")
    first, second = staging / "123.mp4", staging / "456.mp4"
    first.write_bytes(b"new identical recording")
    second.write_bytes(first.read_bytes())
    rows = [recording(first), recording(second, "456")]
    for row in rows:
        common.write_json(
            report / "downloads" / (row["lecture_id"] + ".json"),
            {
                **row,
                "status": "downloaded",
            },
        )
    result = server.place({"records": rows}, report, videos, staging)
    assert occupied.read_bytes() == b"older recording"
    assert result[0]["reference_name"] == "2026.test-1.1.1.mp4"
    assert result[1]["destination_path"] == result[0]["destination_path"]
    assert result[1]["metadata_status"] == "reused-in-run"
    assert first.exists() and second.exists()
    rerun = server.place({"records": rows}, report, videos, staging)
    assert rerun == result


def test_placement_refuses_withheld_permission(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"recording")
    row = recording(source)
    row["existing_videos"] = [{"name": "2026.test-1.1.mp4", "permission": False}]
    with pytest.raises(ValueError, match="withheld"):
        server.place({"records": [row]}, tmp_path, tmp_path, tmp_path)


def test_placement_refuses_changed_verified_source(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"recording")
    row = recording(source)
    common.write_json(tmp_path / "downloads/123.json", {**row, "status": "downloaded"})
    source.write_bytes(b"modified")
    with pytest.raises(ValueError, match="source changed"):
        server.place({"records": [row]}, tmp_path, tmp_path, tmp_path)


def test_stale_sheet_link_uses_unique_exact_title_not_paper_number():
    papers = {
        "2026.test-1.1": {"title": "Other work"},
        "2026.test-1.2": {"title": "Correct work"},
    }
    sheet = {
        "sheet_paper_link": "https://aclanthology.org/2026.test-1.1/",
        "sheet_title": "Correct work",
    }
    provider = {"provider_title": "Correct work"}
    assert metadata.candidate_matches(
        sheet, provider, papers, {"correctwork": ["2026.test-1.2"]}
    ) == ["2026.test-1.2"]
    assert metadata.candidate_matches(
        sheet, provider, papers, {"correctwork": ["2026.test-1.2", "2026.test-1.3"]}
    ) == ["2026.test-1.2", "2026.test-1.3"]


def test_actual_frame_requires_full_title_and_full_author_together():
    paper = {"title": "Learning with Dataset 2026", "authors": ["First Last"]}
    assert metadata.frame_match("Learning with Dataset 2026\nFirst Last", paper)
    assert not metadata.frame_match("Learning with Dataset 2025\nFirst Last", paper)
    assert not metadata.frame_match("Learning with Dataset 2026\nUnrelated Author", paper)
    assert not metadata.frame_match("Learning with Dataset 2026\nFirst", paper)


def test_another_paper_in_a_frame_flags_review_not_automatic_reassignment(tmp_path):
    papers = {
        "2026.test-1.1": {
            "title": "A sufficiently long expected research title",
            "authors": ["First Last"],
            "existing_videos": [],
            "nonvideo_sha256": "expected",
        },
        "2026.test-1.2": {
            "title": "A sufficiently long cited research title",
            "authors": ["Other Author"],
            "existing_videos": [],
            "nonvideo_sha256": "other",
        },
    }
    sheet = tmp_path / "spreadsheet.csv"
    sheet.write_text("frozen input")
    common.write_json(
        tmp_path / "candidates.json",
        {
            "spreadsheet_sha256": common.digest(sheet),
            "papers": papers,
            "records": [{"lecture_id": "123", "candidate_id": "2026.test-1.1"}],
        },
    )
    common.write_json(
        tmp_path / "download-results.json",
        [
            {
                "sheet": {"lecture_id": "123"},
                "status": "downloaded",
                "audio_stream": True,
                "publication_allowed": True,
                "black_duration_ratio": 0.0,
                "frames": [{"path": "frames/123/0.jpg", "timestamp": 5}],
            }
        ],
    )
    ocr = tmp_path / "ocr.jsonl"
    ocr.write_text(
        json.dumps(
            {
                "path": str(tmp_path / "frames/123/0.jpg"),
                "observations": [
                    {
                        "text": papers["2026.test-1.1"]["title"]
                        + "\nFirst Last\n"
                        + papers["2026.test-1.2"]["title"]
                        + "\nOther Author"
                    }
                ],
            }
        )
        + "\n"
    )
    metadata.review(tmp_path, ocr, None)
    row = common.read_json(tmp_path / "reviewed.json")["records"][0]
    assert row["status"] == "needs-review"
    assert row["paper_id"] == "2026.test-1.1"
    assert row["alternate_ids"] == ["2026.test-1.2"]


def test_library_save_reload_preserves_other_metadata_and_video_order(
    tmp_path, monkeypatch
):
    from acl_anthology import Anthology
    from acl_anthology.files import VideoReference
    import subprocess

    repo = tmp_path / "repo"
    data = repo / "data"
    shutil.copytree(Path(__file__).parents[1] / "python/tests/data/anthology", data)
    anthology = Anthology(data, suppress_warnings=True)
    paper = anthology.get_paper("2022.facl-long.1")
    paper.videos = (VideoReference("https://example.org/old.mp4"),)
    anthology.save_all()
    baseline = metadata.nonvideo_digest(paper)
    report = tmp_path / "report"
    report.mkdir()
    common.write_json(
        report / "placements.json",
        [
            {
                "paper_id": paper.full_id,
                "status": "verified",
                "evidence": ["actual title slide"],
                "publication_allowed": True,
                "reference_name": "2022.facl-long.1.mp4",
                "nonvideo_sha256": baseline,
                "existing_videos": [
                    {"name": "https://example.org/old.mp4", "permission": True}
                ],
            }
        ],
    )
    monkeypatch.setattr(
        Anthology, "from_within_repo", lambda: Anthology(data, suppress_warnings=True)
    )
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: str(repo) + "\n"
    )
    metadata.apply(report, False)
    assert (
        len(Anthology(data, suppress_warnings=True).get_paper(paper.full_id).videos) == 1
    )
    metadata.apply(report, True)
    saved = Anthology(data, suppress_warnings=True).get_paper(paper.full_id)
    assert metadata.nonvideo_digest(saved) == baseline
    assert [video.name for video in saved.videos] == [
        "https://example.org/old.mp4",
        "2022.facl-long.1.mp4",
    ]
    assert (
        common.read_json(report / "metadata-validation.json")["repository_checks"][
            "status"
        ]
        == "pending"
    )
    validation_path = report / "metadata-validation.json"
    validation = common.read_json(validation_path)
    validation["repository_checks"]["status"] = "passed"
    common.write_json(validation_path, validation)
    placements = common.read_json(report / "placements.json")
    placements.append({**placements[0], "reference_name": "2022.facl-long.1.1.mp4"})
    common.write_json(report / "placements.json", placements)
    metadata.apply(report, True)
    continued = Anthology(data, suppress_warnings=True).get_paper(paper.full_id)
    assert [video.name for video in continued.videos] == [
        "https://example.org/old.mp4",
        "2022.facl-long.1.mp4",
        "2022.facl-long.1.1.mp4",
    ]
    assert metadata.nonvideo_digest(continued) == baseline
    unexpected = Anthology(data, suppress_warnings=True)
    unexpected.get_paper(paper.full_id).videos += (
        VideoReference("https://example.org/unapproved.mp4"),
    )
    unexpected.save_all()
    with pytest.raises(ValueError, match="Video metadata changed"):
        metadata.apply(report, True)


def test_local_hls_transport_downloads_and_reuses_verified_original_segments(
    tmp_path, monkeypatch
):
    report, staging = tmp_path / "report", tmp_path / "staging"
    report.mkdir()
    staging.mkdir()
    playlist = "#EXTM3U\n#EXTINF:2,\nchunk.ts\n#EXT-X-ENDLIST\n"
    original = b"original MPEG-TS packet bytes"
    requests = []

    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Length": str(len(original))}

        def geturl(self):
            return "https://assets.underline.io/chunk.ts"

    def fetch_segment(request, timeout):
        requests.append(request.full_url)
        return Response(original)

    monkeypatch.setattr(server, "fetch", lambda *args: playlist.encode())
    monkeypatch.setattr(server, "urlopen", fetch_segment)
    record = {
        "sheet": {"lecture_id": "123"},
        "rendition": {"url": "https://assets.underline.io/source.m3u8"},
    }
    local, segments = server.download_segments(record, report, staging)
    assert segments[0].read_bytes() == original
    assert "0.ts" in local.read_text() and "https://" not in local.read_text()
    server.download_segments(record, report, staging)
    assert requests == ["https://assets.underline.io/chunk.ts"]


def test_truncated_original_segment_does_not_become_a_verified_source(
    tmp_path, monkeypatch
):
    report, staging = tmp_path / "report", tmp_path / "staging"
    report.mkdir()
    staging.mkdir()
    monkeypatch.setattr(
        server, "fetch", lambda *args: b"#EXTM3U\n#EXTINF:2,\nchunk.ts\n#EXT-X-ENDLIST\n"
    )

    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Length": "100"}

        def geturl(self):
            return "https://assets.underline.io/chunk.ts"

    monkeypatch.setattr(server, "urlopen", lambda *args, **kwargs: Response(b"truncated"))
    record = {
        "sheet": {"lecture_id": "123"},
        "rendition": {"url": "https://assets.underline.io/source.m3u8"},
    }
    with pytest.raises(ValueError, match="Incomplete original segment"):
        server.download_segments(record, report, staging)
    assert not (staging / ".segments/123/0.ts").exists()
    assert not (report / "segments/123/0.json").exists()
    assert (staging / ".segments/123/0.ts.part").exists()


def test_unpublished_download_requires_explicit_hold_and_cannot_be_placed(
    tmp_path, monkeypatch
):
    row = {"lecture_id": "123", "sheet_row": "2"}
    data = {
        "data": {
            "id": "123",
            "attributes": {
                "published": False,
                "package": "free",
                "title": "Unpublished paper",
                "playlist": "https://assets.underline.io/master.m3u8",
            },
        }
    }
    monkeypatch.setattr(
        server, "fetch", lambda *args, **kwargs: json.dumps(data).encode()
    )
    monkeypatch.setattr(server, "rendition", lambda *args: {"height": 1080})
    with pytest.raises(ValueError, match="not publicly released"):
        server.catalog_record(row, tmp_path)
    result = server.catalog_record(row, tmp_path, include_unpublished=True)
    assert result["publication_allowed"] is False
    source = tmp_path / "123.mp4"
    source.write_bytes(b"retained unpublished original")
    verified = recording(source)
    verified["publication_allowed"] = False
    with pytest.raises(ValueError, match="unpublished"):
        server.place({"records": [verified]}, tmp_path, tmp_path, tmp_path)


def test_remux_preserves_actual_packets_despite_rounded_hls_duration():
    original = server.media_progress("frame=20530\nout_time_us=685013333\nprogress=end\n")
    decoded = server.media_progress("frame=20530\nout_time_us=685050000\nprogress=end\n")
    server.verify_preservation(original, decoded)
    with pytest.raises(ValueError, match="lost original source frames"):
        server.verify_preservation(original, (decoded[0], 20529))
    with pytest.raises(ValueError, match="original packet timing"):
        server.verify_preservation(original, (684.0, 20530))
    with pytest.raises(ValueError, match="not reported"):
        server.media_progress("frame=20530\nout_time_us=685013333\nprogress=continue\n")


def test_stream_copy_counts_packet_hashes_without_a_progress_frame_field():
    packets = "#media_type 0: video\n" + "\n".join(
        f"{stream}, 0, 0, 3003, 100, {'a' * 64}" for stream in (0, 1, 0)
    )
    packets += f", S=1, 1, {'b' * 64}"
    count = server.packet_frame_count(packets)
    assert count == 2
    assert server.media_progress("out_time_us=685013333\nprogress=end\n", count) == (
        685.013333,
        2,
    )
    with pytest.raises(ValueError, match="no verified video packets"):
        server.packet_frame_count("#media_type 1: audio\n")


def test_packet_count_disagreement_requires_original_decode_not_a_tolerance():
    calls = []

    def original_decode():
        calls.append("decoded original")
        return 152.362667, 4565

    reference, method = server.source_reference(
        (152.362667, 4566), (152.362667, 4565), original_decode
    )
    assert calls == ["decoded original"]
    assert reference == (152.362667, 4565)
    assert method == "source-decoded-frame-count"
    with pytest.raises(ValueError, match="lost original source frames"):
        server.source_reference(
            (152.362667, 4566),
            (152.362667, 4565),
            lambda: (152.362667, 4566),
        )
    with pytest.raises(ValueError, match="original packet timing"):
        server.source_reference(
            (152.362667, 4566),
            (151.0, 4565),
            lambda: (152.362667, 4565),
        )


def test_rate_limit_closes_response_and_exposes_required_cooldown(monkeypatch):
    body = io.BytesIO(b"rate limit response")
    error = HTTPError(
        "https://app.underline.io/api/v1/example",
        429,
        "Too Many Requests",
        {"Retry-After": "5"},
        body,
    )

    def limited(*args, **kwargs):
        raise error

    monkeypatch.setattr(common, "urlopen", limited)
    monkeypatch.setattr(common, "_api_next", 0.0)
    with pytest.raises(common.RateLimited) as caught:
        common.fetch(error.url, {"app.underline.io"}, json_api=True)
    assert caught.value.retry_after == 5
    assert body.closed


def test_published_only_v1_receipt_resumes_without_requerying_provider(
    tmp_path, monkeypatch
):
    row = {"lecture_id": "123", "sheet_row": "2"}
    common.write_json(
        tmp_path / "catalog/123.json",
        {
            "sheet": row,
            "status": "available",
            "provider_title": "Previously verified title",
            "provider_paper_link": None,
            "provider_authors": ["First Last"],
            "playlist": "https://assets.underline.io/master.m3u8",
            "rendition": {"height": 1080},
        },
    )

    def unexpected_request(*args, **kwargs):
        raise AssertionError("An already verified catalog must not be downloaded again")

    monkeypatch.setattr(server, "fetch", unexpected_request)
    result = server.catalog_record(row, tmp_path)
    assert result["publication_allowed"] is True
    assert result["publication_policy"] == "published-v1-gate"


def test_review_cannot_override_original_unpublished_download_registry(tmp_path):
    source = tmp_path / "123.mp4"
    source.write_bytes(b"unpublished original")
    row = recording(source)
    common.write_json(
        tmp_path / "downloads/123.json",
        {
            **row,
            "status": "downloaded",
            "publication_allowed": False,
        },
    )
    with pytest.raises(ValueError, match="download registry marks.*unpublished"):
        server.place({"records": [row]}, tmp_path, tmp_path, tmp_path)


def test_incomplete_http_response_is_recorded_without_losing_the_rest_of_the_batch(
    tmp_path,
):
    rows = [
        {"lecture_id": "123", "sheet_row": "2"},
        {"lecture_id": "456", "sheet_row": "3"},
    ]

    def action(row):
        if row["lecture_id"] == "123":
            raise IncompleteRead(b"partial", 10)
        return {"sheet": row, "status": "downloaded"}

    results, failed = server.parallel_records(rows, 1, action, tmp_path, "download")
    assert failed == 1
    assert results[0]["status"] == "failed" and "IncompleteRead" in results[0]["error"]
    assert results[1]["status"] == "downloaded"
    assert common.read_json(tmp_path / "download-job.json")["completed"] == 2


def test_normalized_original_cannot_be_deleted_or_changed_during_finalization(tmp_path):
    report, staging, videos = (
        tmp_path / name for name in ("report", "staging", "videos")
    )
    for path in (report, staging, videos):
        path.mkdir()
    original = staging / "123.original.mp4"
    original.write_bytes(b"original recording")
    row = {
        "original_retained_path": str(original),
        "original_fingerprint": common.fingerprint(original),
        "original_sha256": common.digest(original),
    }
    common.write_json(report / "placements.json", [row])
    common.write_json(
        report / "metadata-validation.json",
        {
            "status": "passed",
            "repository_checks": {"status": "passed"},
            "placements_sha256": common.digest(report / "placements.json"),
        },
    )
    original.write_bytes(b"changed recording")
    with pytest.raises(ValueError, match="retained original changed"):
        server.finalize(report, staging, videos, "move")
    assert original.exists()
    assert not (report / "moves.jsonl").exists()
