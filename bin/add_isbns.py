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
Usage:
  add_isbns.py ISBN-file

  Adds <language>eng</language> to all files in a specified XML file.
  Created for LREC 2020; kept for later adaptation.
"""

import argparse
import os
import sys

from anthology.utils import (
    make_simple_element,
    indent,
)

import lxml.etree as ET


def main(args):

    for line in args.isbn_file:
        venue, isbn = line.rstrip().split()

        xml_file = os.path.join(
            os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{venue}.xml"
        )
        if not os.path.exists(xml_file):
            print(f"Can't find {xml_file}")
            continue
        tree = ET.parse(xml_file)
        meta = tree.getroot().find(f".//volume[@id='1']/meta")
        if meta is not None and meta.find("./isbn") is None:
            print(f"Adding {isbn} to {venue} meta block")
            make_simple_element("isbn", isbn, parent=meta)
        elif volume.find("./isbn") is not None:
            print(f"{venue} already done")

        indent(tree.getroot())
        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("isbn_file", type=argparse.FileType("r"))
    args = parser.parse_args()

    main(args)
