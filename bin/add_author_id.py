#!/usr/bin/env python3
# -*- coding: utf-8  -*-
#
# Copyright 2022 Matt Post <post@cs.jhu.edu>
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
Adds an ID tag to all instances of an author in all XML files where there is no ID tag.

First use case was the Bill Byrne separation of July 2022.

2020.gebnlp-1.4 E14-1026 E14-1028 W16-2324 2021.acl-long.55 2021.eancs-1.2 W15-0116 D19-1125 D19-1331 D19-1459 P14-3000 2022.naacl-main.136 W18-1821 W18-5420 W18-6427 2020.nlp4call-1.2 N19-1406 2021.emnlp-main.620 2021.emnlp-main.666 N18-2081 N18-3013 W17-3531 2020.wmt-1.94 D15-1273 2022.nlp4convai-1.7 P16-2049 C14-1195 P19-1022 W19-4417 W19-4424 W19-5340 W19-5421 2020.wat-1.21 E17-2058 2022.ecnlp-1.13 J14-3008 N15-1041 N15-1105 P18-2051 D17-1208 D17-1220 D17-2005 2020.acl-main.690 2020.acl-main.693 N16-1100 2022.findings-acl.223 2022.findings-acl.301

Usage:

    ./add_author_id.py bill-byrne --last-name Byrne
"""

import argparse
import os

from anthology.utils import indent
from itertools import chain

import lxml.etree as ET


def main(args):
    for xml_file in os.listdir(args.data_dir):
        if not xml_file.endswith(".xml"):
            continue

        changed_one = False

        tree = ET.parse(xml_file)
        for paper_xml in chain(
            tree.getroot().findall(".//paper"), tree.getroot().findall(".//meta")
        ):
            for author_xml in chain(
                paper_xml.findall("./author"), paper_xml.findall("./editor")
            ):
                if "id" in author_xml.attrib:
                    continue
                last_name = author_xml.find("./last").text
                if last_name == args.last_name:
                    paper_id = (
                        paper_xml.attrib["id"] if paper_xml.text == "paper" else "0"
                    )
                    anth_id = f"{xml_file}/{paper_id}"
                    print(f"Adding {args.id} to {anth_id}...")
                    author_xml.attrib["id"] = args.id
                    changed_one = True

        if changed_one:
            indent(tree.getroot())
            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("id", help="Author ID to add")
    parser.add_argument("--last-name", help="Author's last name")
    parser.add_argument("--confirm", action="store_true", help="Confirm each instance")
    parser.add_argument(
        "--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data", "xml")
    )
    args = parser.parse_args()

    main(args)
