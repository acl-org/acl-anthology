#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Matt Post <post@cs.jhu.edu>
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

"""Creates the Crossref metadata submission XML for ACL Anthology data.
Needs to be uploaded to Crossref via the ACL organization credentials.
Note that each DOI assigned costs the ACL $1 USD.

- Only assign DOIs to ACL venues (i.e., those run by ACL or
  (co-)sponsored by an ACL chapter or SIG)
- Do not assign DOIs to journals that assign their own DOIs (as of
  current, both CL and TACL should be assigning their own DOIs)

See also https://github.com/acl-org/acl-anthology/wiki/DOI

Accepts either volume IDs or event IDs (auto-detected by format):

    python3 bin/generate_crossref_doi_metadata.py 2024.emnlp-main 2024.emnlp-long
    python3 bin/generate_crossref_doi_metadata.py emnlp-2024
    python3 bin/generate_crossref_doi_metadata.py W10-17

For events, all colocated volumes are resolved automatically.

Limitations:
- This script does not inject the DOI data into the Anthology XML.
  For this, use `bin/add_dois.py <list of volume IDs>`.
- Doesn't properly handle existing ISBN information.
"""

import logging
import re
import sys
import time

from lxml import etree

from acl_anthology import Anthology
from acl_anthology.constants import RE_EVENT_ID
from acl_anthology.utils.logging import setup_rich_logging

log = logging.getLogger(__name__)

# CONSTANTS
DOI_PREFIX = "10.18653/v1/"
CANONICAL_URL_TEMPLATE = "https://aclanthology.org/{}"
PUBLISHER_PLACE = "Stroudsburg, PA, USA"
DEPOSITOR_NAME = "Matt Post"
EMAIL_ADDRESS = "anthology@aclweb.org"
REGISTRANT = "Association for Computational Linguistics"
PUBLISHER = "Association for Computational Linguistics"
MONTH_HASH = {
    "January": "1",
    "February": "2",
    "March": "3",
    "April": "4",
    "May": "5",
    "June": "6",
    "July": "7",
    "August": "8",
    "Aug": "8",
    "September": "9",
    "October": "10",
    "November": "11",
    "December": "12",
}


def make_simple_element(tag, text=None, attrib=None, parent=None, namespaces=None):
    """Create an lxml Element, optionally appending it to a parent."""
    el = etree.Element(tag, nsmap=namespaces)
    if parent is not None:
        parent.append(el)
    if text is not None:
        el.text = str(text)
    if attrib:
        for key, value in attrib.items():
            el.attrib[key] = value
    return el


def classify_input(identifier):
    """Classify an identifier as a volume ID or event ID.

    Volume IDs contain a dot (new-style, e.g. "2024.emnlp-main") or match
    old-style format (e.g. "W10-17", "P19-1").
    Event IDs match the pattern "venue-year" (e.g. "naacl-2012", "acl-2025").

    Returns:
        A tuple of ("volume", identifier) or ("event", identifier).
    """
    # New-style volume IDs contain a dot
    if "." in identifier:
        return ("volume", identifier)
    # Old-style volume IDs: single uppercase letter + 2 digits + dash + digits
    if re.match(r"^[A-Z]\d{2}-\d+$", identifier):
        return ("volume", identifier)
    # Event IDs: lowercase venue + dash + 4-digit year
    if re.match(RE_EVENT_ID, identifier):
        return ("event", identifier)
    log.error("Cannot classify '%s' as a volume ID or event ID", identifier)
    sys.exit(1)


def resolve_inputs(anthology, identifiers):
    """Resolve a list of identifiers to volume IDs.

    Volume IDs are passed through; event IDs are expanded to their colocated volumes.

    Returns:
        A sorted, deduplicated list of volume full_id strings.
    """
    volume_ids = set()
    for identifier in identifiers:
        kind, value = classify_input(identifier)
        if kind == "volume":
            volume_ids.add(value)
        elif kind == "event":
            event = anthology.get_event(value)
            if event is None:
                log.error("Event '%s' not found", value)
                sys.exit(1)
            for volume in event.volumes():
                volume_ids.add(volume.full_id)
    return sorted(volume_ids)


def generate_crossref_xml(anthology, volume_ids, batch_id=None):
    """Generate Crossref DOI metadata XML for the given volume IDs.

    Args:
        anthology: An Anthology instance.
        volume_ids: List of volume ID strings (e.g., ["W10-17", "2024.emnlp-main"]).
        batch_id: Optional fixed batch ID for the DOI batch. If None, uses current time.

    Returns:
        UTF-8 encoded XML as bytes.
    """
    if batch_id is None:
        batch_id = int(time.time())

    # Assemble container
    doi_batch = make_simple_element(
        "doi_batch",
        attrib={
            "xmlns": "http://www.crossref.org/schema/4.4.1",
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": "http://www.crossref.org/schema/4.4.1 http://www.crossref.org/schema/deposit/crossref4.4.1.xsd",
            "version": "4.4.1",
        },
        namespaces={"xsi": "http://www.w3.org/2001/XMLSchema-instance"},
    )
    tree = etree.ElementTree(doi_batch)

    # Assemble head
    head = make_simple_element("head", parent=tree.getroot())
    make_simple_element("doi_batch_id", text=str(batch_id), parent=head)
    make_simple_element("timestamp", text=str(batch_id), parent=head)
    depositor = make_simple_element("depositor", parent=head)
    make_simple_element("depositor_name", text=DEPOSITOR_NAME, parent=depositor)
    make_simple_element("email_address", text=EMAIL_ADDRESS, parent=depositor)
    make_simple_element("registrant", text=REGISTRANT, parent=head)

    # Assemble body
    body = make_simple_element("body", parent=tree.getroot())

    for full_volume_id in sorted(volume_ids):
        volume = anthology.get_volume(full_volume_id)
        if volume is None:
            log.warning("Can't find volume %s", full_volume_id)
            continue

        year = volume.year
        booktitle = str(volume.title)
        address = volume.address or ""
        publisher = volume.publisher or PUBLISHER

        # Parse month
        start_month = ""
        end_month = ""
        if volume.month:
            month = volume.month
            try:
                parts = re.split("[-–]", month)
                start_month = MONTH_HASH[parts[0]]
                end_month = MONTH_HASH[parts[1]] if len(parts) > 1 else start_month
            except (KeyError, IndexError):
                log.error("Can't parse month %s in %s", month, full_volume_id)
                sys.exit(1)

        # Conference element
        c = make_simple_element("conference", parent=body)

        # Editors as contributors
        contribs = make_simple_element("contributors", parent=c)
        editor_index = 0
        for editor in volume.editors:
            pn = make_simple_element(
                "person_name",
                parent=contribs,
                attrib={
                    "contributor_role": "chair",
                    "sequence": "first" if editor_index == 0 else "additional",
                },
            )
            editor_index += 1
            if editor.name.first:
                make_simple_element("given_name", parent=pn, text=editor.name.first)
            make_simple_element("surname", text=editor.name.last, parent=pn)

        if editor_index == 0:
            log.error("Found no editors for volume %s", full_volume_id)
            sys.exit(1)

        # Event Metadata
        em = make_simple_element("event_metadata", parent=c)
        make_simple_element("conference_name", parent=em, text=booktitle)
        make_simple_element("conference_location", parent=em, text=address)
        make_simple_element(
            "conference_date",
            parent=em,
            attrib={
                "start_year": year,
                "end_year": year,
                "start_month": start_month,
                "end_month": end_month,
            },
        )

        # Proceedings Metadata
        pm = make_simple_element(
            "proceedings_metadata", parent=c, attrib={"language": "en"}
        )
        make_simple_element("proceedings_title", parent=pm, text=booktitle)
        p = make_simple_element("publisher", parent=pm)
        make_simple_element("publisher_name", parent=p, text=publisher)
        make_simple_element("publisher_place", parent=p, text=PUBLISHER_PLACE)
        pd = make_simple_element("publication_date", parent=pm)
        make_simple_element("year", parent=pd, text=year)
        make_simple_element("noisbn", parent=pm, attrib={"reason": "simple_series"})

        # DOI for the proceedings volume
        dd = make_simple_element("doi_data", parent=pm)
        make_simple_element("doi", parent=dd, text=DOI_PREFIX + full_volume_id)
        make_simple_element(
            "resource", parent=dd, text=CANONICAL_URL_TEMPLATE.format(full_volume_id)
        )

        # Individual papers (including frontmatter)
        for paper in volume.papers():
            is_frontmatter = paper.is_frontmatter

            if is_frontmatter:
                contributor_specs = volume.editors
            else:
                contributor_specs = paper.authors

            if len(contributor_specs) == 0:
                log.warning(
                    "Found no contributors for %s %s, skipping",
                    "frontmatter" if is_frontmatter else "paper",
                    paper.full_id,
                )
                continue

            cp = make_simple_element("conference_paper", parent=c)
            paper_contribs = make_simple_element("contributors", parent=cp)

            # Contributors
            author_index = 0
            for author in contributor_specs:
                pn = make_simple_element(
                    "person_name",
                    parent=paper_contribs,
                    attrib={
                        "contributor_role": "author",
                        "sequence": "first" if author_index == 0 else "additional",
                    },
                )
                author_index += 1
                if author.name.first:
                    make_simple_element("given_name", parent=pn, text=author.name.first)
                make_simple_element("surname", text=author.name.last, parent=pn)

            # Title
            if is_frontmatter:
                title_text = "Front Matter"
            else:
                title_text = str(paper.title) if paper.title else "Front Matter"
            o_titles = make_simple_element("titles", parent=cp)
            make_simple_element("title", parent=o_titles, text=title_text)

            # Publication date
            pd = make_simple_element("publication_date", parent=cp)
            make_simple_element("year", parent=pd, text=year)

            # Pages
            if paper.pages:
                o_pages = make_simple_element("pages", parent=cp)
                try:
                    parts = re.split("[-–]", paper.pages)
                    fp_text = parts[0]
                    lp_text = parts[1] if len(parts) > 1 else parts[0]
                except IndexError:
                    fp_text = paper.pages
                    lp_text = paper.pages
                make_simple_element("first_page", parent=o_pages, text=fp_text)
                make_simple_element("last_page", parent=o_pages, text=lp_text)

            # DOI for the paper
            paper_url = paper.full_id
            dd = make_simple_element("doi_data", parent=cp)
            make_simple_element("doi", parent=dd, text=DOI_PREFIX + paper_url)
            make_simple_element(
                "resource", parent=dd, text=CANONICAL_URL_TEMPLATE.format(paper_url)
            )

    return etree.tostring(
        tree,
        pretty_print=True,
        encoding="UTF-8",
        xml_declaration=True,
        with_tail=True,
    )


def main(args):
    setup_rich_logging()
    anthology = Anthology.from_within_repo(verbose=False)
    volume_ids = resolve_inputs(anthology, args.identifiers)

    xml_bytes = generate_crossref_xml(anthology, volume_ids)
    sys.stdout.buffer.write(xml_bytes)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Crossref DOI metadata XML for ACL Anthology volumes or events."
    )
    parser.add_argument(
        "identifiers",
        nargs="+",
        help="Volume IDs (e.g., 2024.emnlp-main, W10-17) or event IDs (e.g., emnlp-2024, naacl-2012)",
    )
    args = parser.parse_args()

    main(args)
