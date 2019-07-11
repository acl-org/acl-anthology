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
from anthology.utils import make_nested, indent

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('infile')
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

    # Ingest each volume
    collection_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'data', 'xml', f'{collection_id}.xml')
    tree = etree.parse(collection_file)
    for volume in root.findall('volume'):
        # TODO: find correct insertion point using volume ID
        volume_id = volume.attrib['id']
        if tree.getroot().find(f"./volume[@id='{volume_id}']") is not None:
            print(f'Volume {volume_id} has already been inserted into {collection_file}')
            sys.exit(1)

        tree.getroot().append(volume)

    indent(tree.getroot())
    tree.write(collection_file, encoding='UTF-8', xml_declaration=True, with_tail=True)
