"""Download, validate, and place public Underline recordings on the archive server."""

import argparse
import fcntl
from http.client import HTTPException
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable
from urllib.parse import urljoin, urlparse
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from common import (
    digest,
    fetch,
    fingerprint,
    fsync_directory,
    http_failure,
    read_json,
    RateLimited,
    scoped,
    sheet_records,
    write_json,
)


ASSET_HOSTS = {"assets.underline.io"}


def rendition(playlist: str) -> dict:
    text = fetch(playlist, ASSET_HOSTS).decode()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    variants = []
    for index, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF:"):
            resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
            bandwidth = re.search(r"(?:AVERAGE-)?BANDWIDTH=(\d+)", line)
            if not resolution or not bandwidth or index + 1 >= len(lines):
                raise ValueError("Incomplete HLS variant")
            variants.append(
                {
                    "url": urljoin(playlist, lines[index + 1]),
                    "width": int(resolution[1]),
                    "height": int(resolution[2]),
                    "bandwidth": int(bandwidth[1]),
                }
            )
    if not variants:
        raise ValueError("Expected a master playlist with explicit renditions")
    selected = max(variants, key=lambda row: (row["height"], row["bandwidth"]))
    media = fetch(selected["url"], ASSET_HOSTS).decode()
    if "#EXT-X-ENDLIST" not in media:
        raise ValueError("Refusing an unfinished/live playlist")
    if re.search(r"#EXT-X-KEY:.*METHOD=(?!NONE)", media):
        raise ValueError("Encrypted recordings require a separately approved workflow")
    for line in media.splitlines():
        if line.strip() and not line.startswith("#"):
            parsed = urlparse(urljoin(selected["url"], line.strip()))
            if parsed.scheme != "https" or parsed.hostname not in ASSET_HOSTS:
                raise ValueError("Unapproved media segment URL")
    duration = sum(float(value) for value in re.findall(r"#EXTINF:([\d.]+)", media))
    if not duration > 0:
        raise ValueError("Playlist has no duration")
    selected["expected_duration"] = duration
    selected["estimated_bytes"] = int(duration * selected["bandwidth"] / 8)
    return selected


def catalog_record(row: dict, report: Path, include_unpublished: bool = False) -> dict:
    output = report / "catalog" / (row["lecture_id"] + ".json")
    cached = None
    if output.is_file():
        cached = read_json(output)
        legacy_keys = {
            "sheet",
            "status",
            "provider_title",
            "provider_paper_link",
            "provider_authors",
            "playlist",
            "rendition",
        }
        if (
            set(cached) == legacy_keys
            and cached["sheet"] == row
            and cached["status"] == "available"
        ):
            # Version 1 only wrote receipts after its published/free gate passed.
            cached["publication_allowed"] = True
            cached["publication_policy"] = "published-v1-gate"
            write_json(output, cached)
            print(
                "Upgraded published-only catalog receipt", row["lecture_id"], flush=True
            )
        if (
            cached.get("sheet") == row
            and cached["status"] == "available"
            and "publication_allowed" in cached
            and (cached["publication_allowed"] or include_unpublished)
        ):
            return cached
    url = (
        "https://app.underline.io/api/v1/thin_lectures/"
        + row["lecture_id"]
        + "?include=tag,event,sorted_profiles"
    )
    data = json.loads(fetch(url, {"app.underline.io"}, json_api=True))
    if str(data["data"]["id"]) != row["lecture_id"]:
        raise ValueError("Provider returned another lecture")
    attributes = data["data"]["attributes"]
    if not isinstance(attributes["published"], bool):
        raise ValueError("Provider did not supply a boolean publication status")
    if attributes["package"] != "free" or (
        not attributes["published"] and not include_unpublished
    ):
        raise ValueError("Recording is not publicly released with free access")
    authors = [
        (person["attributes"].get("first_name") or "")
        + " "
        + (person["attributes"].get("last_name") or "")
        for person in data.get("included", [])
        if person["type"] == "thin_profiles"
    ]
    record = {
        "sheet": row,
        "status": "available",
        "provider_title": attributes["title"],
        "provider_paper_link": attributes.get("paperLink"),
        "provider_authors": [name.strip() for name in authors],
        "playlist": attributes["playlist"],
        "publication_allowed": bool(attributes["published"]),
        "publication_policy": "published"
        if attributes["published"]
        else "unpublished-retain-only",
        "rendition": (
            cached["rendition"]
            if cached
            and cached.get("sheet") == row
            and cached.get("playlist") == attributes["playlist"]
            else rendition(attributes["playlist"])
        ),
    }
    write_json(output, record)
    return record


def parallel_records(rows: list[dict], workers: int, action, report: Path, phase: str):
    with (report / (phase + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_records(rows, workers, action, report, phase)


def run_records(rows: list[dict], workers: int, action, report: Path, phase: str):
    results = []
    failed = 0
    status = {
        "status": "running",
        "phase": phase,
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "total": len(rows),
        "workers": workers,
        "completed": 0,
        "failed": 0,
        "script_sha256": digest(Path(__file__)),
    }
    write_json(report / (phase + "-job.json"), status)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(action, row): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            try:
                result = future.result()
            except (
                CancelledError,
                HTTPException,
                OSError,
                ValueError,
                KeyError,
                RuntimeError,
                subprocess.SubprocessError,
            ) as error:
                failed += 1
                if isinstance(error, RateLimited):
                    for pending in futures:
                        pending.cancel()
                    write_json(
                        report / "rate-limit.json",
                        {
                            "host": error.host,
                            "retry_after_seconds": error.retry_after,
                            "observed_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                result = {
                    "sheet": row.get("sheet", row),
                    "status": "failed",
                    "phase": phase,
                    "error": (
                        "Not attempted: provider requested a cooldown."
                        if isinstance(error, CancelledError)
                        else f"{type(error).__name__}: {error}"
                    ),
                }
                write_json(
                    report
                    / "failures"
                    / (phase + "-" + result["sheet"]["lecture_id"] + ".json"),
                    result,
                )
                if not isinstance(error, CancelledError):
                    print(result["error"], file=sys.stderr, flush=True)
            results.append(result)
            if len(results) % 25 == 0 or len(results) == len(rows):
                print(phase, len(results), "/", len(rows), "failed", failed, flush=True)
                write_json(
                    report / (phase + "-job.json"),
                    {
                        **status,
                        "completed": len(results),
                        "failed": failed,
                    },
                )
    results.sort(key=lambda row: int(row["sheet"]["sheet_row"]))
    write_json(report / (phase + "-results.json"), results)
    write_json(
        report / (phase + "-job.json"),
        {
            **status,
            "status": "failed" if failed else "complete",
            "completed": len(results),
            "failed": failed,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return results, failed


def run_ffmpeg(command: list[str], log: Path, timeout: int = 1800):
    process = subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, umask=0o077
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(process.stderr)
    if process.returncode:
        raise RuntimeError(f"ffmpeg exited {process.returncode}; see {log}")
    return process


def media_progress(text: str, frame_count: int | None = None) -> tuple[float, int]:
    times = re.findall(r"^out_time_us=(\d+)$", text, re.MULTILINE)
    if frame_count is None:
        frames = re.findall(r"^frame=\s*(\d+)$", text, re.MULTILINE)
        frame_count = int(frames[-1]) if frames else 0
    if not times or frame_count <= 0 or "progress=end" not in text:
        raise ValueError("Complete source/video processing was not reported")
    return int(times[-1]) / 1_000_000, frame_count


def packet_frame_count(framehash: str) -> int:
    count = 0
    for line in framehash.splitlines():
        if not line or line.startswith("#"):
            continue
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 6 or len(fields[5]) != 64:
            raise ValueError("Unexpected source packet-hash output")
        int(fields[5], 16)
        if int(fields[0]) == 0:
            count += 1
    if count == 0:
        raise ValueError("Source has no verified video packets")
    return count


def verify_preservation(source: tuple[float, int], decoded: tuple[float, int]) -> None:
    if source[1] != decoded[1]:
        raise ValueError(
            f"Decoded video lost original source frames: {decoded[1]} versus {source[1]}"
        )
    if abs(source[0] - decoded[0]) > 0.1:
        raise ValueError(
            f"Decoded duration differs from original packet timing: {decoded[0]} versus {source[0]}"
        )


def source_reference(
    packets: tuple[float, int],
    decoded: tuple[float, int],
    decode_source: Callable[[], tuple[float, int]],
) -> tuple[tuple[float, int], str]:
    if packets[1] == decoded[1]:
        reference, method = packets, "source-packet-count"
    else:
        reference, method = decode_source(), "source-decoded-frame-count"
    verify_preservation(reference, decoded)
    return reference, method


def download_segments(
    record: dict, report: Path, staging: Path
) -> tuple[Path, list[Path]]:
    url = record["rendition"]["url"]
    text = fetch(url, ASSET_HOSTS).decode()
    if "#EXT-X-ENDLIST" not in text or re.search(r"URI=|#EXT-X-BYTERANGE", text):
        raise ValueError(
            "Local transport requires a complete, unencrypted MPEG-TS playlist"
        )
    folder = staging / ".segments" / record["sheet"]["lecture_id"]
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    rewritten = []
    segments = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            rewritten.append(line)
            continue
        segment_url = urljoin(url, line.strip())
        parsed = urlparse(segment_url)
        host = parsed.hostname
        if (
            parsed.scheme != "https"
            or host is None
            or host not in ASSET_HOSTS
            or parsed.username
            or parsed.password
            or not parsed.path.endswith(".ts")
        ):
            raise ValueError("Unapproved or unsupported segment")
        number = len(segments)
        segment = scoped(folder / f"{number}.ts", staging)
        receipt = report / "segments" / record["sheet"]["lecture_id"] / f"{number}.json"
        if segment.exists():
            fingerprint(segment)
            previous = read_json(receipt)
            if previous["url"] != segment_url or previous["sha256"] != digest(segment):
                raise ValueError("Cached original segment changed")
        else:
            partial = segment.with_suffix(".ts.part")
            if partial.exists():
                suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
                partial.rename(partial.with_name(partial.name + ".failed-" + suffix))
            try:
                response = urlopen(Request(segment_url), timeout=90)
            except HTTPError as error:
                http_failure(error, host)
            with response:
                if (
                    response.status != 200
                    or urlparse(response.geturl()).hostname not in ASSET_HOSTS
                ):
                    raise ValueError("Unexpected segment response")
                expected_size = response.headers.get("Content-Length")
                with partial.open("xb") as stream:
                    while block := response.read(1024 * 1024):
                        if shutil.disk_usage(staging).free < 20 * 1024**3:
                            raise OSError("Archive disk reserve reached")
                        stream.write(block)
                    stream.flush()
                    os.fsync(stream.fileno())
            if not partial.stat().st_size or (
                expected_size is not None and partial.stat().st_size != int(expected_size)
            ):
                raise ValueError("Incomplete original segment download")
            os.link(partial, segment, follow_symlinks=False)
            partial.unlink()
            write_json(
                receipt,
                {
                    "url": segment_url,
                    "sha256": digest(segment),
                    "size": segment.stat().st_size,
                },
            )
        rewritten.append(segment.name)
        segments.append(segment)
    playlist = scoped(folder / "source.m3u8", staging)
    if playlist.exists():
        fingerprint(playlist)
    playlist.write_text("\n".join(rewritten) + "\n")
    return playlist, segments


def download_record(record: dict, report: Path, staging: Path, ffmpeg: str) -> dict:
    if not isinstance(record["publication_allowed"], bool):
        raise ValueError("Recording release policy is missing or invalid")
    lecture_id = record["sheet"]["lecture_id"]
    source = scoped(staging / (lecture_id + ".mp4"), staging)
    receipt = report / "downloads" / (lecture_id + ".json")
    if source.exists():
        if not receipt.is_file():
            raise ValueError(f"Existing source has no verified receipt: {source}")
        cached = read_json(receipt)
        if cached["status"] != "downloaded" or cached[
            "source_fingerprint"
        ] != fingerprint(source):
            raise ValueError("Previously downloaded source changed")
        if cached["sha256"] != digest(source):
            raise ValueError("Previously downloaded source checksum changed")
        return cached
    expected = record["rendition"]["estimated_bytes"]
    if shutil.disk_usage(staging).free < expected + 20 * 1024**3:
        raise OSError("Archive disk reserve would be exhausted")
    partial = source.with_suffix(".mp4.part")
    if partial.exists():
        suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        partial.rename(partial.with_name(partial.name + ".failed-" + suffix))
    prefix = [ffmpeg, "-nostdin", "-hide_banner", "-threads", "1"]
    playlist, segments = download_segments(record, report, staging)
    original = run_ffmpeg(
        [
            *prefix,
            "-xerror",
            "-protocol_whitelist",
            "file,crypto",
            "-i",
            str(playlist),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-c",
            "copy",
            "-nostats",
            "-progress",
            "pipe:2",
            "-f",
            "framehash",
            "-",
        ],
        report / "logs" / (lecture_id + "-source-packet.log"),
    )
    source_progress = media_progress(original.stderr, packet_frame_count(original.stdout))
    run_ffmpeg(
        [
            *prefix,
            "-v",
            "warning",
            "-protocol_whitelist",
            "file,crypto",
            "-i",
            str(playlist),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            "-n",
            str(partial),
        ],
        report / "logs" / (lecture_id + "-download.log"),
    )
    process = run_ffmpeg(
        [
            *prefix,
            "-xerror",
            "-i",
            str(partial),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-vf",
            "blackdetect=d=0.1:pix_th=0.1:pic_th=0.98",
            "-filter_threads",
            "1",
            "-threads",
            "1",
            "-nostats",
            "-progress",
            "pipe:1",
            "-f",
            "null",
            "-",
        ],
        report / "logs" / (lecture_id + "-decode.log"),
    )
    decoded_progress = media_progress(process.stdout)

    def decode_source() -> tuple[float, int]:
        source_decode = run_ffmpeg(
            [
                *prefix,
                "-xerror",
                "-protocol_whitelist",
                "file,crypto",
                "-i",
                str(playlist),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                "blackdetect=d=0.1:pix_th=0.1:pic_th=0.98",
                "-filter_threads",
                "1",
                "-threads",
                "1",
                "-nostats",
                "-progress",
                "pipe:1",
                "-f",
                "null",
                "-",
            ],
            report / "logs" / (lecture_id + "-source-decode.log"),
        )
        return media_progress(source_decode.stdout)

    reference, validation_method = source_reference(
        source_progress, decoded_progress, decode_source
    )
    duration, decoded_frames = decoded_progress
    audio = bool(re.search(r"Stream #0:\d+.*Audio:", process.stderr))
    black = sum(
        float(value) for value in re.findall(r"black_duration:([\d.]+)", process.stderr)
    )
    timestamps = (
        (5.0, 12.0, 60.0)
        if duration > 61
        else (duration * 0.1, duration * 0.35, duration * 0.7)
    )
    images = []
    for number, timestamp in enumerate(timestamps):
        image = report / "frames" / lecture_id / (str(number) + ".jpg")
        image.parent.mkdir(parents=True, exist_ok=True)
        run_ffmpeg(
            [
                *prefix,
                "-v",
                "error",
                "-ss",
                str(timestamp),
                "-i",
                str(partial),
                "-map",
                "0:v:0",
                "-frames:v",
                "1",
                "-an",
                "-vf",
                "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-filter_threads",
                "1",
                "-threads",
                "1",
                "-pix_fmt",
                "yuvj420p",
                "-q:v",
                "3",
                "-y",
                str(image),
            ],
            report / "logs" / (lecture_id + f"-frame-{number}.log"),
            timeout=120,
        )
        if not image.is_file() or image.stat().st_size < 100:
            raise ValueError("Actual video frame extraction failed")
        images.append({"path": str(image.relative_to(report)), "timestamp": timestamp})
    os.link(partial, source, follow_symlinks=False)
    partial.unlink()
    source.chmod(0o600)
    fsync_directory(staging)
    result = {
        **record,
        "status": "downloaded",
        "source_path": str(source),
        "source_fingerprint": fingerprint(source),
        "sha256": digest(source),
        "duration_seconds": duration,
        "decoded_frames": decoded_frames,
        "source_packet_duration_seconds": source_progress[0],
        "source_video_packets": source_progress[1],
        "source_frame_reference": reference[1],
        "source_validation_method": validation_method,
        "playlist_duration_seconds": record["rendition"]["expected_duration"],
        "audio_stream": audio,
        "black_duration_ratio": black / duration,
        "frames": images,
        "original_segments": len(segments),
        "transport": "HTTPS segments downloaded with urllib; local lossless HLS remux",
    }
    write_json(receipt, result)
    for segment in segments:
        segment.unlink()
    playlist.unlink()
    if not any(playlist.parent.iterdir()):
        playlist.parent.rmdir()
    return result


def archive_path(videos: Path, paper_id: str, name: str) -> Path:
    match = re.fullmatch(r"\d{4}\.([a-zA-Z\d]+)-[a-zA-Z\d]+\.\d+", paper_id)
    if not match or not re.fullmatch(
        re.escape(paper_id) + r"(?:\.\d+)?\.(mp4|mov|m4v|webm)", name
    ):
        raise ValueError("Invalid canonical paper/video name")
    parent = videos / match[1]
    parent.mkdir(exist_ok=True)
    return scoped(parent / name, videos)


def place(plan: dict, report: Path, videos: Path, staging: Path) -> list[dict]:
    actions = []
    planned = {}
    for row in plan["records"]:
        if row["status"] != "verified":
            continue
        if not row["publication_allowed"]:
            raise ValueError("An unpublished recording must remain in retained staging")
        source = scoped(Path(row["source_path"]), staging)
        if any(not video["permission"] for video in row["existing_videos"]):
            raise ValueError("A withheld paper must not receive a public recording")
        downloaded = read_json(report / "downloads" / (row["lecture_id"] + ".json"))
        if not downloaded["publication_allowed"]:
            raise ValueError(
                "The original download registry marks this recording unpublished"
            )
        if (
            downloaded["status"] != "downloaded"
            or downloaded["source_path"] != row["source_path"]
            or downloaded["sha256"] != row["sha256"]
        ):
            raise ValueError("Reviewed recording does not match its download registry")
        receipt = report / "placements" / (row["lecture_id"] + ".json")
        if receipt.is_file():
            previous = read_json(receipt)
            if (
                previous["paper_id"] != row["paper_id"]
                or previous["sha256"] != row["sha256"]
                or fingerprint(Path(previous["destination_path"]))
                != previous["destination_fingerprint"]
                or digest(Path(previous["destination_path"])) != row["sha256"]
            ):
                raise ValueError("Previous placement differs from the reviewed recording")
            if fingerprint(source) != previous["source_fingerprint"]:
                raise ValueError("Previously placed source changed")
            actions.append(previous)
            planned[(row["paper_id"], row["sha256"])] = previous
            continue
        if (
            fingerprint(source) != row["source_fingerprint"]
            or digest(source) != row["sha256"]
        ):
            raise ValueError("Verified source changed before placement")
        chosen = None
        prior = planned.get((row["paper_id"], row["sha256"]))
        if prior:
            chosen = (
                Path(prior["destination_path"]),
                prior["reference_name"],
                "reused-in-run",
            )
        for video in row["existing_videos"]:
            if chosen:
                break
            name = video["name"]
            if "://" in name:
                continue
            destination = archive_path(videos, row["paper_id"], name)
            if destination.is_file() and digest(destination) == row["sha256"]:
                chosen = (destination, name, "already-present")
                break
        if chosen is None:
            number = 0
            while True:
                name = row["paper_id"] + (f".{number}" if number else "") + ".mp4"
                destination = archive_path(videos, row["paper_id"], name)
                if not os.path.lexists(destination):
                    break
                number += 1
            os.link(source, destination, follow_symlinks=False)
            os.chmod(destination, 0o644)
            fsync_directory(destination.parent)
            chosen = (destination, name, "added")
        destination, name, status = chosen
        if digest(destination) != row["sha256"]:
            raise ValueError("Placed media checksum differs")
        action = {
            **row,
            "reference_name": name,
            "metadata_status": status,
            "destination_path": str(destination),
            "destination_fingerprint": fingerprint(destination),
            "source_fingerprint": fingerprint(source),
            "url": "https://aclanthology.org/" + name,
        }
        actions.append(action)
        planned[(row["paper_id"], row["sha256"])] = action
        write_json(receipt, action)
    write_json(report / "placements.json", actions)
    return actions


def finalize(report: Path, staging: Path, videos: Path, mode: str):
    placements = read_json(report / "placements.json")
    validation = read_json(report / "metadata-validation.json")
    if validation["status"] != "passed":
        raise ValueError("Metadata save/reload validation is required")
    if validation.get("repository_checks", {}).get("status") != "passed":
        raise ValueError("Passing repository checks are required before source movement")
    if validation["placements_sha256"] != digest(report / "placements.json"):
        raise ValueError("Validation covers a different placement plan")
    moved = {}
    for row in placements:
        if row.get("original_retained_path"):
            original = scoped(Path(row["original_retained_path"]), staging)
            if (
                fingerprint(original) != row["original_fingerprint"]
                or digest(original) != row["original_sha256"]
            ):
                raise ValueError("A normalized recording's retained original changed")
        if not row["publication_allowed"]:
            raise ValueError(
                "An unpublished recording cannot be finalized for publication"
            )
        source = scoped(Path(row["source_path"]), staging)
        destination = scoped(Path(row["destination_path"]), videos)
        if fingerprint(destination) != row["destination_fingerprint"]:
            raise ValueError("Canonical file changed since placement")
        if digest(destination) != row["sha256"]:
            raise ValueError("Final byte-identity check failed")
        receipt_path = report / "moves" / (row["lecture_id"] + ".json")
        if receipt_path.is_file():
            receipt = read_json(receipt_path)
            if receipt["placement"] != mode or receipt["action"] != row:
                raise ValueError("Movement receipt covers a different action")
            if not source.exists() and mode == "move":
                if receipt["status"] not in {"intent", "complete"}:
                    raise ValueError("Missing source lacks an authorized movement intent")
                moved[row["lecture_id"]] = receipt
        if row["lecture_id"] not in moved:
            if (
                fingerprint(source) != row["source_fingerprint"]
                or digest(source) != row["sha256"]
            ):
                raise ValueError("Staging source changed since placement")
        with urlopen(Request(row["url"], method="HEAD"), timeout=45) as response:
            if (
                response.status != 200
                or int(response.headers["Content-Length"])
                != row["destination_fingerprint"]["size"]
                or response.headers.get_content_type() != "video/mp4"
            ):
                raise ValueError("Public archive URL does not match the placed recording")
    journal = report / "moves.jsonl"
    with journal.open("a") as stream:
        for row in placements:
            source = Path(row["source_path"])
            destination = Path(row["destination_path"])
            receipt_path = report / "moves" / (row["lecture_id"] + ".json")
            if fingerprint(destination) != row["destination_fingerprint"]:
                raise ValueError("Destination changed immediately before movement")
            if row["lecture_id"] in moved:
                write_json(
                    receipt_path, {"status": "complete", "placement": mode, "action": row}
                )
                continue
            if fingerprint(source) != row["source_fingerprint"]:
                raise ValueError("Source changed immediately before movement")
            if mode == "move":
                write_json(
                    receipt_path, {"status": "intent", "placement": mode, "action": row}
                )
                stream.write(json.dumps({"event": "intent", **row}) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                source.unlink()
                fsync_directory(source.parent)
                if fingerprint(destination) != row["destination_fingerprint"]:
                    raise ValueError("Canonical recording changed after movement")
            stream.write(json.dumps({"event": mode, **row}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            write_json(
                receipt_path, {"status": "complete", "placement": mode, "action": row}
            )
    linked = {row["sheet"]["lecture_id"] for row in placements}
    for row in read_json(report / "download-results.json"):
        if row.get("original_retained_path"):
            original = scoped(Path(row["original_retained_path"]), staging)
            if (
                fingerprint(original) != row["original_fingerprint"]
                or digest(original) != row["original_sha256"]
            ):
                raise ValueError(
                    "A normalized recording's original was changed or removed"
                )
        if row["status"] == "downloaded" and row["sheet"]["lecture_id"] not in linked:
            source = scoped(Path(row["source_path"]), staging)
            if (
                fingerprint(source) != row["source_fingerprint"]
                or digest(source) != row["sha256"]
            ):
                raise ValueError("An unmatched original was changed or removed")
    write_json(
        report / "finalized.json",
        {
            "status": "complete",
            "placement": mode,
            "recordings": len(placements),
            "moved_sources": len(placements) if mode == "move" else 0,
            "placements_sha256": digest(report / "placements.json"),
            "journal_sha256": digest(journal),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("catalog", "download", "place", "finalize"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--staging", type=Path)
    parser.add_argument("--videos", type=Path)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 5))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-unpublished", action="store_true")
    parser.add_argument(
        "--placement", choices=("move", "hardlink-retain"), default="move"
    )
    args = parser.parse_args()
    report = args.report.resolve(strict=True)
    if args.command == "catalog":
        rows = sheet_records(report / "spreadsheet.csv")
        if args.limit:
            rows = rows[: args.limit]
        records, failed = parallel_records(
            rows,
            args.workers,
            lambda row: catalog_record(row, report, args.include_unpublished),
            report,
            "catalog",
        )
        print("AVAILABLE", sum(row["status"] == "available" for row in records))
        print(
            "ESTIMATED_BYTES",
            sum(
                row["rendition"]["estimated_bytes"]
                for row in records
                if row["status"] == "available"
            ),
        )
        raise SystemExit(1 if failed else 0)
    if args.staging is None:
        parser.error("--staging is required")
    staging = args.staging.resolve()
    staging.mkdir(parents=True, exist_ok=True)
    if args.command == "download":
        if not args.ffmpeg:
            parser.error("--ffmpeg is required")
        records = [
            row
            for row in read_json(report / "catalog-results.json")
            if row["status"] == "available"
        ]
        if args.limit:
            records = records[: args.limit]
        _, failed = parallel_records(
            records,
            args.workers,
            lambda row: download_record(row, report, staging, args.ffmpeg),
            report,
            "download",
        )
        raise SystemExit(1 if failed else 0)
    if args.videos is None:
        parser.error("--videos is required")
    videos = args.videos.resolve(strict=True)
    if args.command == "place":
        place(read_json(report / "reviewed.json"), report, videos, staging)
    else:
        finalize(report, staging, videos, args.placement)


if __name__ == "__main__":
    main()
