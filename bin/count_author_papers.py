#!/usr/bin/env python3

"""
Count papers per author for an Anthology event.

The event must be specified explicitly. By default, this includes both the
event's own collection volumes and the volumes listed as colocated with the
event:

    ./bin/count_author_papers.py --event acl-2026 --output build/acl-2026-author-paper-counts.tsv

Use --main-only to restrict the count to the event's collection volumes, or
--colocated-only to count only the colocated volumes.

Use --prolific-threshold N to additionally report how many papers have at least
one author with more than N papers in the counted set.
"""

import argparse
import csv
import sys
import warnings

from collections import Counter
from pathlib import Path
from typing import Iterable, NamedTuple

from acl_anthology import Anthology
from acl_anthology.collections import Volume
from acl_anthology.exceptions import NameSpecResolutionWarning


class AuthorCount(NamedTuple):
    count: int
    author: str
    person_id: str


class CountResult(NamedTuple):
    rows: list[AuthorCount]
    paper_count: int
    author_ids_by_paper: list[frozenset[str]]


def event_volumes(
    anthology: Anthology,
    event_id: str,
    include_main: bool = True,
    include_colocated: bool = True,
) -> list[Volume]:
    """Returns the event collection volumes and/or colocated volumes."""
    event = anthology.get_event(event_id)
    if event is None:
        raise ValueError(f"Event {event_id} not found in the Anthology.")

    volumes: list[Volume] = []
    seen: set[tuple[str, str, str | None]] = set()

    def add_volumes(items: Iterable[Volume]) -> None:
        for volume in items:
            if volume.full_id_tuple in seen:
                continue
            volumes.append(volume)
            seen.add(volume.full_id_tuple)

    if include_main:
        add_volumes(event.collection.volumes())
    if include_colocated:
        add_volumes(event.volumes())

    return volumes


def count_author_papers(volumes: Iterable[Volume]) -> CountResult:
    """Counts non-frontmatter, non-deleted papers per resolved author identity."""
    counts: Counter[str] = Counter()
    people_by_id = {}
    paper_count = 0
    author_ids_by_paper: list[frozenset[str]] = []

    for volume in volumes:
        for paper in volume.papers():
            if paper.is_frontmatter or paper.is_deleted:
                continue
            paper_count += 1
            authors_on_paper = {}
            for author_spec in paper.authors:
                person = author_spec.resolve()
                authors_on_paper[person.id] = person
            author_ids_by_paper.append(frozenset(authors_on_paper))
            for person_id, person in authors_on_paper.items():
                counts[person_id] += 1
                people_by_id[person_id] = person

    rows = [
        AuthorCount(
            count,
            people_by_id[person_id].canonical_name.as_first_last(),
            person_id,
        )
        for person_id, count in counts.items()
    ]
    rows.sort(key=lambda row: (-row.count, row.author.casefold(), row.person_id))
    return CountResult(rows, paper_count, author_ids_by_paper)


def count_papers_with_prolific_authors(
    rows: Iterable[AuthorCount],
    author_ids_by_paper: Iterable[frozenset[str]],
    threshold: int,
) -> tuple[int, int]:
    """Counts authors over threshold and papers containing at least one of them."""
    prolific_author_ids = {
        row.person_id for row in rows if row.count > threshold
    }
    paper_count = sum(
        1 for author_ids in author_ids_by_paper if author_ids & prolific_author_ids
    )
    return len(prolific_author_ids), paper_count


def write_tsv(rows: Iterable[AuthorCount], output: Path | None) -> None:
    stream = output.open("w", encoding="utf-8", newline="") if output else sys.stdout
    try:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("count", "author", "person_id"))
        for row in rows:
            writer.writerow(row)
    finally:
        if output:
            stream.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--event",
        required=True,
        help="Event ID to count (e.g. acl-2026).",
    )
    parser.add_argument(
        "--datadir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data",
        help="Path to the Anthology data directory. Default: %(default)s.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write TSV output to this path instead of STDOUT.",
    )
    parser.add_argument(
        "--main-only",
        action="store_true",
        help="Count only the event's own collection volumes.",
    )
    parser.add_argument(
        "--colocated-only",
        action="store_true",
        help="Count only volumes listed as colocated with the event.",
    )
    parser.add_argument(
        "--prolific-threshold",
        "-n",
        type=int,
        metavar="N",
        help="Report papers with at least one author who has more than N papers in the counted set.",
    )
    parser.add_argument(
        "--show-resolution-warnings",
        action="store_true",
        help="Show warnings emitted while resolving author identities.",
    )
    args = parser.parse_args()

    if args.main_only and args.colocated_only:
        parser.error("--main-only and --colocated-only cannot be used together")
    if args.prolific_threshold is not None and args.prolific_threshold < 0:
        parser.error("--prolific-threshold must be non-negative")

    if not args.show_resolution_warnings:
        warnings.filterwarnings("ignore", category=NameSpecResolutionWarning)

    include_main = not args.colocated_only
    include_colocated = not args.main_only

    anthology = Anthology(datadir=args.datadir, verbose=False)
    volumes = event_volumes(
        anthology,
        args.event,
        include_main=include_main,
        include_colocated=include_colocated,
    )
    result = count_author_papers(volumes)
    write_tsv(result.rows, args.output)

    if args.output:
        print(f"Wrote: {args.output}", file=sys.stderr)
        print(f"Volumes: {len(volumes)}", file=sys.stderr)
        print(f"Papers counted: {result.paper_count}", file=sys.stderr)
        print(f"Authors: {len(result.rows)}", file=sys.stderr)

    if args.prolific_threshold is not None:
        prolific_author_count, prolific_paper_count = count_papers_with_prolific_authors(
            result.rows,
            result.author_ids_by_paper,
            args.prolific_threshold,
        )
        print(
            f"Overly-prolific threshold: > {args.prolific_threshold} papers",
            file=sys.stderr,
        )
        print(
            f"Overly-prolific authors: {prolific_author_count}",
            file=sys.stderr,
        )
        print(
            f"Papers with overly-prolific author: {prolific_paper_count}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()