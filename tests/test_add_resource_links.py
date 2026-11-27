"""Tests for bin/add_resource_links.py."""

import pytest
from lxml import etree

from acl_anthology.text import MarkupText
from bin.add_resource_links import (
    NEEDS_CLEANUP,
    UNRECOGNIZED,
    find_resource_urls,
    resource_url,
)


@pytest.mark.parametrize(
    "text, expected",
    (
        (
            "https://github.com/acl-org/acl-anthology",
            "https://github.com/acl-org/acl-anthology",
        ),
        # Normalization: scheme, www, .git, trailing slash
        ("github.com/foo/bar-baz", "https://github.com/foo/bar-baz"),
        ("http://www.github.com/foo/bar", "https://github.com/foo/bar"),
        ("https://github.com/foo/bar.git", "https://github.com/foo/bar"),
        ("https://github.com/foo/bar/", "https://github.com/foo/bar"),
        ("https://github.com/foo/bar/tree/main/", "https://github.com/foo/bar/tree/main"),
        ("https://github.com/foo/bar#2.0", "https://github.com/foo/bar#2.0"),
        # Dots and all-caps suffixes in repository names are kept
        ("https://github.com/foo/bert.cpp", "https://github.com/foo/bert.cpp"),
        ("https://github.com/foo/NotAI.AI", "https://github.com/foo/NotAI.AI"),
        # Zenodo records and DOIs
        ("https://zenodo.org/records/13932202", "https://zenodo.org/records/13932202"),
        (
            "https://doi.org/10.5281/zenodo.3779901",
            "https://doi.org/10.5281/zenodo.3779901",
        ),
        ("http://dx.doi.org/10.5281/zenodo.42", "https://doi.org/10.5281/zenodo.42"),
    ),
)
def test_resource_url(text, expected):
    assert resource_url(text) == (expected, None)


@pytest.mark.parametrize(
    "text",
    (
        "https://foo.github.io/bar",
        "https://gist.github.com/foo/123",
        "https://doi.org/10.18653/v1/2020.acl-main.1",
        "https://example.com",
    ),
)
def test_resource_url_not_a_resource(text):
    assert resource_url(text) == (None, None)


@pytest.mark.parametrize(
    "text, reason",
    (
        ("https://github.com/anonymous/repo", "placeholder owner"),
        ("https://github.com/Autodive", "no repository"),
        ("https://github.com/foo/bar.", NEEDS_CLEANUP),
        ("https://github.com/foo/bar)", NEEDS_CLEANUP),
        ("https://github.com/bytedance/pasa.Demo", NEEDS_CLEANUP),
        ("https://zenodo.org/records/1;", NEEDS_CLEANUP),
        # Must be exactly one well-formed link
        ("https://github.com/a/bhttps://github.com/a/b", UNRECOGNIZED),
        ("https://github.com/a/b>GitHub", UNRECOGNIZED),
        ("https://github.com/a/b and more", UNRECOGNIZED),
    ),
)
def test_resource_url_skipped(text, reason):
    assert resource_url(text) == (None, reason)


@pytest.mark.parametrize(
    "xml, expected",
    (
        # Only <url> (and <a href>) tags count, including nested in other markup
        (
            "<abstract>Code: <i><url>https://github.com/a/b</url></i>; also "
            "https://github.com/c/d and <url>https://example.com</url>.</abstract>",
            ["https://github.com/a/b"],
        ),
        # <a href> links count too (the href, not the link text); order is kept
        (
            '<abstract><a href="https://github.com/a/b">our code</a>, '
            "<url>https://zenodo.org/records/1</url> and "
            '<a href="https://github.com/c/d">https://github.com/x/y</a> '
            '<a href="https://example.com">site</a></abstract>',
            [
                "https://github.com/a/b",
                "https://zenodo.org/records/1",
                "https://github.com/c/d",
            ],
        ),
        # Duplicates are merged; order of appearance is kept
        (
            "<abstract><url>https://github.com/a/b</url> "
            "<url>https://doi.org/10.5281/zenodo.7</url> "
            "<url>https://github.com/A/B/</url></abstract>",
            ["https://github.com/a/b", "https://doi.org/10.5281/zenodo.7"],
        ),
        ("<abstract>Plain text only: https://github.com/a/b.</abstract>", []),
        ("<abstract>No markup at all.</abstract>", []),
    ),
)
def test_find_resource_urls(xml, expected):
    abstract = MarkupText.from_xml(etree.fromstring(xml))
    urls, _ = find_resource_urls(abstract)
    assert urls == expected


def test_find_resource_urls_reports_skipped():
    abstract = MarkupText.from_xml(
        etree.fromstring("<abstract><url>https://github.com/a/b.Demo:</url></abstract>")
    )
    assert find_resource_urls(abstract) == (
        [],
        [("https://github.com/a/b.Demo:", NEEDS_CLEANUP)],
    )


def test_find_resource_urls_reports_skipped_href():
    abstract = MarkupText.from_xml(
        etree.fromstring(
            '<abstract><a href="https://github.com/someorg">org</a></abstract>'
        )
    )
    assert find_resource_urls(abstract) == (
        [],
        [("https://github.com/someorg", "no repository")],
    )
