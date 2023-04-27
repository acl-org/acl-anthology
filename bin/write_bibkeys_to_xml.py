#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: write_bibkeys_to_xml.py [--importdir=DIR] [-c | --commit] [--debug]

Generates BibTeX keys for papers that lack them, and writes them to the XML
(if -c|--commit is given).

Options:
  --importdir=DIR          Directory to import XML files from.
                             [default: {scriptdir}/../data/]
  -c, --commit             Commit (=write) the changes to the XML files;
                             will only do a dry run otherwise.
  --debug                  Output debug-level log messages.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
import logging as log
import os

from anthology import Anthology
from anthology.utils import SeverityTracker, make_simple_element, indent

import lxml.etree as ET


def write_bibkeys(anthology, srcdir, commit=False):
    for volume_id, volume in anthology.volumes.items():
        papers_without_bibkey = []

        for paper in volume:
            bibkey = paper.bibkey
            if bibkey is None or bibkey == paper.full_id:
                papers_without_bibkey.append(paper)

        if papers_without_bibkey:
            log.info(
                f"Found {len(papers_without_bibkey):4d} papers without bibkeys in volume {volume_id}"
            )
            if not commit:
                continue
        else:
            continue

        # We got some new bibkeys and need to write them to the XML
        xml_file = os.path.join(srcdir, "xml", f"{volume.collection_id}.xml")
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for paper in papers_without_bibkey:
            if paper.paper_id == "0":
                node = root.find(f"./volume[@id='{paper.volume_id}']/frontmatter")
                if node is None:  # dummy frontmatter
                    continue
            else:
                node = root.find(
                    f"./volume[@id='{paper.volume_id}']/paper[@id='{paper.paper_id}']"
                )
            if node is None:
                log.error(f"Paper {paper.full_id} not found in {xml_file}")
                continue

            # Generate unique bibkey
            bibkey = anthology.pindex.create_bibkey(paper, vidx=anthology.venues)
            make_simple_element("bibkey", bibkey, parent=node)

        indent(root)
        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )

    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    log.info("Instantiating the Anthology...")
    anthology = Anthology(importdir=args["--importdir"], require_bibkeys=False)
    log.info("Scanning for papers without <bibkey> tags...")
    write_bibkeys(anthology, args["--importdir"], commit=bool(args["--commit"]))

    if not args["--commit"]:
        if tracker.highest >= log.ERROR:
            log.warning(
                "There were errors! Please check them carefully before re-running this script with -c/--commit."
            )
        else:
            log.warning(
                "Re-run this script with -c/--commit to save these changes to the XML files."
            )

    if tracker.highest >= log.ERROR:
        exit(1)
