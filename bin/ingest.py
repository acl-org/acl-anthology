#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Matt Post <post@cs.jhu.edu>
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
Ingests data into the Anthology. It takes an XML file and:

- converts to nested format if not already done
- applies normalization (fixed-case protection)
- runs sanity checks (e.g., % of authors in input data that are new)
"""

import argparse
import os
import re
import sys

import lxml.etree as etree

from normalize_anth import process
from anthology.utils import make_nested, make_simple_element, indent

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('infile')
    parser.add_argument('--append', '-a', action='store_true', help='Append to existing volume instead of quitting.')
    args = parser.parse_args()

    tree = etree.parse(args.infile)

    # Ensure nested format
    root = make_nested(tree.getroot())
    collection_id = root.attrib['id']

    # Normalize
    for paper in root.findall('.//paper'):
        papernum = "{} vol {} paper {}".format(root.attrib['id'],
                                               paper.getparent().attrib['id'],
                                               paper.attrib['id'])
        for oldnode in paper:
            location = "{}:{}".format(papernum, oldnode.tag)
            process(oldnode, informat='xml')

    # Ingest each volume.
    # First, find the XML file.
    collection_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'data', 'xml', f'{collection_id}.xml')
    tree = etree.parse(collection_file) if os.path.exists(collection_file) else etree.ElementTree(make_simple_element('collection', attrib={'id': collection_id}))

    for new_volume in root.findall('volume'):
        volume_id = new_volume.attrib['id']
        existing_volume = tree.getroot().find(f"./volume[@id='{volume_id}']")
        if existing_volume is not None:
            if args.append:
                for paper in new_volume.findall('./paper'):
                    print(f'Appending {paper.attrib["id"]}')
                    existing_volume.append(paper)
            else:
                print(f'Volume {volume_id} has already been inserted into {collection_file}.')
                print(f'You can append to this volume by passing `--append` (or `-a`) to this script.')
                print(f'Quitting, since you didn\'t.')
                sys.exit(1)

            break
    else:
        # If no existing volume was found, append the volume
        # TODO: find correct insertion point in the sequence of existing volumes, instead of appending
        tree.getroot().append(new_volume)

    indent(tree.getroot())
    tree.write(collection_file, encoding='UTF-8', xml_declaration=True, with_tail=True)
