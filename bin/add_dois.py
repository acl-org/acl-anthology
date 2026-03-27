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
but simply adds to the XML, after checking that the DOI URL exists and resolves.

Accepts either volume IDs or event IDs (auto-detected by format):

    python3 bin/add_dois.py 2024.emnlp-main 2024.emnlp-long
    python3 bin/add_dois.py emnlp-2024
    python3 bin/add_dois.py P19-1 P19-2 P19-3 P19-4 W19-32

For events, all colocated volumes are resolved automatically.

Modifies the XML.  Warns if DOIs already present.  Use -f to force.
"""

import logging
import sys
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


def test_url_code(url):
    """Test a URL with a HEAD request, returning the response."""
    headers = {"user-agent": "acl-anthology/0.0.1"}
    return requests.head(url, headers=headers, allow_redirects=True)


def add_doi_to_item(item, anth_id, doi_prefix=DOI_PREFIX, force=False):
    """Check that the DOI resolves and set it on the item (paper or volume).

    Args:
        item: A Paper or Volume object from the acl_anthology library.
        anth_id: The full Anthology ID used to construct the DOI.
        doi_prefix: The DOI prefix to use.
        force: Whether to overwrite existing DOIs.

    Returns:
        True if the DOI was added, False otherwise.
    """
    new_doi = f"{doi_prefix}{anth_id}"

    if item.doi is not None and not force:
        log.warning(
            "[%s] Cowardly refusing to overwrite existing DOI %s (use --force)",
            anth_id,
            item.doi,
        )
        return False

    doi_url = f"{DOI_URL_PREFIX}{new_doi}"
    for _ in range(3):  # retry on transient failures
        try:
            result = test_url_code(doi_url)
            if result.status_code == 200:
                log.info("Adding DOI %s", new_doi)
                item.doi = new_doi
                return True
            elif result.status_code == 429:
                pause_for = int(result.headers["Retry-After"])
                log.warning("Got 429, pausing for %d seconds", pause_for)
                sleep(pause_for + 1)
            elif result.status_code == 404:
                log.warning("Got 404")
                break
            else:
                log.warning("Other problem: %s", result)
        except Exception as e:
            log.error("%s", e)

    log.error("Couldn't add DOI for %s", doi_url)
    return False


def process_volume(anthology, full_volume_id, doi_prefix=DOI_PREFIX, force=False):
    """Process a single volume, adding DOIs to it and all its papers.

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
    added = add_doi_to_item(volume, full_volume_id, doi_prefix, force)
    num_added += added

    # Add DOIs for all papers (including frontmatter)
    for paper in volume.papers():
        added = add_doi_to_item(paper, paper.full_id, doi_prefix, force)
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

    for volume_id in volume_ids:
        process_volume(anthology, volume_id, doi_prefix=args.prefix, force=args.force)


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
        help=f"The DOI prefix to use (default: {DOI_PREFIX})",
    )
    parser.add_argument(
        "--force",
        "-f",
        help="Force overwrite of existing DOI information",
        action="store_true",
    )
    args = parser.parse_args()

    main(args)
