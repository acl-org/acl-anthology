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
Used to add ingested DOIs into the Anthology.  
Does not actually assign DOIs (separate script to manufacture XML to submit to Crossref)

Usage:

  add_dois.py VOLUME_ID

- The ACL Volume ID to add DOIs to (e.g., P17-1, W18-02)

Modifies the XML.  Warns if DOIs already present.  Use -f to force
"""

import argparse
import sys
import tempfile

DOI_PREFIX = "10.18653/v1/"

from anthology.utils import build_anthology_id, deconstruct_anthology_volume, stringify_children

import lxml.etree as ET
import urllib.request

def main(args):

    collection_id, volume_id = deconstruct_anthology_volume(args.anthology_volume)

    print(f'Attempting to add DOIs for {args.anthology_volume}', file=sys.stderr)

    # Update XML
    xml_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'data', 'xml', f'{collection_id}.xml')
    tree = ET.parse(xml_file)
    # add newline to end-of-file if not present
    if not tree.getroot().tail: tree.getroot().tail = '\n'
    volume_sequence = str(int(volume_id))
    volume = tree.getroot().find(f"./volume[@id='{volume_sequence}']")
    if volume is not None:
        n = 0
        volume_title = volume.find(f"./meta/booktitle")
        print (stringify_children(volume_title))
        print(f'Identified as {volume_title}', file=sys.stderr)

        # Process frontmatter
        frontmatter = volume.find('frontmatter')
        has_doi = False
        old_doi_text = ""

        for doi in frontmatter.findall('doi'):
            has_doi = True
            old_doi_text = doi.text

        if (not has_doi or args.force): # need to assign DOI
            new_doi_text = args.prefix + collection_id + "-" + volume_id
            doi = ""
            
            if (args.force and has_doi):
                print(f'Overwritting existing booktitle DOI {old_doi_text} with {new_doi_text}', file=sys.stderr)
                doi = frontmatter.find('doi')
            else:
                print(f'Writing booktitle DOI {new_doi_text}', file=sys.stderr)
                doi = ET.Element('doi')

            doi.text = new_doi_text

            # Set tails to maintain proper indentation
            frontmatter[-1].tail += '  '
            doi.tail = '\n    '  # newline and two levels of indent
            frontmatter.append(doi)
            n += 1
        
        # Iterate through all papers
        for paper in volume.findall('paper'):
            has_doi = False
            old_doi_text = ""

            # check if DOI exists
            for doi in paper.findall('doi'):
                has_doi = True
                old_doi_text = doi.text

            if (not has_doi or args.force): # need to assign DOIs
                new_doi_text = args.prefix + build_anthology_id(collection_id, volume_id, paper.get('id'))
                doi = ""

                if (args.force and has_doi):
                    print(f'Overwritting existing DOI {old_doi_text} with {new_doi_text}', file=sys.stderr)
                    doi = paper.find('doi')
                else:
                    print(f'Writing DOI {new_doi_text}', file=sys.stderr)
                    doi = ET.Element('doi')

                doi.text = new_doi_text

                # Set tails to maintain proper indentation
                paper[-1].tail += '  '
                doi.tail = '\n    '  # newline and two levels of indent
                paper.append(doi)
                n += 1
        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
        print(f'-> added {n} DOIs to to the XML for collection {collection_id}', file=sys.stderr)

    else:
        print(f'-> FATAL: volume {volume} not found in the Anthology', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('anthology_volume', help='The Anthology Volume (e.g., P17-1, W18-02)')
    parser.add_argument('--prefix', '-p', default= DOI_PREFIX, help="The DOI prefix to use (default: " + DOI_PREFIX + ")")
    parser.add_argument('--force', '-f', help="Force overwrite of existing DOI information", action="store_true")
    args = parser.parse_args()

    main(args)
