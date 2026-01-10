#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019, 2020 Matt Post <post@cs.jhu.edu>
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
Utility script I change all the time for finding papers and doing quick fixes on them.
"""

import argparse

import lxml.etree as etree


from anthology.utils import (
    make_simple_element,
)


def main(args):
    for collection_file in args.files:
        root_node = etree.parse(collection_file).getroot()
        for paper in root_node.findall(".//paper"):
            title = paper.find("./title")
            search_text = " [In <fixed-case>F</fixed-case>rench]"
            if search_text in title.text:
                title.text = title.text.sub(search_text, "")
                make_simple_element("language", "fra", parent=paper)

        tree = etree.ElementTree(root_node)
        tree.write(
            collection_file, encoding="UTF-8", xml_declaration=True, with_tail=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", help="List of XML files.")
    args = parser.parse_args()
    main(args)
