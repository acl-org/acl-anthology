"""Shared validation and persistence for archived presentation videos."""

import csv
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import unicodedata
from urllib.error import HTTPError
from typing import NoReturn
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class RateLimited(ValueError):
    def __init__(self, host: str, retry_after: int):
        self.host = host
        self.retry_after = retry_after
        super().__init__(
            f"{host} rate limited requests; wait at least {retry_after} seconds"
        )


_api_lock = threading.Lock()
_api_next = 0.0


def normalize(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", html.unescape(text)).casefold()
        if char.isalnum()
    )


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"Refusing a symlinked output: {path}")
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_json(path: Path):
    return json.loads(path.read_text())


def http_failure(error: HTTPError, host: str) -> NoReturn:
    global _api_next
    code = error.code
    retry = error.headers.get("Retry-After", "60")
    error.close()
    if code == 429:
        if retry.isdigit():
            wait = max(1, int(retry))
        else:
            from datetime import datetime, timezone
            from email.utils import parsedate_to_datetime

            wait = max(
                1,
                int(
                    (
                        parsedate_to_datetime(retry) - datetime.now(timezone.utc)
                    ).total_seconds()
                ),
            )
        with _api_lock:
            _api_next = max(_api_next, time.monotonic() + wait)
        raise RateLimited(host, wait) from None
    raise ValueError(f"HTTP {code} while fetching {error.url}") from None


def fetch(url: str, hosts: set[str], *, json_api: bool = False) -> bytes:
    global _api_next
    parsed = urlparse(url)
    host = parsed.hostname
    if (
        parsed.scheme != "https"
        or host is None
        or host not in hosts
        or parsed.username
        or parsed.password
    ):
        raise ValueError(f"Unapproved source URL: {url}")
    headers = {"User-Agent": "ACL-Anthology-video-ingestion"}
    if json_api:
        headers["Accept"] = "application/vnd.api+json"
        with _api_lock:
            time.sleep(max(0, _api_next - time.monotonic()))
            _api_next = time.monotonic() + 1
    try:
        with urlopen(Request(url, headers=headers), timeout=60) as response:
            if urlparse(response.geturl()).hostname not in hosts:
                raise ValueError("Unexpected source redirect")
            if response.status != 200:
                raise ValueError(f"Unexpected source status: {response.status}")
            data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise ValueError("Source metadata exceeds the size limit")
            return data
    except HTTPError as error:
        http_failure(error, host)


def sheet_records(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"Title", "Paper number", "video", "Frontend URI"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Unexpected spreadsheet columns")
        records = []
        seen = set()
        for number, row in enumerate(reader, start=2):
            flag = row["video"].strip().casefold()
            if flag not in {"", "yes", "no"}:
                raise ValueError(f"Unknown video flag on row {number}: {flag}")
            if flag != "yes":
                continue
            url = row["Frontend URI"].strip()
            parsed = urlparse(url)
            match = re.fullmatch(r"/lecture/(\d+)-[^/]+/?", parsed.path)
            if (
                parsed.scheme != "https"
                or parsed.hostname != "underline.io"
                or parsed.username
                or parsed.password
                or not match
            ):
                raise ValueError(f"Invalid lecture URL on row {number}")
            lecture_id = match[1]
            if lecture_id in seen:
                raise ValueError(f"Duplicate lecture: {lecture_id}")
            seen.add(lecture_id)
            records.append(
                {
                    "lecture_id": lecture_id,
                    "sheet_row": str(number),
                    "paper_number": row["Paper number"].strip(),
                    "sheet_title": row["Title"].strip(),
                    "sheet_paper_link": row.get(
                        "Paper Link (Proceedings Link)", ""
                    ).strip(),
                    "event_session": row.get("Event session", "").strip(),
                    "lecture_url": url,
                }
            )
    return records


def fingerprint(path: Path) -> dict[str, int]:
    import stat

    value = path.lstat()
    if not stat.S_ISREG(value.st_mode):
        raise ValueError(f"Not a regular file: {path}")
    return {
        "device": value.st_dev,
        "inode": value.st_ino,
        "size": value.st_size,
        "mtime_ns": value.st_mtime_ns,
        "mode": stat.S_IMODE(value.st_mode),
    }


def scoped(path: Path, root: Path) -> Path:
    if (
        not path.is_absolute()
        or ".." in path.parts
        or root not in path.parents
        or path.parent.resolve() != path.parent
    ):
        raise ValueError(f"Path outside its approved root or symlinked: {path}")
    return path
