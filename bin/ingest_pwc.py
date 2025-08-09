#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 Robert Stojnic
# Copyright 2023–2025 Matt Post, Marcel Bollmann
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

import json
import os
import logging as log
from pathlib import Path
import requests
import sys

from acl_anthology import Anthology
from acl_anthology.files import PapersWithCodeReference
from acl_anthology.utils.ids import parse_id
from acl_anthology.utils.logging import setup_rich_logging

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Import metadata from Papers with Code")
    ap.add_argument(
        "-i", "--infile", help="Input metadata JSON (default: fetch from PWC API)"
    )
    args = ap.parse_args()

    setup_rich_logging(level=log.INFO)

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

    datadir = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "data"
    anthology = Anthology(datadir=datadir)

    # Iterate over all papers in the JSON response
    changed_collections = set()
    ids_with_pwc_reference = set()

    for full_id, pwc_data in pwc_meta.items():
        if full_id.endswith(".pdf"):
            full_id = full_id[:-4]
        try:
            parsed_id = parse_id(full_id)
        except ValueError:
            log.error(f"Failed to parse Anthology ID: {full_id}")
            continue

        if paper := anthology.get_paper(parsed_id):
            pwc_code = pwc_data["code"]
            reference = PapersWithCodeReference(
                code=(pwc_code["name"], pwc_code["url"]) if pwc_code["url"] else None,
                community_code=bool(pwc_code["additional"]),
                datasets=[
                    (pwc_ds["name"], pwc_ds["url"]) for pwc_ds in pwc_data["datasets"]
                ],
            )
            if (
                reference.code is None
                and not reference.community_code
                and not reference.datasets
            ):
                reference = None
            else:
                ids_with_pwc_reference.add(full_id)

            if paper.paperswithcode != reference:
                paper.paperswithcode = reference
                changed_collections.add(parsed_id[0])

    # Sanity-check that there are no other papers with PwC references
    all_pwc = {
        paper.full_id for paper in anthology.papers() if paper.paperswithcode is not None
    }
    for full_id in all_pwc - ids_with_pwc_reference:
        paper = anthology.get_paper(full_id)
        paper.paperswithcode = None
        changed_collections.add(paper.full_id_tuple[0])

    # Save changes
    for collection_id in changed_collections:
        log.info(f"Modified Papers with Code metadata in {collection_id}")
        anthology.get_collection(collection_id).save()
