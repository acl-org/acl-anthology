#!/usr/bin/env python3
"""Validate and safely extract a generated website tar archive."""

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile


class ArchiveValidationError(ValueError):
    """Raised when a site archive violates the deployment contract."""


def canonical_member_path(member: tarfile.TarInfo) -> PurePosixPath | None:
    """Return a safe relative path, or None for the archive's root directory."""
    name = member.name
    if "\x00" in name or "\\" in name:
        raise ArchiveValidationError(f"unsafe archive path: {name!r}")
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        raise ArchiveValidationError(f"control character in archive path: {name!r}")

    while name.startswith("./"):
        name = name[2:]
    if member.isdir():
        name = name.rstrip("/")
    if name in ("", "."):
        if member.isdir():
            return None
        raise ArchiveValidationError("the archive root must be a directory")
    if name.startswith("/"):
        raise ArchiveValidationError(f"absolute archive path: {member.name!r}")

    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ArchiveValidationError(f"unsafe archive path: {member.name!r}")
    if len(name.encode("utf-8")) > 4096:
        raise ArchiveValidationError(f"archive path is too long: {member.name!r}")
    if any(len(part.encode("utf-8")) > 255 for part in parts):
        raise ArchiveValidationError(
            f"archive path component is too long: {member.name!r}"
        )

    return PurePosixPath(*parts)


def validate_and_extract(
    archive_path: Path,
    output_dir: Path,
    *,
    max_archive_bytes: int,
    max_expanded_bytes: int,
    max_file_bytes: int,
    max_entries: int,
) -> tuple[int, int]:
    """Validate archive_path and extract regular files into a new output_dir."""
    archive_size = archive_path.stat().st_size
    if archive_size == 0 or archive_size > max_archive_bytes:
        raise ArchiveValidationError(
            f"archive size {archive_size} is outside 1..{max_archive_bytes} bytes"
        )
    if output_dir.exists():
        raise ArchiveValidationError(f"output path already exists: {output_dir}")

    members: list[tuple[tarfile.TarInfo, PurePosixPath, bool]] = []
    path_types: dict[PurePosixPath, bool] = {}
    expanded_bytes = 0

    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for entry_number, member in enumerate(archive, start=1):
                if entry_number > max_entries:
                    raise ArchiveValidationError(
                        f"archive contains more than {max_entries} entries"
                    )
                if not (member.isdir() or member.isfile()):
                    raise ArchiveValidationError(
                        f"unsupported archive entry type for {member.name!r}"
                    )

                member_path = canonical_member_path(member)
                if member_path is None:
                    continue
                if member_path in path_types:
                    raise ArchiveValidationError(
                        f"duplicate archive path: {member_path.as_posix()!r}"
                    )

                is_directory = member.isdir()
                path_types[member_path] = is_directory
                if is_directory:
                    if member.size != 0:
                        raise ArchiveValidationError(
                            f"directory has nonzero size: {member_path.as_posix()!r}"
                        )
                else:
                    if member.size < 0 or member.size > max_file_bytes:
                        raise ArchiveValidationError(
                            f"file {member_path.as_posix()!r} exceeds the "
                            f"{max_file_bytes}-byte limit"
                        )
                    expanded_bytes += member.size
                    if expanded_bytes > max_expanded_bytes:
                        raise ArchiveValidationError(
                            f"expanded archive exceeds {max_expanded_bytes} bytes"
                        )
                members.append((member, member_path, is_directory))

            for member_path in path_types:
                for parent in member_path.parents:
                    if parent == PurePosixPath("."):
                        break
                    if parent in path_types and not path_types[parent]:
                        raise ArchiveValidationError(
                            f"file is used as a parent directory: {parent.as_posix()!r}"
                        )

            output_dir.mkdir(parents=True, mode=0o755)
            os.chmod(output_dir, 0o755)
            for _, member_path, is_directory in sorted(
                members, key=lambda item: (not item[2], len(item[1].parts))
            ):
                if is_directory:
                    destination = output_dir.joinpath(*member_path.parts)
                    destination.mkdir(parents=True, exist_ok=True, mode=0o755)
                    os.chmod(destination, 0o755)

            file_count = 0
            for member, member_path, is_directory in members:
                if is_directory:
                    continue
                destination = output_dir.joinpath(*member_path.parts)
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                source = archive.extractfile(member)
                if source is None:
                    raise ArchiveValidationError(
                        f"could not read archive file: {member_path.as_posix()!r}"
                    )

                remaining = member.size
                with source, destination.open("xb") as target:
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ArchiveValidationError(
                                f"truncated archive file: {member_path.as_posix()!r}"
                            )
                        target.write(chunk)
                        remaining -= len(chunk)
                    if source.read(1):
                        raise ArchiveValidationError(
                            f"archive file exceeds declared size: {member_path.as_posix()!r}"
                        )
                os.chmod(destination, 0o644)
                file_count += 1
    except (ArchiveValidationError, OSError, tarfile.TarError):
        shutil.rmtree(output_dir, ignore_errors=True)
        raise

    return file_count, expanded_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-archive-bytes", type=int, required=True)
    parser.add_argument("--max-expanded-bytes", type=int, required=True)
    parser.add_argument("--max-file-bytes", type=int, required=True)
    parser.add_argument("--max-entries", type=int, required=True)
    args = parser.parse_args()

    try:
        file_count, expanded_bytes = validate_and_extract(
            args.archive,
            args.output,
            max_archive_bytes=args.max_archive_bytes,
            max_expanded_bytes=args.max_expanded_bytes,
            max_file_bytes=args.max_file_bytes,
            max_entries=args.max_entries,
        )
    except (ArchiveValidationError, OSError, tarfile.TarError) as error:
        parser.error(str(error))

    print(
        f"Validated {file_count} files ({expanded_bytes} expanded bytes) "
        f"from {args.archive}."
    )


if __name__ == "__main__":
    main()
