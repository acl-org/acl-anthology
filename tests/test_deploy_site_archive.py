from __future__ import annotations

import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

import pytest


SCRIPT_DIR = Path(__file__).parents[1] / "bin" / "aclanthology.org"
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_site_archive", SCRIPT_DIR / "validate_site_archive.py"
)
assert VALIDATOR_SPEC is not None and VALIDATOR_SPEC.loader is not None
validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
sys.modules[VALIDATOR_SPEC.name] = validator
VALIDATOR_SPEC.loader.exec_module(validator)

DEPLOY_SPEC = importlib.util.spec_from_file_location(
    "deploy_site_archive", SCRIPT_DIR / "deploy_site_archive.py"
)
assert DEPLOY_SPEC is not None and DEPLOY_SPEC.loader is not None
deploy = importlib.util.module_from_spec(DEPLOY_SPEC)
sys.modules[DEPLOY_SPEC.name] = deploy
DEPLOY_SPEC.loader.exec_module(deploy)


def make_archive(path: Path, files: dict[str, bytes]) -> bytes:
    with tarfile.open(path, "w:gz") as archive:
        for name, value in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(value)
            archive.addfile(member, io.BytesIO(value))
    return path.read_bytes()


def make_config(tmp_path: Path, *, preview_quota: int = 10_000) -> Path:
    paths = {
        "anthology_files": tmp_path / "anthology-files",
        "production_root": tmp_path / "production",
        "preview_root": tmp_path / "previews",
    }
    paths["anthology_files"].mkdir()
    (paths["production_root"] / "releases").mkdir(parents=True)
    (paths["preview_root"] / "releases").mkdir(parents=True)
    (paths["preview_root"] / "public").mkdir(parents=True)

    config = tmp_path / "deploy.toml"
    config.write_text(
        f"""
[common]
anthology_files = "{paths["anthology_files"]}"

[production]
release_root = "{paths["production_root"] / "releases"}"
current_link = "{paths["production_root"] / "current"}"
lock_file = "{paths["production_root"] / "deploy.lock"}"
keep_releases = 2
max_archive_bytes = 10000
max_expanded_bytes = 10000
max_file_bytes = 5000
max_entries = 100

[preview]
release_root = "{paths["preview_root"] / "releases"}"
public_root = "{paths["preview_root"] / "public"}"
lock_file = "{paths["preview_root"] / "deploy.lock"}"
max_age_days = 30
max_total_bytes = {preview_quota}
max_archive_bytes = 10000
max_expanded_bytes = 10000
max_file_bytes = 5000
max_entries = 100
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return config


def request(mode: str, archive: bytes, *, slug: str = "branch-123456789abc"):
    commit = "a" * 40
    digest = hashlib.sha256(archive).hexdigest()
    if mode == "production":
        command = f"deploy {commit} {digest} {len(archive)}"
    else:
        command = f"deploy {slug} {commit} {digest} {len(archive)}"
    return deploy.parse_request(mode, command)


def test_production_deploys_and_retains_previous_release(tmp_path: Path) -> None:
    config_path = make_config(tmp_path)
    common, production, _ = deploy.load_config(config_path)

    first_archive = make_archive(tmp_path / "first.tar.gz", {"index.html": b"first"})
    first_release = deploy.deploy_production(
        io.BytesIO(first_archive),
        request("production", first_archive),
        common,
        production,
    )
    assert production.current_link.is_symlink()
    assert (production.current_link / "index.html").read_bytes() == b"first"
    assert (
        production.current_link / "anthology-files"
    ).resolve() == common.anthology_files

    second_archive = make_archive(tmp_path / "second.tar.gz", {"index.html": b"second"})
    second_request = request("production", second_archive)
    second_request = deploy.DeploymentRequest(
        commit="b" * 40,
        digest=second_request.digest,
        size=second_request.size,
    )
    second_release = deploy.deploy_production(
        io.BytesIO(second_archive), second_request, common, production
    )

    assert first_release != second_release
    assert (production.current_link / "index.html").read_bytes() == b"second"
    assert len(list(production.release_root.iterdir())) == 2


def test_preview_deploys_atomically_and_replaces_old_release(tmp_path: Path) -> None:
    config_path = make_config(tmp_path)
    common, _, preview = deploy.load_config(config_path)
    slug = "feature-123456789abc"

    first_archive = make_archive(tmp_path / "first.tar.gz", {"index.html": b"first"})
    deploy.deploy_preview(
        io.BytesIO(first_archive),
        request("preview", first_archive, slug=slug),
        common,
        preview,
    )
    public_link = preview.public_root / slug
    assert public_link.is_symlink()
    assert (public_link / "index.html").read_bytes() == b"first"

    second_archive = make_archive(tmp_path / "second.tar.gz", {"index.html": b"second"})
    second_request = request("preview", second_archive, slug=slug)
    second_request = deploy.DeploymentRequest(
        commit="b" * 40,
        digest=second_request.digest,
        size=second_request.size,
        slug=slug,
    )
    deploy.deploy_preview(io.BytesIO(second_archive), second_request, common, preview)

    assert (public_link / "index.html").read_bytes() == b"second"
    assert len(list((preview.release_root / slug).iterdir())) == 1


def test_rejects_wrong_digest_and_cleans_incoming_file(tmp_path: Path) -> None:
    config_path = make_config(tmp_path)
    common, production, _ = deploy.load_config(config_path)
    archive = make_archive(tmp_path / "site.tar.gz", {"index.html": b"site"})
    invalid_request = deploy.DeploymentRequest(
        commit="a" * 40,
        digest="0" * 64,
        size=len(archive),
    )

    with pytest.raises(deploy.DeploymentError, match="digest"):
        deploy.deploy_production(io.BytesIO(archive), invalid_request, common, production)
    assert not list(production.release_root.glob(".incoming-*"))


@pytest.mark.parametrize(
    "command",
    [
        "",
        "deploy bad-sha " + "0" * 64 + " 1",
        "deploy  " + "a" * 40 + " " + "0" * 64 + " 1",
        "deploy ../escape " + "a" * 40 + " " + "0" * 64 + " 1",
    ],
)
def test_rejects_invalid_commands(command: str) -> None:
    mode = "preview" if "../escape" in command else "production"
    with pytest.raises(deploy.DeploymentError):
        deploy.parse_request(mode, command)


def test_cleanup_removes_expired_preview(tmp_path: Path) -> None:
    config_path = make_config(tmp_path)
    common, _, preview = deploy.load_config(config_path)
    slug = "expired-123456789abc"
    archive = make_archive(tmp_path / "site.tar.gz", {"index.html": b"site"})
    deploy.deploy_preview(
        io.BytesIO(archive),
        request("preview", archive, slug=slug),
        common,
        preview,
    )
    link = preview.public_root / slug
    expired_time = time.time() - 31 * 24 * 60 * 60
    os.utime(link, (expired_time, expired_time), follow_symlinks=False)

    deploy.cleanup_previews(preview)

    assert not os.path.lexists(link)
    assert not (preview.release_root / slug).exists()


def test_preview_quota_evicts_oldest_other_preview(tmp_path: Path) -> None:
    config_path = make_config(tmp_path, preview_quota=16)
    common, _, preview = deploy.load_config(config_path)
    first_slug = "first-123456789abc"
    second_slug = "second-123456789abc"
    first_archive = make_archive(tmp_path / "first.tar.gz", {"index.html": b"1234567890"})
    deploy.deploy_preview(
        io.BytesIO(first_archive),
        request("preview", first_archive, slug=first_slug),
        common,
        preview,
    )

    second_archive = make_archive(
        tmp_path / "second.tar.gz", {"index.html": b"abcdefghij"}
    )
    deploy.deploy_preview(
        io.BytesIO(second_archive),
        request("preview", second_archive, slug=second_slug),
        common,
        preview,
    )

    assert not os.path.lexists(preview.public_root / first_slug)
    assert (preview.public_root / second_slug).is_symlink()


def test_quota_failure_leaves_no_unactivated_release(tmp_path: Path) -> None:
    config_path = make_config(tmp_path, preview_quota=5)
    common, _, preview = deploy.load_config(config_path)
    slug = "too-large-123456789abc"
    archive = make_archive(tmp_path / "site.tar.gz", {"index.html": b"123456"})

    with pytest.raises(deploy.DeploymentError, match="quota"):
        deploy.deploy_preview(
            io.BytesIO(archive),
            request("preview", archive, slug=slug),
            common,
            preview,
        )

    assert not os.path.lexists(preview.public_root / slug)
    assert not (preview.release_root / slug).exists()


def test_cleanup_removes_orphans_and_stale_staging(tmp_path: Path) -> None:
    config_path = make_config(tmp_path)
    _, _, preview = deploy.load_config(config_path)
    orphan = preview.release_root / "orphan-123456789abc"
    orphan.mkdir()
    (orphan / "file").write_text("orphan", encoding="utf-8")
    incoming = preview.release_root / ".incoming-old.tar.gz"
    incoming.write_bytes(b"old")
    extraction = preview.release_root / ".extract-old"
    extraction.mkdir()
    (extraction / "file").write_text("old", encoding="utf-8")
    old_time = time.time() - 2 * 24 * 60 * 60
    os.utime(incoming, (old_time, old_time))
    os.utime(extraction, (old_time, old_time))

    deploy.cleanup_previews(preview)

    assert not orphan.exists()
    assert not incoming.exists()
    assert not extraction.exists()


def test_forced_command_cli_activates_production(tmp_path: Path) -> None:
    config_path = make_config(tmp_path)
    _, production, _ = deploy.load_config(config_path)
    archive = make_archive(tmp_path / "site.tar.gz", {"index.html": b"cli"})
    deployment_request = request("production", archive)
    command = (
        f"deploy {deployment_request.commit} {deployment_request.digest} "
        f"{deployment_request.size}"
    )
    environment = os.environ.copy()
    environment["SSH_ORIGINAL_COMMAND"] = command

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT_DIR / "deploy_site_archive.py",
            "--config",
            config_path,
            "production",
        ],
        input=archive,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr.decode()
    assert b"Activated production release" in result.stdout
    assert (production.current_link / "index.html").read_bytes() == b"cli"
