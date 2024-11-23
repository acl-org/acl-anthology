#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Min-Yen Kan
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
Does not actually assign DOIs (separate script to manufacture XML to submit to Crossref), but
simply adds to the XML, after checking that the DOI URL exists and resolves.

Usage:

    add_dois.py [list of volume IDs]

e.g.,

    python3 add_dois.py P19-1 P19-2 P19-3 P19-4 W19-32

Modifies the XML.  Warns if DOIs already present.  Use -f to force.

Limitations:
- Doesn't current add the entire proceedings volume itself.
"""

import sys
import os
import anthology.data as data

from anthology.utils import (
    build_anthology_id,
    deconstruct_anthology_id,
    test_url_code,
    indent,
    make_simple_element,
)
from anthology.formatter import MarkupFormatter
from time import sleep

import lxml.etree as ET


def add_doi(xml_node, anth_id, force=False):
    """
    :param xml_node: the XML node to add the DOI to
    :param anth_id: The Anthology ID of the paper, volume, or frontmatter
    :param force: Whether to overwrite existing DOIs
    """

    new_doi_text = f"{data.DOI_PREFIX}{anth_id}"

    doi = xml_node.find("doi")
    if doi is not None:
        print(
            f"-> [{anth_id}] Cowardly refusing to overwrite existing DOI {doi.text} (use --force)",
            file=sys.stderr,
        )
        return False

    doi_url = f"{data.DOI_URL_PREFIX}{data.DOI_PREFIX}{anth_id}"
    for tries in [1, 2, 3]:  # lots of random failures
        try:
            result = test_url_code(doi_url)
            if result.status_code == 200:
                doi = make_simple_element("doi", text=new_doi_text)
                print(f"-> Adding DOI {new_doi_text}", file=sys.stderr)
                xml_node.append(doi)
                return True
            elif result.status_code == 429:  # too many requests
                pause_for = int(result.headers["Retry-After"])
                print(f"--> Got 429, pausing for {pause_for} seconds", file=sys.stderr)
                sleep(pause_for + 1)
            elif result.status_code == 404:  # not found
                print("--> Got 404", file=sys.stderr)
                break
            else:
                print(f"--> Other problem: {result}", file=sys.stderr)

        except Exception as e:
            print(e)

    print(f"-> Couldn't add DOI for {doi_url}", file=sys.stderr)
    return False


def process_volume(anthology_volume):
    collection_id, volume_id, _ = deconstruct_anthology_id(anthology_volume)

    print(f"Attempting to add DOIs for {anthology_volume}", file=sys.stderr)

    # Update XML
    xml_file = os.path.join(
        os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{collection_id}.xml"
    )
    tree = ET.parse(xml_file)

    formatter = MarkupFormatter()

    num_added = 0

    volume = tree.getroot().find(f"./volume[@id='{volume_id}']")
    if volume is not None:
        volume_booktitle = volume.find("./meta/booktitle")
        volume_title = formatter.as_text(volume_booktitle)
        print(f'-> Found volume "{volume_title}"', file=sys.stderr)

        # Add the volume-level DOI
        meta_node = volume.find("meta")
        if meta_node is not None:
            anth_id = build_anthology_id(collection_id, volume_id)
            added = add_doi(meta_node, anth_id, force=args.force)
            num_added += added

        # Iterate through all papers
        papers = volume.findall("paper")
        if (frontmatter := volume.find("frontmatter")) is not None:
            papers.insert(0, frontmatter)

        for paper_node in papers:
            # get the paper id attrib, default to 0 (frontmatter)
            paper_id = int(paper_node.attrib.get("id", 0))
            anth_id = build_anthology_id(collection_id, volume_id, paper_id)

            added = add_doi(paper_node, anth_id, force=args.force)
            if added:
                num_added += 1
                sleep(0.1)

        indent(tree.getroot())

        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
        print(
            f"-> added {num_added} DOIs to to the XML for collection {collection_id}",
            file=sys.stderr,
        )

    else:
        print(f"-> FATAL: volume {volume} not found in the Anthology", file=sys.stderr)
        sys.exit(1)


def main(args):
    for volume in args.anthology_volumes:
        process_volume(volume)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "anthology_volumes",
        nargs="+",
        help="One or more Anthology volumes (e.g., P17-1, W18-02)",
    )
    parser.add_argument(
        "--prefix",
        "-p",
        default=data.DOI_PREFIX,
        help="The DOI prefix to use (default: " + data.DOI_PREFIX + ")",
    )
    parser.add_argument(
        "--force",
        "-f",
        help="Force overwrite of existing DOI information",
        action="store_true",
    )
    args = parser.parse_args()

    main(args)
