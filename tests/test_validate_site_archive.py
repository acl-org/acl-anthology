from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import tarfile

import pytest


SCRIPT = (
    Path(__file__).parents[1] / "bin" / "aclanthology.org" / "validate_site_archive.py"
)
SPEC = importlib.util.spec_from_file_location("validate_site_archive", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
validate_site_archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_site_archive)

ArchiveValidationError = validate_site_archive.ArchiveValidationError
validate_and_extract = validate_site_archive.validate_and_extract


def make_archive(path: Path, entries: list[tuple[str, str, bytes | str]]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for entry_type, name, value in entries:
            member = tarfile.TarInfo(name)
            if entry_type == "file":
                assert isinstance(value, bytes)
                member.size = len(value)
                archive.addfile(member, io.BytesIO(value))
            elif entry_type == "directory":
                member.type = tarfile.DIRTYPE
                archive.addfile(member)
            elif entry_type == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = str(value)
                archive.addfile(member)
            elif entry_type == "hardlink":
                member.type = tarfile.LNKTYPE
                member.linkname = str(value)
                archive.addfile(member)
            else:  # pragma: no cover
                raise AssertionError(f"unknown test entry type: {entry_type}")


def extract(archive: Path, output: Path, **overrides: int) -> tuple[int, int]:
    limits = {
        "max_archive_bytes": 1024 * 1024,
        "max_expanded_bytes": 1024 * 1024,
        "max_file_bytes": 1024 * 1024,
        "max_entries": 100,
    }
    limits.update(overrides)
    return validate_and_extract(archive, output, **limits)


def test_extracts_only_regular_files_and_directories(tmp_path: Path) -> None:
    archive = tmp_path / "site.tar.gz"
    output = tmp_path / "output"
    make_archive(
        archive,
        [
            ("directory", ".", ""),
            ("directory", "./assets/", ""),
            ("file", "./index.html", b"<h1>ACL</h1>"),
            ("file", "./assets/site.css", b"body {}"),
        ],
    )

    assert extract(archive, output) == (2, 19)
    assert (output / "index.html").read_bytes() == b"<h1>ACL</h1>"
    assert (output / "assets" / "site.css").read_bytes() == b"body {}"
    assert (output / "index.html").stat().st_mode & 0o777 == 0o644
    assert (output / "assets").stat().st_mode & 0o777 == 0o755


@pytest.mark.parametrize(
    ("entry_type", "name", "value"),
    [
        ("file", "../escape", b"bad"),
        ("file", "/absolute", b"bad"),
        ("file", "dir\\windows", b"bad"),
        ("symlink", "link", "target"),
        ("hardlink", "link", "target"),
    ],
)
def test_rejects_unsafe_entries(
    tmp_path: Path, entry_type: str, name: str, value: bytes | str
) -> None:
    archive = tmp_path / "site.tar.gz"
    output = tmp_path / "output"
    make_archive(archive, [(entry_type, name, value)])

    with pytest.raises(ArchiveValidationError):
        extract(archive, output)
    assert not output.exists()


def test_rejects_duplicate_paths(tmp_path: Path) -> None:
    archive = tmp_path / "site.tar.gz"
    output = tmp_path / "output"
    make_archive(
        archive,
        [("file", "index.html", b"first"), ("file", "./index.html", b"second")],
    )

    with pytest.raises(ArchiveValidationError, match="duplicate"):
        extract(archive, output)


def test_rejects_file_used_as_parent(tmp_path: Path) -> None:
    archive = tmp_path / "site.tar.gz"
    output = tmp_path / "output"
    make_archive(
        archive,
        [("file", "assets", b"file"), ("file", "assets/site.css", b"child")],
    )

    with pytest.raises(ArchiveValidationError, match="parent directory"):
        extract(archive, output)


@pytest.mark.parametrize(
    ("override", "value", "match"),
    [
        ("max_file_bytes", 3, "file.*exceeds"),
        ("max_expanded_bytes", 3, "expanded archive exceeds"),
        ("max_entries", 1, "more than 1 entries"),
    ],
)
def test_enforces_resource_limits(
    tmp_path: Path, override: str, value: int, match: str
) -> None:
    archive = tmp_path / "site.tar.gz"
    output = tmp_path / "output"
    make_archive(
        archive,
        [("file", "one", b"1234"), ("file", "two", b"5678")],
    )

    with pytest.raises(ArchiveValidationError, match=match):
        extract(archive, output, **{override: value})
