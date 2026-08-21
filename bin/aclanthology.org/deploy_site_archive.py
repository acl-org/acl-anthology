#!/usr/bin/env python3
"""Receive and atomically activate a validated ACL Anthology site archive."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import tomllib
from typing import BinaryIO, Any

from validate_site_archive import ArchiveValidationError, validate_and_extract


COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PREVIEW_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
RELEASE_PATTERN = re.compile(r"^[0-9a-f]{40}-[0-9a-f]{16}$")


class DeploymentError(RuntimeError):
    """Raised when a deployment request is invalid or cannot be activated."""


@dataclass(frozen=True)
class Limits:
    max_archive_bytes: int
    max_expanded_bytes: int
    max_file_bytes: int
    max_entries: int


@dataclass(frozen=True)
class CommonConfig:
    anthology_files: Path


@dataclass(frozen=True)
class ProductionConfig:
    release_root: Path
    current_link: Path
    lock_file: Path
    keep_releases: int
    limits: Limits


@dataclass(frozen=True)
class PreviewConfig:
    release_root: Path
    public_root: Path
    lock_file: Path
    max_age_days: int
    max_total_bytes: int
    limits: Limits


@dataclass(frozen=True)
class DeploymentRequest:
    commit: str
    digest: str
    size: int
    slug: str | None = None


def required_path(section: dict[str, Any], key: str) -> Path:
    value = section.get(key)
    if not isinstance(value, str) or not value.startswith("/"):
        raise DeploymentError(f"configuration value {key!r} must be an absolute path")
    return Path(value)


def required_positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise DeploymentError(f"configuration value {key!r} must be positive")
    return value


def load_limits(section: dict[str, Any]) -> Limits:
    return Limits(
        max_archive_bytes=required_positive_int(section, "max_archive_bytes"),
        max_expanded_bytes=required_positive_int(section, "max_expanded_bytes"),
        max_file_bytes=required_positive_int(section, "max_file_bytes"),
        max_entries=required_positive_int(section, "max_entries"),
    )


def load_config(
    config_path: Path,
) -> tuple[CommonConfig, ProductionConfig, PreviewConfig]:
    with config_path.open("rb") as config_file:
        raw = tomllib.load(config_file)

    common_section = raw.get("common", {})
    production_section = raw.get("production", {})
    preview_section = raw.get("preview", {})
    if not all(
        isinstance(section, dict)
        for section in (common_section, production_section, preview_section)
    ):
        raise DeploymentError("deployment configuration sections must be tables")

    common = CommonConfig(
        anthology_files=required_path(common_section, "anthology_files")
    )
    production = ProductionConfig(
        release_root=required_path(production_section, "release_root"),
        current_link=required_path(production_section, "current_link"),
        lock_file=required_path(production_section, "lock_file"),
        keep_releases=required_positive_int(production_section, "keep_releases"),
        limits=load_limits(production_section),
    )
    preview = PreviewConfig(
        release_root=required_path(preview_section, "release_root"),
        public_root=required_path(preview_section, "public_root"),
        lock_file=required_path(preview_section, "lock_file"),
        max_age_days=required_positive_int(preview_section, "max_age_days"),
        max_total_bytes=required_positive_int(preview_section, "max_total_bytes"),
        limits=load_limits(preview_section),
    )
    return common, production, preview


def parse_request(mode: str, original_command: str) -> DeploymentRequest:
    if not original_command or any(
        ord(character) < 32 or ord(character) == 127 for character in original_command
    ):
        raise DeploymentError("invalid SSH deployment command")

    fields = original_command.split(" ")
    if any(not field for field in fields):
        raise DeploymentError("invalid SSH deployment command spacing")
    expected_fields = 4 if mode == "production" else 5
    if len(fields) != expected_fields or fields[0] != "deploy":
        raise DeploymentError(f"invalid {mode} deployment command")

    if mode == "production":
        _, commit, digest, size_text = fields
        slug = None
    else:
        _, slug, commit, digest, size_text = fields
        if not PREVIEW_SLUG_PATTERN.fullmatch(slug):
            raise DeploymentError("invalid preview slug")

    if not COMMIT_PATTERN.fullmatch(commit):
        raise DeploymentError("invalid deployment commit")
    if not DIGEST_PATTERN.fullmatch(digest):
        raise DeploymentError("invalid deployment digest")
    if not size_text.isascii() or not size_text.isdecimal():
        raise DeploymentError("invalid deployment size")

    return DeploymentRequest(
        commit=commit,
        digest=digest,
        size=int(size_text),
        slug=slug,
    )


def ensure_managed_directory(path: Path) -> None:
    if not path.is_dir() or path.is_symlink():
        raise DeploymentError(f"managed directory is missing or unsafe: {path}")


def lexists(path: Path) -> bool:
    return os.path.lexists(path)


def receive_archive(
    stream: BinaryIO,
    destination_dir: Path,
    request: DeploymentRequest,
    max_archive_bytes: int,
) -> Path:
    if request.size <= 0 or request.size > max_archive_bytes:
        raise DeploymentError(
            f"archive size {request.size} is outside 1..{max_archive_bytes} bytes"
        )

    digest = hashlib.sha256()
    archive_file = tempfile.NamedTemporaryFile(
        dir=destination_dir,
        prefix=".incoming-",
        suffix=".tar.gz",
        delete=False,
    )
    archive_path = Path(archive_file.name)
    try:
        remaining = request.size
        with archive_file:
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise DeploymentError("deployment stream ended early")
                archive_file.write(chunk)
                digest.update(chunk)
                remaining -= len(chunk)
            if stream.read(1):
                raise DeploymentError("deployment stream exceeds declared size")
            archive_file.flush()
            os.fsync(archive_file.fileno())

        if digest.hexdigest() != request.digest:
            raise DeploymentError("deployment digest does not match archive bytes")
        return archive_path
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise


def directory_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for root, directories, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        directories[:] = [
            name for name in directories if not (root_path / name).is_symlink()
        ]
        for name in files:
            file_path = root_path / name
            if not file_path.is_symlink():
                total += file_path.stat().st_size
    return total


def cleanup_staging(root: Path, now: float | None = None) -> None:
    current_time = time.time() if now is None else now
    cutoff = current_time - 24 * 60 * 60
    for candidate in root.iterdir():
        if not candidate.name.startswith((".incoming-", ".extract-")):
            continue
        if candidate.is_symlink() or candidate.lstat().st_mtime >= cutoff:
            continue
        if candidate.is_dir():
            shutil.rmtree(candidate)
        elif candidate.is_file():
            candidate.unlink()


def atomic_link(link: Path, target: Path) -> None:
    ensure_managed_directory(link.parent)
    if lexists(link) and not link.is_symlink():
        raise DeploymentError(f"activation path is not a symlink: {link}")

    temporary_link = link.parent / f".{link.name}.new-{os.getpid()}"
    temporary_link.unlink(missing_ok=True)
    try:
        relative_target = os.path.relpath(target, link.parent)
        temporary_link.symlink_to(relative_target, target_is_directory=True)
        os.replace(temporary_link, link)
    finally:
        temporary_link.unlink(missing_ok=True)


def prepare_release(
    archive_path: Path,
    release_path: Path,
    staging_root: Path,
    common: CommonConfig,
    limits: Limits,
) -> tuple[Path, int]:
    if lexists(release_path):
        if not release_path.is_dir() or release_path.is_symlink():
            raise DeploymentError(f"existing release is unsafe: {release_path}")
        return release_path, directory_size(release_path)

    staging_dir = Path(tempfile.mkdtemp(dir=staging_root, prefix=".extract-"))
    extracted_site = staging_dir / "site"
    try:
        _, expanded_bytes = validate_and_extract(
            archive_path,
            extracted_site,
            max_archive_bytes=limits.max_archive_bytes,
            max_expanded_bytes=limits.max_expanded_bytes,
            max_file_bytes=limits.max_file_bytes,
            max_entries=limits.max_entries,
        )
        index_file = extracted_site / "index.html"
        if not index_file.is_file() or index_file.is_symlink():
            raise DeploymentError("site archive does not contain a regular index.html")

        anthology_files_link = extracted_site / "anthology-files"
        if lexists(anthology_files_link):
            raise DeploymentError("site archive contains a reserved anthology-files path")
        anthology_files_link.symlink_to(common.anthology_files, target_is_directory=True)

        release_path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        try:
            os.replace(extracted_site, release_path)
        except OSError:
            if not release_path.is_dir() or release_path.is_symlink():
                raise
        return release_path, expanded_bytes
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def cleanup_production(config: ProductionConfig, active_release: Path) -> None:
    releases = [
        path
        for path in config.release_root.iterdir()
        if path.is_dir()
        and not path.is_symlink()
        and RELEASE_PATTERN.fullmatch(path.name)
    ]
    releases.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    inactive_releases = [release for release in releases if release != active_release]
    keep = {
        active_release,
        *inactive_releases[: max(0, config.keep_releases - 1)],
    }
    for release in releases:
        if release not in keep:
            shutil.rmtree(release)


def preview_deployments(config: PreviewConfig) -> list[tuple[float, str, Path]]:
    deployments = []
    for link in config.public_root.iterdir():
        if not link.is_symlink() or not PREVIEW_SLUG_PATTERN.fullmatch(link.name):
            continue
        deployments.append((link.lstat().st_mtime, link.name, link))
    return deployments


def remove_preview(config: PreviewConfig, slug: str, link: Path) -> None:
    link.unlink(missing_ok=True)
    release_dir = config.release_root / slug
    if release_dir.is_dir() and not release_dir.is_symlink():
        shutil.rmtree(release_dir)


def cleanup_previews(config: PreviewConfig, now: float | None = None) -> None:
    ensure_managed_directory(config.release_root)
    ensure_managed_directory(config.public_root)
    current_time = time.time() if now is None else now
    cutoff = current_time - config.max_age_days * 24 * 60 * 60
    cleanup_staging(config.release_root, current_time)

    for modified, slug, link in preview_deployments(config):
        if modified < cutoff:
            remove_preview(config, slug, link)

    active_slugs = {slug for _, slug, _ in preview_deployments(config)}
    for release_dir in config.release_root.iterdir():
        if (
            release_dir.is_dir()
            and not release_dir.is_symlink()
            and PREVIEW_SLUG_PATTERN.fullmatch(release_dir.name)
            and release_dir.name not in active_slugs
        ):
            shutil.rmtree(release_dir)

    deployments = sorted(preview_deployments(config))
    total_bytes = directory_size(config.release_root)
    for _, slug, link in deployments:
        if total_bytes <= config.max_total_bytes:
            break
        remove_preview(config, slug, link)
        total_bytes = directory_size(config.release_root)


def deploy_production(
    stream: BinaryIO,
    request: DeploymentRequest,
    common: CommonConfig,
    config: ProductionConfig,
) -> str:
    ensure_managed_directory(config.release_root)
    ensure_managed_directory(config.current_link.parent)
    if not common.anthology_files.is_dir():
        raise DeploymentError(
            f"anthology-files directory is missing: {common.anthology_files}"
        )
    cleanup_staging(config.release_root)
    release_name = f"{request.commit}-{request.digest[:16]}"
    release_path = config.release_root / release_name

    archive_path = receive_archive(
        stream, config.release_root, request, config.limits.max_archive_bytes
    )
    try:
        release_path, _ = prepare_release(
            archive_path, release_path, config.release_root, common, config.limits
        )
        atomic_link(config.current_link, release_path)
        cleanup_production(config, release_path)
    finally:
        archive_path.unlink(missing_ok=True)
    return release_name


def evict_previews_for_space(
    config: PreviewConfig,
    incoming_slug: str,
    incoming_bytes: int,
) -> None:
    existing_slug_bytes = directory_size(config.release_root / incoming_slug)
    projected_bytes = (
        directory_size(config.release_root) - existing_slug_bytes + incoming_bytes
    )
    deployments = sorted(
        deployment
        for deployment in preview_deployments(config)
        if deployment[1] != incoming_slug
    )
    for _, slug, link in deployments:
        if projected_bytes <= config.max_total_bytes:
            break
        removed_bytes = directory_size(config.release_root / slug)
        remove_preview(config, slug, link)
        projected_bytes -= removed_bytes
    if projected_bytes > config.max_total_bytes:
        raise DeploymentError(
            f"preview quota of {config.max_total_bytes} bytes would be exceeded"
        )


def deploy_preview(
    stream: BinaryIO,
    request: DeploymentRequest,
    common: CommonConfig,
    config: PreviewConfig,
) -> str:
    if request.slug is None:  # pragma: no cover - enforced by parse_request
        raise DeploymentError("preview deployment is missing a slug")
    ensure_managed_directory(config.release_root)
    ensure_managed_directory(config.public_root)
    if not common.anthology_files.is_dir():
        raise DeploymentError(
            f"anthology-files directory is missing: {common.anthology_files}"
        )
    cleanup_previews(config)

    release_name = f"{request.commit}-{request.digest[:16]}"
    slug_root = config.release_root / request.slug
    release_path = slug_root / release_name
    release_existed = lexists(release_path)
    if lexists(slug_root) and (not slug_root.is_dir() or slug_root.is_symlink()):
        raise DeploymentError(f"preview release root is unsafe: {slug_root}")
    archive_path = receive_archive(
        stream, config.release_root, request, config.limits.max_archive_bytes
    )
    try:
        release_path, expanded_bytes = prepare_release(
            archive_path, release_path, config.release_root, common, config.limits
        )
        archive_path.unlink(missing_ok=True)
        evict_previews_for_space(config, request.slug, expanded_bytes)
        public_link = config.public_root / request.slug
        atomic_link(public_link, release_path)

        for old_release in slug_root.iterdir():
            if (
                old_release != release_path
                and old_release.is_dir()
                and not old_release.is_symlink()
            ):
                shutil.rmtree(old_release)
    except Exception:
        if (
            not release_existed
            and release_path.is_dir()
            and not release_path.is_symlink()
        ):
            shutil.rmtree(release_path)
        if (
            slug_root.is_dir()
            and not slug_root.is_symlink()
            and not any(slug_root.iterdir())
        ):
            slug_root.rmdir()
        raise
    finally:
        archive_path.unlink(missing_ok=True)
    return f"{request.slug}/{release_name}"


def locked(lock_file: Path):
    lock_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    lock = lock_file.open("a+")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    return lock


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/acl-anthology/deploy.toml"),
    )
    parser.add_argument("mode", choices=("production", "preview", "cleanup-previews"))
    args = parser.parse_args()

    try:
        common, production, preview = load_config(args.config)
        if args.mode == "cleanup-previews":
            with locked(preview.lock_file):
                cleanup_previews(preview)
            print("Preview cleanup complete.")
            return

        request = parse_request(args.mode, os.environ.get("SSH_ORIGINAL_COMMAND", ""))
        if args.mode == "production":
            with locked(production.lock_file):
                release = deploy_production(sys.stdin.buffer, request, common, production)
        else:
            with locked(preview.lock_file):
                release = deploy_preview(sys.stdin.buffer, request, common, preview)
        print(f"Activated {args.mode} release {release}.")
    except (ArchiveValidationError, DeploymentError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
