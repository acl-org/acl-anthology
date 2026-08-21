"""Tests for the browser-search benchmark model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.benchmark_search import (
    bucket_for,
    normalize,
    paper_buckets_for,
    prepare_author_rows,
    prepare_paper_rows,
    search_authors,
    search_papers,
)


def test_author_search_normalizes_and_ranks_like_browser():
    rows = [
        ["Matt Poston", "matt-poston", 20, "", ""],
        ["Matt Post", "matt-post/unverified", 100, "", ""],
        ["Matt Post", "matt-post", 10, "0000-0002-0000-0001", "M. Post"],
        ["Éva Ács", "eva-acs", 5, "", ""],
    ]
    entries = prepare_author_rows(rows)

    assert normalize("Éva ÁCS") == "eva acs"
    assert bucket_for(" Éva") == "e"
    assert paper_buckets_for(" Éva", {"eva", "eve"}) == ["eva"]
    assert paper_buckets_for("ma", {"mac", "mat", "max"}) == [
        "mac",
        "mat",
        "max",
    ]
    assert paper_buckets_for("a", {"a", "an"}) == ["a"]
    assert [entry["row"][1] for entry in search_authors(entries, "Matt Post")] == [
        "matt-post",
        "matt-post/unverified",
        "matt-poston",
    ]
    assert search_authors(entries, "0000-0002")[0]["row"][1] == "matt-post"


def test_author_search_ranks_surface_forms_and_breaks_ties_by_id():
    rows = [
        ["Yang Liu", "yang-liu-z", 29, "", [], "", []],
        ["Yang Janet Liu", "yang-janet-liu", 29, "", ["Yang Liu"], "", []],
        ["Yang Liu (刘洋)", "yang-liu-ict", 87, "", ["刘洋"], "", ["刘洋"], "Yang Liu"],
        ["Yanghua Xiao", "yanghua-xiao", 89, "", [], "", []],
        [
            "Yang Liu (刘扬)",
            "yang-liu-icsi",
            103,
            "",
            ["Y. Liu"],
            "",
            ["刘扬"],
            "Yang Liu",
        ],
        ["Yang Liu", "yang-liu-a", 29, "", [], "", []],
    ]
    entries = prepare_author_rows(rows)

    assert [entry["row"][1] for entry in search_authors(entries, "Yang")] == [
        "yang-liu-icsi",
        "yanghua-xiao",
        "yang-liu-ict",
        "yang-janet-liu",
        "yang-liu-a",
        "yang-liu-z",
    ]
    assert [entry["row"][1] for entry in search_authors(entries, "Yang Liu")] == [
        "yang-liu-icsi",
        "yang-liu-ict",
        "yang-janet-liu",
        "yang-liu-a",
        "yang-liu-z",
    ]


def test_paper_search_distinguishes_title_and_author_intersection():
    rows = [
        [
            "Neural Machine Translation",
            "2024.test.1",
            "2024",
            "Ada Lovelace",
            "Ada Lovelace Augusta Ada King",
        ],
        [
            "Parsing Speech",
            "2023.test.2",
            "2023",
            "Grace Hopper",
            "Grace Hopper",
        ],
    ]
    entries = prepare_paper_rows(rows)

    title_matches = search_papers(entries, "neural translation")
    assert [(entry["row"][1], entry["match_kind"]) for entry in title_matches] == [
        ("2024.test.1", "title")
    ]

    intersection_matches = search_papers(entries, "ada translation")
    assert [(entry["row"][1], entry["match_kind"]) for entry in intersection_matches] == [
        ("2024.test.1", "title+author")
    ]

    assert search_papers(entries, "ada lovelace") == []
