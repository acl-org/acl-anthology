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
  add_language.py XML_file

  Adds <language>eng</language> to all files in a specified XML file.
  Created for LREC 2020; kept for later adaptation.
"""

import argparse

from anthology.utils import (
    make_simple_element,
    indent,
)

import lxml.etree as ET


def main(args):

    for xml_file in args.xml_files:
        tree = ET.parse(xml_file)
        for paper in tree.getroot().findall(f".//paper"):
            make_simple_element("language", "eng", parent=paper)

        indent(tree.getroot())
        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("xml_files", nargs="+")
    args = parser.parse_args()

    main(args)
