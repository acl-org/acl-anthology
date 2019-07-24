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
from anthology.utils import make_nested, make_simple_element, build_anthology_id, indent
from anthology.index import AnthologyIndex
from anthology.people import PersonName

from itertools import chain


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('infile')
    parser.add_argument('--append', '-a', action='store_true', help='Append to existing volume instead of quitting.')
    args = parser.parse_args()

    people = AnthologyIndex(None, srcdir=os.path.join(os.path.dirname(sys.argv[0]), '..', 'data'))

    tree_being_added = etree.parse(args.infile)

    # Ensure nested format
    root_being_added = make_nested(tree_being_added.getroot())
    collection_id = root_being_added.attrib['id']

    # Ensure names are properly identified
    ambiguous = {}
    for paper in root_being_added.findall('.//paper'):
        anth_id = build_anthology_id(collection_id,
                                     paper.getparent().attrib['id'],
                                     paper.attrib['id'])

        for node in chain(paper.findall('author'), paper.findall('editor')):
            name = PersonName.from_element(node)
            ids = people.get_ids(name)
            if len(ids) > 1:
                print(f'WARNING ({anth_id}): ambiguous author {name}, defaulting to first of {ids}')
                ambiguous[anth_id] = (name, ids)

                node.attrib['id'] = ids[0]

    # Normalize
    for paper in root_being_added.findall('.//paper'):
        for oldnode in paper:
            process(oldnode, informat='xml')

    # Ingest each volume.
    # First, find the XML file.
    collection_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'data', 'xml', f'{collection_id}.xml')

    if os.path.exists(collection_file):
        existing_tree = etree.parse(collection_file)
    else:
        existing_tree = etree.ElementTree(make_simple_element('collection', attrib={'id': collection_id}))

    # Insert each volume
    for i, new_volume in enumerate(root_being_added.findall('volume')):
        new_volume_id = int(new_volume.attrib['id'])
        existing_volume = existing_tree.getroot().find(f"./volume[@id='{new_volume_id}']")
        if existing_volume is None:
            # Find the insertion point among the other volumes
            insertion_point = 0
            for i, volume in enumerate(existing_tree.getroot()):
                if new_volume_id < int(volume.attrib['id']):
                    break
                insertion_point = i + 1
            print(f"Inserting volume {new_volume_id} at collection position {insertion_point}")
            existing_tree.getroot().insert(insertion_point, new_volume)
        else:
            # Append to existing volume (useful for TACL, which has a single volume each year) if requested
            if args.append:
                for paper in new_volume.findall('./paper'):
                    print(f'Appending {paper.attrib["id"]}')
                    existing_volume.append(paper)
            else:
                print(f'Volume {new_volume_id} has already been inserted into {collection_file}.')
                print(f'You can append to this volume by passing `--append` (or `-a`) to this script.')
                print(f'Quitting, since you didn\'t.')
                sys.exit(1)

    indent(existing_tree.getroot())
    existing_tree.write(collection_file, encoding='UTF-8', xml_declaration=True, with_tail=True)
