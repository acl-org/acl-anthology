#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 Matt Post <post@cs.jhu.edu>
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
Used to add an award to a paper in the Anthology.

Usage:

  add_award.py paper_id "Award title"

"""

import argparse
import filetype
import os
import shutil
import ssl
import sys
import tempfile

from anthology.utils import (
    deconstruct_anthology_id,
    make_simple_element,
    indent,
    compute_hash,
    infer_url,
    is_newstyle_id,
)
from anthology.data import ANTHOLOGY_PDF

import lxml.etree as ET


def main(args):
    print(f"Adding {args.award} to {args.anthology_id}...")

    collection_id, volume_id, paper_id = deconstruct_anthology_id(args.anthology_id)

    # Update XML
    xml_file = os.path.join(
        os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{collection_id}.xml"
    )
    tree = ET.parse(xml_file)
    paper = tree.getroot().find(f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']")
    if paper is None:
        print(f"Error: Can't find paper {args.anthology_id}, quitting")

    existing_award = paper.find("./award")
    if existing_award is not None and award.text.lower() == args.award:
        print(
            f"Error: Award {args.award} already exists for {args.anthology_id}, quitting"
        )

    make_simple_element("award", args.award, parent=paper)
    indent(tree.getroot())

    tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "anthology_id", help="The Anthology paper ID to revise (e.g., P18-1001)"
    )
    parser.add_argument("award", help="Brief description of the changes.")
    args = parser.parse_args()

    main(args)
