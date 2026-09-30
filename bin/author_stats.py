#!/usr/bin/env python3
"""Compute author metrics and cache monthly snapshots outside the site build."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import TypedDict

from acl_anthology import Anthology, config
from omegaconf import OmegaConf

START = date(2026, 2, 1)
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "hugo/assets/data/author-history.json"
SCHEMA_VERSION = 3
CATEGORY_COUNT = 4


class YearCounts(TypedDict):
    year: int
    authorships: list[int]
    authors: list[int]


class AuthorStats(TypedDict):
    years: list[YearCounts]
    totals: list[int]


def compute_authorship_stats(
    anthology: Anthology, *, legacy: bool = False
) -> AuthorStats:
    """Count namespec occurrences and distinct people, excluding editors/deletions.

    Arrays are ordered: verified with/without ORCID, unverified with
    OpenReview only, unverified without either ID.
    Year 0 is a separately deduplicated pre-2020 group. Database totals
    include every person, including editor-only pages.

    Legacy explicit people were defined in name_variants.yaml; their ORCIDs
    lived on namespecs. Snapshots use their own library's name resolution.
    """
    anthology.load_all()
    orcid_ids: set[str] = set()
    openreview_ids: set[str] = set()
    for volume in anthology.volumes():
        for spec in volume.editors:
            if legacy and spec.orcid:
                orcid_ids.add(anthology.people.get_by_namespec(spec).id)
            if getattr(spec, "openreview", None):
                openreview_ids.add(anthology.people.get_by_namespec(spec).id)
    for paper in anthology.papers():
        for spec in (*paper.authors, *paper.editors):
            if legacy and spec.orcid:
                orcid_ids.add(anthology.people.get_by_namespec(spec).id)
            if getattr(spec, "openreview", None):
                openreview_ids.add(anthology.people.get_by_namespec(spec).id)
    if not legacy:
        from acl_anthology.utils.ids import is_verified_person_id

    categories = {}
    for person in anthology.people.values():
        verified = person.is_explicit if legacy else is_verified_person_id(person.id)
        has_orcid = person.id in orcid_ids if legacy else bool(person.orcid)
        if has_orcid and not verified:
            raise ValueError(f"Unverified person {person.id} has an ORCID")
        categories[person.id] = (
            (0 if has_orcid else 1)
            if verified
            else (2 if person.id in openreview_ids else 3)
        )

    authorships: dict[int, Counter[int]] = defaultdict(Counter)
    authors: dict[int, set[str]] = defaultdict(set)
    for paper in anthology.papers():
        if paper.is_frontmatter or paper.is_deleted:
            continue
        if not paper.year.isdigit():
            raise ValueError(f"{paper.full_id}: invalid publication year {paper.year!r}")
        year = int(paper.year)
        for spec in paper.authors:
            person_id = anthology.people.get_by_namespec(spec).id
            for group in (year, 0) if year < 2020 else (year,):
                authorships[group][categories[person_id]] += 1
                authors[group].add(person_id)
    years: list[YearCounts] = []
    for year in sorted(authorships):
        unique = Counter(categories[person_id] for person_id in authors[year])
        years.append(
            {
                "year": year,
                "authorships": [authorships[year][i] for i in range(CATEGORY_COUNT)],
                "authors": [unique[i] for i in range(CATEGORY_COUNT)],
            }
        )
    totals = Counter(categories.values())
    return {"years": years, "totals": [totals[i] for i in range(CATEGORY_COUNT)]}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def month_starts(through: date) -> list[date]:
    if through < START:
        raise ValueError("Checkpoints start in February 2026")
    return [
        date(year, month, 1)
        for year in range(START.year, through.year + 1)
        for month in range(1, 13)
        if START <= date(year, month, 1) <= through
    ]


def checkpoint_revision(repo: Path, ref: str, checkpoint: date) -> str:
    """Select the newest first-parent ancestor strictly before midnight UTC."""
    cutoff = int(
        datetime.combine(checkpoint, datetime.min.time(), timezone.utc).timestamp()
    )
    # Inspect all ancestors: commit dates need not be monotonic along the branch.
    for line in git(repo, "log", "--first-parent", "--format=%H %ct", ref).splitlines():
        revision, timestamp = line.split()
        if int(timestamp) < cutoff:
            return revision
    raise ValueError(f"No commit before {checkpoint}; fetch the full history")


def compute_checkpoint(repo: Path, revision: str) -> dict:
    """Use the checkpoint's public library API to preserve historical resolution."""
    with tempfile.TemporaryDirectory(prefix="anthology-author-stats-") as tmp:
        directory = Path(tmp)
        archive = directory / "snapshot.tar"
        with archive.open("wb") as stream:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "archive",
                    revision,
                    "data",
                    "python/acl_anthology",
                ],
                stdout=stream,
                check=True,
            )
        subprocess.run(["tar", "-xf", str(archive), "-C", tmp], check=True)
        legacy = not (directory / "data/json/people.json").exists()
        output = directory / "counts.json"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(directory / "python")
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--snapshot-data",
                str(directory / "data"),
                "--output",
                str(output),
                *(["--legacy"] if legacy else []),
            ],
            env=env,
            check=True,
        )
        return {
            **json.loads(output.read_text()),
            "identity_model": "legacy" if legacy else "verified",
        }


def update_history(repo: Path, ref: str, through: date, output: Path) -> None:
    if git(repo, "rev-parse", "--is-shallow-repository") == "true":
        raise ValueError(
            "Historical metrics require a full clone; run git fetch --unshallow"
        )
    if through > datetime.now(timezone.utc).date():
        raise ValueError("Cannot compute checkpoints in the future")
    existing = (
        json.loads(output.read_text())
        if output.exists()
        else {"schema_version": SCHEMA_VERSION, "checkpoints": []}
    )
    if existing["schema_version"] not in (1, 2, SCHEMA_VERSION):
        raise ValueError("Unsupported author-history schema version")
    cached = (
        {entry["date"]: entry for entry in existing["checkpoints"]}
        if existing["schema_version"] == SCHEMA_VERSION
        else {}
    )
    for checkpoint in month_starts(through):
        revision = checkpoint_revision(repo, ref, checkpoint)
        key = checkpoint.isoformat()
        if key in cached and cached[key]["revision"] == revision:
            continue
        print(f"Computing {key} at {revision}", flush=True)
        cached[key] = {
            "date": key,
            "revision": revision,
            **compute_checkpoint(repo, revision),
        }
        # Persist each successful checkpoint so a failed backfill can resume.
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "checkpoints": [cached[key] for key in sorted(cached)],
                },
                indent=2,
            )
            + "\n"
        )
        temporary.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--ref", default="origin/master")
    parser.add_argument(
        "--through", type=date.fromisoformat, default=datetime.now(timezone.utc).date()
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--snapshot-data", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--legacy", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    OmegaConf.resolve(config)
    if args.snapshot_data:
        stats = compute_authorship_stats(
            Anthology(args.snapshot_data), legacy=args.legacy
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(stats) + "\n")
    else:
        update_history(args.repo, args.ref, args.through, args.output)


if __name__ == "__main__":
    main()
