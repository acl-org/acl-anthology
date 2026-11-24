#! /usr/bin/env python3
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

"""
Used to add ingested DOIs into the Anthology XML.
Does not actually assign DOIs (separate script: generate_crossref_doi_metadata.py),
but simply adds to the XML, after checking that the DOI resolver recognizes it.
Resolver redirects count as success, regardless of the landing page's availability.

Accepts either volume IDs or event IDs (auto-detected by format):

    python3 bin/add_dois.py 2024.emnlp-main 2024.emnlp-long
    python3 bin/add_dois.py emnlp-2024
    python3 bin/add_dois.py P19-1 P19-2 P19-3 P19-4 W19-32

For events, all colocated volumes are resolved automatically.
Use --prefix v1/ for legacy DOIs of the form 10.18653/v1/<Anthology ID>.
Full DOI prefixes (e.g., --prefix 10.18653/v1/) are also accepted.

Modifies the XML.  Warns if DOIs already present.  Use -f to force.
Failed checks are retried up to five times with exponential backoff and respect
Retry-After headers. Failures are listed in red at the end; the script exits with
status 1 if any remain. Successful additions are still saved.
"""

import logging
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from time import sleep

import requests

# Allow importing sibling scripts from bin/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acl_anthology import Anthology
from acl_anthology.utils.logging import setup_rich_logging

from generate_crossref_doi_metadata import resolve_inputs, DOI_PREFIX

log = logging.getLogger(__name__)

# Constants
DOI_URL_PREFIX = "https://doi.org/"
MAX_ATTEMPTS = 5


def test_url_code(url):
    """Check the resolver without depending on the redirected website."""
    headers = {"user-agent": "acl-anthology/0.0.1"}
    return requests.head(url, headers=headers, allow_redirects=False, timeout=30)


def retry_delay(response: requests.Response | None, attempt: int) -> float:
    """Return exponential backoff, respecting Retry-After seconds or HTTP dates."""
    delay = 2**attempt
    if response is None:
        return delay
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return delay
    try:
        seconds = float(int(retry_after))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(retry_after)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            seconds = (retry_at - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            log.warning("Invalid Retry-After header %r; using backoff", retry_after)
            return delay
    return max(delay, seconds)


def add_doi_to_item(
    item,
    anth_id,
    doi_prefix=DOI_PREFIX,
    force=False,
    failures: dict[str, str] | None = None,
):
    """Check that the DOI resolves and set it on the item (paper or volume).

    Args:
        item: A Paper or Volume object from the acl_anthology library.
        anth_id: The full Anthology ID used to construct the DOI.
        doi_prefix: A suffix under 10.18653/ (e.g., "v1/") or a full DOI prefix.
        force: Whether to overwrite existing DOIs.
        failures: Optional mapping of failed DOI URLs to their last error.

    Returns:
        True if the DOI was added, False otherwise.
    """
    if not doi_prefix.startswith("10."):
        doi_prefix = f"{DOI_PREFIX}{doi_prefix}"
    new_doi = f"{doi_prefix}{anth_id}"

    if item.doi is not None:
        if force:
            log.warning(
                "[%s] Overwriting existing DOI %s with %s",
                anth_id,
                item.doi,
                new_doi,
            )
        else:
            return False

    doi_url = f"{DOI_URL_PREFIX}{new_doi}"
    for attempt in range(MAX_ATTEMPTS):
        result = None
        try:
            result = test_url_code(doi_url)
        except requests.RequestException as exc:
            reason = str(exc) or type(exc).__name__
        else:
            if result.status_code == 200 or (
                result.status_code in (301, 302, 303, 307, 308)
                and result.headers.get("Location")
            ):
                log.info("Adding DOI %s", new_doi)
                item.doi = new_doi
                return True
            reason = f"HTTP {result.status_code}"
            if result.status_code in (301, 302, 303, 307, 308):
                reason += " (redirect without a Location header)"

        log.warning(
            "DOI check failed for %s (attempt %d/%d): %s",
            doi_url,
            attempt + 1,
            MAX_ATTEMPTS,
            reason,
        )
        if attempt < MAX_ATTEMPTS - 1:
            pause_for = retry_delay(result, attempt)
            log.info("Retrying in %g seconds", pause_for)
            sleep(pause_for)

    log.error("Couldn't add DOI for %s: %s", doi_url, reason)
    if failures is not None:
        failures[doi_url] = reason
    return False


def process_volume(
    anthology,
    full_volume_id,
    doi_prefix=DOI_PREFIX,
    force=False,
    failures: dict[str, str] | None = None,
):
    """Process a single volume, adding DOIs to it and all its papers.

    If supplied, failures collects failed volume and paper DOI URLs and errors.

    Returns:
        The number of DOIs added.
    """
    volume = anthology.get_volume(full_volume_id)
    if volume is None:
        log.error("Volume %s not found in the Anthology", full_volume_id)
        sys.exit(1)

    log.info("Attempting to add DOIs for %s", full_volume_id)
    log.info('Found volume "%s"', volume.title)

    num_added = 0

    # Add volume-level DOI
    added = add_doi_to_item(volume, full_volume_id, doi_prefix, force, failures=failures)
    num_added += added

    # Add DOIs for all papers (including frontmatter)
    for paper in volume.papers():
        added = add_doi_to_item(
            paper, paper.full_id, doi_prefix, force, failures=failures
        )
        if added:
            num_added += 1
            sleep(0.1)

    # Save the collection
    collection = volume.parent
    collection.save()
    log.info("Added %d DOIs to the XML for collection %s", num_added, collection.id)

    return num_added


def main(args):
    setup_rich_logging()
    anthology = Anthology.from_within_repo(verbose=False)
    volume_ids = resolve_inputs(anthology, args.identifiers)

    failures: dict[str, str] = {}
    num_added = 0
    for volume_id in volume_ids:
        num_added += process_volume(
            anthology,
            volume_id,
            doi_prefix=args.prefix,
            force=args.force,
            failures=failures,
        )

    log.info("Finished adding DOIs: %d added, %d failed", num_added, len(failures))
    if failures:
        log.error(
            "[bold red]%d DOI(s) failed:[/bold red]",
            len(failures),
            extra={"markup": True, "highlighter": None},
        )
        for doi_url, reason in failures.items():
            log.error("  %s: %s", doi_url, reason)
        return 1
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Add DOIs to Anthology XML after verifying they resolve."
    )
    parser.add_argument(
        "identifiers",
        nargs="+",
        help="Volume IDs (e.g., 2024.emnlp-main, W10-17) or event IDs (e.g., emnlp-2024, naacl-2012)",
    )
    parser.add_argument(
        "--prefix",
        "-p",
        default=DOI_PREFIX,
        help=f"DOI prefix suffix (e.g., v1/) or full DOI prefix (default: {DOI_PREFIX})",
    )
    parser.add_argument(
        "--force",
        "-f",
        help="Force overwrite of existing DOI information",
        action="store_true",
    )
    args = parser.parse_args()

    sys.exit(main(args))
