#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Matt Post
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Benchmark the generated browser search indexes.

The benchmark mirrors the normalization, filtering, and ranking performed by
the author-directory JavaScript. It reports timings without enforcing machine-
specific performance thresholds.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import statistics
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable

DEFAULT_AUTHOR_QUERIES = (
    "matt post",
    "zhang",
    "éva",
    "0000-0002",
)
DEFAULT_PAPER_QUERIES = (
    "attention is all you need",
    "machine translation",
    "devlin bert pre-training",
    "matt post translation",
)


def normalize(value: str) -> str:
    """Normalize text like the browser search implementation."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    ).casefold()


def bucket_for(query: str) -> str:
    """Return the generated index bucket used for a query."""
    for char in normalize(query):
        if char.isalnum() or char == "_":
            return char if "a" <= char <= "z" else "other"
    return "other"


def paper_buckets_for(token: str, available: set[str]) -> list[str]:
    """Return title buckets used for one browser query token."""
    word = next(iter(re.findall(r"\w+", normalize(token))), "")
    if not word:
        return []
    if len(word) < 2:
        return [word] if word in available else []
    prefix = word[:3]
    if not prefix[0].isascii() or not prefix[0].isalnum():
        return ["other"] if "other" in available else []
    if len(prefix) == 2:
        return sorted(bucket for bucket in available if bucket.startswith(prefix))
    return [prefix] if prefix in available else []


def prepare_author_rows(rows: list[list[Any]]) -> list[dict[str, Any]]:
    """Precompute normalized author fields as the browser does after loading."""
    return [
        {
            "row": row,
            "name": normalize(row[0]),
            "searchable": normalize(
                " ".join(str(value) for value in (row[0], row[3], row[4]))
            ),
        }
        for row in rows
    ]


def author_rank(entry: dict[str, Any], query: str) -> int:
    """Mirror the author-directory exact/prefix/token-prefix ranking."""
    name = entry["name"]
    if name == query:
        return 0
    if name.startswith(query):
        return 1
    if any(token.startswith(query) for token in name.split()):
        return 2
    return 3


def is_verified_author(row: list[Any]) -> bool:
    return not row[1].endswith("/unverified")


def search_authors(entries: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Search and rank prepared author entries."""
    normalized_query = normalize(query.strip())
    tokens = normalized_query.split()
    matches = [
        entry
        for entry in entries
        if all(token in entry["searchable"] for token in tokens)
    ]
    return sorted(
        matches,
        key=lambda entry: (
            author_rank(entry, normalized_query),
            -int(is_verified_author(entry["row"])),
            -entry["row"][2],
            entry["row"][0].casefold(),
        ),
    )


def prepare_paper_rows(rows: list[list[Any]]) -> list[dict[str, Any]]:
    """Precompute normalized title and author fields for paper records."""
    return [
        {
            "row": row,
            "title": normalize(row[0]),
            "authors": normalize(" ".join((row[3], row[4]))),
        }
        for row in rows
    ]


def load_paper_query_rows(
    index_dir: Path,
    buckets: list[str],
    *,
    measure_compressed_size: bool,
) -> tuple[list[list[Any]], int]:
    """Load and deduplicate all title buckets relevant to a query."""
    rows_by_id = {}
    compressed_size = 0
    for bucket in buckets:
        path = index_dir / f"{bucket}.json"
        payload = path.read_bytes()
        if measure_compressed_size:
            compressed_size += len(gzip.compress(payload, mtime=0))
        for row in json.loads(payload):
            rows_by_id[row[1]] = row
    return list(rows_by_id.values()), compressed_size


def paper_match_kind(entry: dict[str, Any], tokens: list[str]) -> str | None:
    """Classify a paper match as title-only or title/author intersection."""
    title_matches = [token in entry["title"] for token in tokens]
    author_matches = [token in entry["authors"] for token in tokens]
    if not all(
        title_match or author_match
        for title_match, author_match in zip(title_matches, author_matches)
    ):
        return None
    if all(title_matches):
        return "title"
    if any(title_matches) and any(author_matches):
        return "title+author"
    return None


def paper_rank(entry: dict[str, Any], query: str) -> int:
    """Rank exact and prefix title matches before broader/intersection matches."""
    if entry["match_kind"] == "title+author":
        return 4
    title = entry["title"]
    if title == query:
        return 0
    if title.startswith(query):
        return 1
    query_tokens = query.split()
    title_tokens = title.split()
    if all(
        any(title_token.startswith(query_token) for title_token in title_tokens)
        for query_token in query_tokens
    ):
        return 2
    return 3


def search_papers(entries: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Search paper titles, allowing queries split across title and author."""
    normalized_query = normalize(query.strip())
    tokens = normalized_query.split()
    matches = []
    for entry in entries:
        match_kind = paper_match_kind(entry, tokens)
        if match_kind is not None:
            matches.append({**entry, "match_kind": match_kind})
    return sorted(
        matches,
        key=lambda entry: (
            paper_rank(entry, normalized_query),
            -int(entry["row"][2]),
            entry["row"][0].casefold(),
            entry["row"][1],
        ),
    )


def milliseconds(samples: list[float]) -> tuple[float, float]:
    """Return median and 95th-percentile durations in milliseconds."""
    ordered = sorted(samples)
    percentile_index = min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))
    return statistics.median(ordered) * 1000, ordered[percentile_index] * 1000


def measure(operation: Callable[[], Any], iterations: int) -> tuple[float, float]:
    samples = []
    for _ in range(iterations):
        started = time.perf_counter()
        operation()
        samples.append(time.perf_counter() - started)
    return milliseconds(samples)


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def benchmark_authors(index_dir: Path, queries: tuple[str, ...], iterations: int) -> None:
    paths = sorted(index_dir.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"No author index buckets found under {index_dir}")

    raw_size = sum(path.stat().st_size for path in paths)
    gzip_size = sum(len(gzip.compress(path.read_bytes(), mtime=0)) for path in paths)
    all_rows = [row for path in paths for row in json.loads(path.read_bytes())]
    unique_records = len({row[1] for row in all_rows})

    print("Author index")
    print(f"  buckets: {len(paths)}")
    print(f"  rows: {len(all_rows):,} ({unique_records:,} unique author pages)")
    print(f"  size: {format_bytes(raw_size)} raw, {format_bytes(gzip_size)} gzip")
    print()
    print(
        "  query          bucket rows  gzip      cold p50/p95   warm p50/p95   matches  top"
    )

    for query in queries:
        path = index_dir / f"{bucket_for(query)}.json"

        def cold_search() -> list[dict[str, Any]]:
            rows = json.loads(path.read_bytes())
            return search_authors(prepare_author_rows(rows), query)

        prepared = prepare_author_rows(json.loads(path.read_bytes()))
        matches = search_authors(prepared, query)
        cold_p50, cold_p95 = measure(cold_search, max(3, iterations // 5))
        warm_p50, warm_p95 = measure(lambda: search_authors(prepared, query), iterations)
        compressed_size = len(gzip.compress(path.read_bytes(), mtime=0))
        top = matches[0]["row"][1] if matches else "-"
        print(
            f"  {query[:14]:14} {path.stem:>6} {len(prepared):>5,}  "
            f"{format_bytes(compressed_size):>8}  "
            f"{cold_p50:6.1f}/{cold_p95:<6.1f}  "
            f"{warm_p50:6.1f}/{warm_p95:<6.1f}  "
            f"{len(matches):>7,}  {top}"
        )


def benchmark_papers(index_dir: Path, queries: tuple[str, ...], iterations: int) -> None:
    paths = sorted(index_dir.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"No paper index buckets found under {index_dir}")

    raw_size = sum(path.stat().st_size for path in paths)
    gzip_size = sum(len(gzip.compress(path.read_bytes(), mtime=0)) for path in paths)
    all_rows = [row for path in paths for row in json.loads(path.read_bytes())]
    unique_records = len({row[1] for row in all_rows})
    available_buckets = {path.stem for path in paths}

    print("Paper index")
    print(f"  buckets: {len(paths)}")
    print(f"  rows: {len(all_rows):,} ({unique_records:,} unique papers)")
    print(f"  size: {format_bytes(raw_size)} raw, {format_bytes(gzip_size)} gzip")
    print()
    print(
        "  query          bucket rows  gzip      cold p50/p95   warm p50/p95   title/both  top"
    )

    for query in queries:
        buckets = sorted(
            {
                bucket
                for token in normalize(query).split()
                for bucket in paper_buckets_for(token, available_buckets)
            }
        )

        def cold_search() -> list[dict[str, Any]]:
            rows, _compressed_size = load_paper_query_rows(
                index_dir, buckets, measure_compressed_size=False
            )
            return search_papers(prepare_paper_rows(rows), query)

        rows, compressed_size = load_paper_query_rows(
            index_dir, buckets, measure_compressed_size=True
        )
        prepared = prepare_paper_rows(rows)
        matches = search_papers(prepared, query)
        cold_p50, cold_p95 = measure(cold_search, max(3, iterations // 5))
        warm_p50, warm_p95 = measure(lambda: search_papers(prepared, query), iterations)
        title_matches = sum(match["match_kind"] == "title" for match in matches)
        intersection_matches = len(matches) - title_matches
        top = matches[0]["row"][1] if matches else "-"
        print(
            f"  {query[:14]:14} {len(buckets):>6} {len(prepared):>5,}  "
            f"{format_bytes(compressed_size):>8}  "
            f"{cold_p50:6.1f}/{cold_p95:<6.1f}  "
            f"{warm_p50:6.1f}/{warm_p95:<6.1f}  "
            f"{title_matches:>5,}/{intersection_matches:<5,}  {top}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path("build/static/people/index"),
        help="Generated author-index directory (default: %(default)s)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=25,
        help="Warm query iterations (default: %(default)s)",
    )
    parser.add_argument(
        "--author-query",
        action="append",
        dest="author_queries",
        help="Author query to benchmark; may be repeated",
    )
    parser.add_argument(
        "--paper-query",
        action="append",
        dest="paper_queries",
        help="Paper query to benchmark; may be repeated",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    author_queries = tuple(args.author_queries or DEFAULT_AUTHOR_QUERIES)
    paper_queries = tuple(args.paper_queries or DEFAULT_PAPER_QUERIES)
    benchmark_authors(args.index_dir, author_queries, args.iterations)
    paper_index_dir = args.index_dir / "papers"
    if paper_index_dir.is_dir():
        print()
        benchmark_papers(paper_index_dir, paper_queries, args.iterations)


if __name__ == "__main__":
    main()
