#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Nathan Schneider <nathan.schneider@georgetown.edu>
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

"""Add resource links for GitHub/Zenodo URLs marked up in paper abstracts.
These are extracted `<url>` tags in the abstract, and `<url type="resource">`
element is added to the paper (unless already present).
URLs are normalized and must follow the format of a GitHub repo or Zenodo resource.
For example:
    `https://github.com/the-user/the-repo-name`
    `https://zenodo.org/records/11111111`
    `https://doi.org/10.5281/zenodo.11111111`

Usage:
  add_resource_links.py [COLLECTION_ID ...]

  If no collection IDs (e.g. 2025.acl) are given, all collections are processed.

Arguments:
  COLLECTION_ID ...     IDs of one or more collections to scan for new resource links.
"""

from docopt import docopt
import logging as log
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

from acl_anthology import Anthology
from acl_anthology.files import RESOURCE_URL_PREFIXES, URLReference
from acl_anthology.text import MarkupText
from acl_anthology.utils.logging import setup_rich_logging

sys.path.insert(0, str(Path(__file__).resolve().parent))
from correct.convert_markdown_in_abstracts import split_url_trailing  # noqa: E402

RESOURCE_TYPE = "resource"

# GitHub owners that are placeholders for anonymized submissions
PLACEHOLDER_OWNERS = {
    "anon",
    "anonymous",
    "anonymized",
    "anonymous-author",
    "anonymous-authors",
    "anonymoususer",
    "xxx",
    "xxxx",
    "username",
    "user",
}

GITHUB_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9-]+)"
    r"(?:/(?P<repo>[A-Za-z0-9_.-]+)(?P<rest>[/#?]\S*)?)?/?",
    re.IGNORECASE,
)
LOOKS_LIKE_RESOURCE_RE = re.compile(
    r"(?<![\w.-])github\.com/|zenodo\.org/|10\.5281/zenodo", re.IGNORECASE
)
ZENODO_RE = re.compile(
    r"(?:https?://)?(?:www\.)?zenodo\.org/(?P<path>(?:records?|doi|communities)/\S+)",
    re.IGNORECASE,
)
ZENODO_DOI_RE = re.compile(
    r"(?:https?://)?(?:dx\.)?doi\.org/10\.5281/zenodo\.(?P<id>\d+)/?", re.IGNORECASE
)

NEEDS_CLEANUP = "needs cleanup (run correct/convert_markdown_in_abstracts.py)"
UNRECOGNIZED = "unrecognized link format (fix abstract manually)"


def resource_url(text: str) -> tuple[Optional[str], Optional[str]]:
    """Interprets the contents of a `<url>` tag as a resource link if it points to GitHub or Zenodo.
    If the link does not follow the expected format (e.g. GitHub user rather than repo,
    or a placeholder with "anonymous" etc.), return the reason it was skipped.

    Returns:
        A tuple `(url, None)` with the normalized URL if `text` is a resource link; `(None, reason)` if it looks like one but is skipped for the given reason; or `(None, None)` if it is not a resource link.
    """
    text, trailing = split_url_trailing(text.strip())
    if m := GITHUB_RE.fullmatch(text):
        if m.group("owner").lower() in PLACEHOLDER_OWNERS:
            return None, "placeholder owner"
        if trailing:
            return None, NEEDS_CLEANUP
        if (repo := m.group("repo")) is None:
            return None, "no repository"
        if repo.lower().endswith(".git"):
            repo = repo[:-4]
        url = f"https://github.com/{m.group('owner')}/{repo}{m.group('rest') or ''}"
    elif m := ZENODO_RE.fullmatch(text):
        if trailing:
            return None, NEEDS_CLEANUP
        url = f"https://zenodo.org/{m.group('path')}"
    elif m := ZENODO_DOI_RE.fullmatch(text):
        if trailing:
            return None, NEEDS_CLEANUP
        url = f"https://doi.org/10.5281/zenodo.{m.group('id')}"
    elif LOOKS_LIKE_RESOURCE_RE.search(text):
        return None, UNRECOGNIZED
    else:
        return None, None
    url = url.rstrip("/")
    if not url.startswith(RESOURCE_URL_PREFIXES):  # sanity check; can't happen
        return None, "not an allowed resource URL"
    return url, None


def find_resource_urls(
    text: MarkupText,
) -> tuple[list[str], list[tuple[str, str]]]:
    """Finds resource links among the `<url>` tags in a piece of markup text.

    Returns:
        A tuple `(urls, skipped)`, where `urls` is a list of normalized, deduplicated resource URLs in order of appearance, and `skipped` is a list of `(url_text, reason)` tuples for links that look like resource links but were skipped.
    """
    urls: list[str] = []
    skipped: list[tuple[str, str]] = []
    for elem in text.to_xml().iter("url"):
        link_text = "".join(elem.itertext())
        url, reason = resource_url(link_text)
        if reason is not None:
            skipped.append((link_text, reason))
        elif url is not None and normalize_key(url) not in map(normalize_key, urls):
            urls.append(url)
    return urls, skipped


def normalize_key(url: str) -> str:
    """Key for comparing URLs: case-insensitive, ignoring a trailing slash."""
    return url.lower().rstrip("/")


def add_resource_links(collection_ids: list[str]) -> None:
    anthology = Anthology.from_within_repo()

    stats: Counter = Counter()
    collections = list(map(anthology.collections.get, collection_ids)) or [anthology]
    for collection in collections:
        if not collection:
            raise ValueError(f"Invalid collection ID")
        for paper in collection.papers():
            if paper.abstract is None:
                continue
            urls, skipped = find_resource_urls(paper.abstract)
            for link_text, reason in skipped:
                stats["skipped"] += 1
                level = (
                    log.WARNING if reason in (NEEDS_CLEANUP, UNRECOGNIZED) else log.DEBUG
                )
                log.log(level, f"{paper.full_id}: skipped {link_text}: {reason}")

            existing = {
                normalize_key(ref.name)
                for type_, ref in paper.urls
                if type_ == RESOURCE_TYPE
            }
            new = [url for url in urls if normalize_key(url) not in existing]
            stats["already present"] += len(urls) - len(new)
            if not new:
                continue
            for url in new:
                log.debug(f"{paper.full_id}: adding {url}")
            stats["papers modified"] += 1
            stats["links added"] += len(new)
            if len(new) > 1:
                stats["papers with multiple links"] += 1
            paper.urls = paper.urls + tuple(
                (RESOURCE_TYPE, URLReference(url)) for url in new
            )

    log.info(
        f"Added {stats['links added']} links to {stats['papers modified']} papers"
        f" ({stats['papers with multiple links']} with multiple links);"
        f" {stats['already present']} already present, {stats['skipped']} skipped"
    )
    anthology.save_all()


if __name__ == "__main__":
    assert __doc__
    args = docopt(__doc__)

    setup_rich_logging(level=log.INFO)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)

    add_resource_links(args['COLLECTION_ID'])
