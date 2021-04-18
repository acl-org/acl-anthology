#! /usr/bin/env python3
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
Reads in a tab-delimited list of (Anth ID, new title) pairs, and sets
the titles for the papers. Efficiently opens each XML file only once
if inputs are ordered.

    cat new-titles.tsv | python3 ./fix_titles.py
"""

import argparse
import os
import sys

from anthology.utils import indent, deconstruct_anthology_id, make_simple_element
from normalize_anth import normalize

import lxml.etree as ET


def main(args):

    prev_xml_file = None
    tree = None
    for line in args.tsv_file:
        anth_id, newtitle = line.rstrip().split("\t")

        collection_id, volume_id, paper_id = deconstruct_anthology_id(anth_id)

        xml_file = os.path.join(
            os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{collection_id}.xml"
        )

        if prev_xml_file is not None and xml_file != prev_xml_file:
            print(f"-> Dumping to file {prev_xml_file}")
            indent(tree.getroot())
            tree.write(prev_xml_file, encoding="UTF-8", xml_declaration=True)

        if prev_xml_file is None or xml_file != prev_xml_file:
            tree = ET.parse(xml_file)

        volume = tree.getroot().find(f"./volume[@id='{volume_id}']")
        paper = volume.find(f"./paper[@id='{paper_id}']")
        if paper is None:
            print(f"Can't find {anth_id} in {xml_file}")
            continue

        title = paper.find(f"./title")
        if title is None:
            print(f"** WARNING: no title for for {anth_id}")
            continue

        print(f"{anth_id}: Changing title from\n-> {title.text} to\n-> {newtitle}")

        # Remove kids from existing title, update text, then re-normalize
        kids = [kid for kid in title]
        for kid in kids:
            title.remove(kid)
        title.text = newtitle
        normalize(title, informat="latex")

        prev_xml_file = xml_file

    indent(tree.getroot())
    tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
    print(f"-> Dumping to file {xml_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "tsv_file", nargs="?", default=sys.stdin, help="Where to read TSV file from"
    )
    args = parser.parse_args()

    main(args)
