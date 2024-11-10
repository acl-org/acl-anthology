#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
Used to import the links to code and data from Papers with Code (paperswithcode.com)
"""

import logging
import json
import lxml.etree as etree
import os
import logging as log
import requests
import sys


def format_str(x):
    """Format as string if a value is missing or bool."""
    if x is None:
        return ""
    elif isinstance(x, bool):
        return "true" if x else "false"
    else:
        return str(x)


def shift_tails(element):
    """Shift XML children tails to preserve the exact formatting"""
    children = list(element)
    children[-1].tail = children[-2].tail
    children[-2].tail = children[-3].tail


def remove_and_shift_tails(element, child):
    """Remove element and make tails consistent"""
    children = list(element)
    inx = children.index(child)

    if inx > 0:
        children[inx - 1].tail = children[inx].tail

    element.remove(child)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Import metadata from Papers with Code")
    ap.add_argument(
        "-i", "--infile", help="Input metadata JSON (default: fetch from PWC API)"
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.infile:
        with open(args.infile, "r") as f:
            pwc_meta = json.load(f)
    else:
        # Adds a 30s 'timeout' threshold for HTTP request
        res = requests.get("https://paperswithcode.com/integrations/acl/", timeout=30)
        if res.ok:
            pwc_meta = res.json()
        else:
            log.warning("Couldn't fetch metadata from Papers with Code (server error).")
            sys.exit(1)

    data_base = "data/xml"

    for xml_filename in os.listdir(data_base):
        # skip any non-xml files
        if not xml_filename.endswith(".xml"):
            continue

        full_path = os.path.join(data_base, xml_filename)

        # load
        with open(full_path) as f:
            tree = etree.parse(f)

        # track if we modified
        old_content = etree.tostring(
            tree, encoding="UTF-8", xml_declaration=True, with_tail=True
        ).decode("utf8")

        for volume in tree.findall("volume"):
            for paper in volume.findall("paper"):
                acl_url = paper.find("url")
                if acl_url is not None:
                    acl_id = acl_url.text
                else:
                    # skip if we cannot construct the id
                    continue

                # start by removing any old entries
                for old in paper.findall("pwccode"):
                    remove_and_shift_tails(paper, old)
                for old in paper.findall("pwcdataset"):
                    remove_and_shift_tails(paper, old)

                if acl_id in pwc_meta:
                    pwc = pwc_meta[acl_id]
                    pwc_code = pwc["code"]
                    if pwc_code["url"] or pwc_code["additional"]:
                        code = etree.SubElement(paper, "pwccode")
                        code.set("url", format_str(pwc_code["url"]))
                        code.set("additional", format_str(pwc_code["additional"]))
                        if pwc_code["name"]:
                            code.text = pwc_code["name"]
                        shift_tails(paper)

                    for pwc_data in pwc["datasets"]:
                        data = etree.SubElement(paper, "pwcdataset")
                        data.set("url", pwc_data["url"])
                        data.text = pwc_data["name"]
                        shift_tails(paper)

        new_content = etree.tostring(
            tree, encoding="UTF-8", xml_declaration=True, with_tail=True
        ).decode("utf8")

        if old_content != new_content:
            with open(full_path, "w") as outfile:
                outfile.write(new_content + "\n")  # all files end with newline

            log.info(f"Modified Papers with Code metadata in {full_path}")
