#!/usr/bin/env python3
"""Summarize how many people share each name in the ACL Anthology."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
from typing import Iterable, Mapping


def _ensure_acl_anthology_on_path() -> None:
    """Allow running from a repo checkout without installing the package."""

    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        candidate = parent / "acl_anthology"
        if candidate.is_dir():
            project_root = parent
            break
    else:  # pragma: no cover
        return

    python_dir = project_root / "python"
    for path in (python_dir, project_root):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


try:  # pragma: no cover - import guard only runs outside packaged installs
    from acl_anthology import Anthology
    from acl_anthology.people import Name
except ModuleNotFoundError:  # pragma: no cover - fallback for repo checkouts
    _ensure_acl_anthology_on_path()
    from acl_anthology import Anthology
    from acl_anthology.people import Name


def _candidate_datadirs() -> Iterable[Path]:
    """Yield plausible data directories without assuming the CWD."""
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        yield parent / "data"
    yield Path.cwd() / "data"


def _resolve_datadir(cli_value: str | None) -> Path:
    if cli_value is not None:
        candidate = Path(cli_value).expanduser().resolve()
        if (candidate / "xml").is_dir():
            return candidate
        raise SystemExit(
            f"{candidate} does not look like an Anthology data directory (missing xml/)."
        )

    for candidate in _candidate_datadirs():
        if (candidate / "xml").is_dir():
            return candidate

    raise SystemExit(
        "Unable to locate the Anthology data directory. Pass --datadir or --repo-url."
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Iterate over all names in the ACL Anthology and show how many distinct "
            "people share each name."
        )
    )
    parser.add_argument(
        "--datadir",
        help=(
            "Path to the Anthology data folder (the one containing xml/). "
            "If omitted, the script attempts to infer it from its location."
        ),
    )
    parser.add_argument(
        "--repo-url",
        help=(
            "If supplied, clone/pull the Anthology data from this Git URL before running."
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=0,
        help="Number of most ambiguous names to list explicitly (default: 25).",
    )
    parser.add_argument(
        "--min-shared",
        type=int,
        default=1,
        help="Only list names shared by at least this many people (default: 2).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable progress bars emitted by the loader.",
    )
    return parser.parse_args()


def _load_anthology(args: argparse.Namespace) -> Anthology:
    verbose = not args.quiet
    if args.repo_url:
        return Anthology.from_repo(repo_url=args.repo_url, verbose=verbose)
    datadir = _resolve_datadir(args.datadir)
    return Anthology(datadir=datadir, verbose=verbose)


def _print_histogram(histogram: Counter[int]) -> None:
    if not histogram:
        print("No names found.")
        return

    max_names = max(histogram.values())
    scale = max(max_names // 50, 1)  # keep bars readable in plain text
    print("People sharing\tName count\tHistogram")
    for shared_by in sorted(histogram):
        name_count = histogram[shared_by]
        bar = "#" * max(name_count // scale, 1)
        print(f"{shared_by:>13}\t{name_count:>9}\t{bar}")


def _print_top_names(
    name_index: Mapping[Name, list[str]], min_shared: int, top_n: int
) -> None:
    shared_names = [
        (name, len(person_ids))
        for name, person_ids in name_index.items()
        if len(person_ids) >= min_shared
    ]
    shared_names.sort(key=lambda item: (-item[1], item[0].as_last_first()))

    if not shared_names:
        print(
            f"No names are shared by at least {min_shared} people; try lowering --min-shared."
        )
        return

    limit = min(top_n, len(shared_names)) if top_n > 0 else len(shared_names)
    print(f"\nTop {limit} names shared by >= {min_shared} people:")
    for name, count in shared_names[:limit]:
        print(f"  {name.as_last_first():<40} {count}")


def main() -> None:
    args = _parse_args()
    anthology = _load_anthology(args)

    # Building the person index parses the entire Anthology once.
    anthology.people.load()
    name_index = anthology.people.by_name

    histogram = Counter(len(person_ids) for person_ids in name_index.values())
    _print_histogram(histogram)
    _print_top_names(name_index, args.min_shared, args.top)


if __name__ == "__main__":
    main()
