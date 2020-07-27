#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020, Matt Post
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
Reads through TACL papers in a specified XML file, downloads the PDF via the DOI
if not reachable on the Anthology, names appropriately.

https://www.mitpressjournals.org/doi/pdf/10.1162/tacl_a_00297
"""

import sys
import os

from anthology.utils import (
    deconstruct_anthology_id,
    infer_url,
    test_url_code,
    is_newstyle_id,
    retrieve_url,
)
from time import sleep

import lxml.etree as ET


def process_volume(anthology_volume):

    collection_id, volume_id, _ = deconstruct_anthology_id(anthology_volume)
    if is_newstyle_id(anthology_volume):
        venue_path = collection_id.split(".")[1]
    else:
        venue_path = os.path.join(collection_id[0], collection_id)

    print(f"Downloading PDFs for {anthology_volume}", file=sys.stderr)

    # Update XML
    xml_file = os.path.join(
        os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{collection_id}.xml"
    )
    tree = ET.parse(xml_file)

    for paper in tree.getroot().findall(f".//paper"):
        anthid = paper.find("./url").text

        # Try to get the URL from the Anthology
        if not test_url_code(infer_url(anthid)):
            doi = paper.find("./doi").text
            doi_pdf = f"https://www.mitpressjournals.org/doi/pdf/{doi}"
            local_path = os.path.join(
                args.anthology_files_dir, venue_path, f"{anthid}.pdf"
            )
            if not os.path.exists(os.path.dirname(local_path)):
                os.makedirs(os.path.dirname(local_path))

            retrieve_url(doi_pdf, local_path)
            print(f"Saved {doi_pdf} to {local_path}")
            sleep(1)


def main(args):
    for volume in args.anthology_volumes:
        process_volume(volume)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "anthology_volumes",
        nargs="+",
        help="One or more Anthology volumes (e.g., P17-1, W18-02)",
    )
    parser.add_argument(
        "--anthology-files-dir",
        "-d",
        default=os.path.join(os.environ["HOME"], "anthology-files/pdf"),
        help="Anthology web directory root.",
    )
    args = parser.parse_args()

    main(args)
