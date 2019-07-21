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
simply adds to the XML, after checking that the URL exists.

Usage:

  add_dois.py VOLUME_ID

- The ACL Volume ID to add DOIs to (e.g., P17-1, W18-02)

Modifies the XML.  Warns if DOIs already present.  Use -f to force.
"""

import argparse
import sys
import os
import tempfile
import anthology.data as data
import copy

from anthology.utils import build_anthology_id, deconstruct_anthology_id, stringify_children, test_url, indent, make_simple_element
from anthology.formatter import MarkupFormatter
from itertools import chain

import lxml.etree as ET
import urllib.request

def add_doi(xml_node, collection_id, volume_id, force=False):
    if 'id' in xml_node.attrib:
        # normal paper
        paper_id = int(xml_node.attrib['id'])
    else:
        # frontmatter
        paper_id = 0

    anth_id = build_anthology_id(collection_id, volume_id, paper_id)
    new_doi_text = f'{data.DOI_PREFIX}{anth_id}'
    doi_url = f'{data.DOI_URL_PREFIX}{data.DOI_PREFIX}{anth_id}'
    if not test_url(doi_url):
        print(f"-> [{anth_id}] Skipping since DOI {doi_url} doesn't exist")
        return False

    doi = xml_node.find('doi')
    if doi is not None:
        print(f'-> [{anth_id}] Cowardly refusing to overwrite existing DOI {doi.text} (use --force)', file=sys.stderr)
        return False

    else:
        doi = make_simple_element('doi', text=new_doi_text)
        print(f'Adding DOI {new_doi_text}', file=sys.stderr)
        xml_node.append(doi)
        return True


def main(args):

    collection_id, volume_id, _ = deconstruct_anthology_id(args.anthology_volume)

    print(f'Attempting to add DOIs for {args.anthology_volume}', file=sys.stderr)

    # Update XML
    xml_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'data', 'xml', f'{collection_id}.xml')
    tree = ET.parse(xml_file)

    formatter = MarkupFormatter()

    num_added = 0

    volume = tree.getroot().find(f"./volume[@id='{volume_id}']")
    if volume is not None:
        volume_booktitle = volume.find(f"./meta/booktitle")
        volume_title = formatter.as_text(volume_booktitle)
        print(f'Identified as {volume_title}', file=sys.stderr)

        # Iterate through all papers
        for paper in chain(volume.find('frontmatter'), volume.findall('paper')):
            num_added += add_doi(paper, collection_id, volume_id, force=args.force)

        indent(tree.getroot())

        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
        print(f'-> added {num_added} DOIs to to the XML for collection {collection_id}', file=sys.stderr)

    else:
        print(f'-> FATAL: volume {volume} not found in the Anthology', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('anthology_volume', help='The Anthology Volume (e.g., P17-1, W18-02)')
    parser.add_argument('--prefix', '-p', default=data.DOI_PREFIX, help="The DOI prefix to use (default: " + data.DOI_PREFIX + ")")
    parser.add_argument('--force', '-f', help="Force overwrite of existing DOI information", action="store_true")
    args = parser.parse_args()

    main(args)
