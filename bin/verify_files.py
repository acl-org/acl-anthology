#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: verify_files.py FILE... [options] [--help]

Verify checksum of files downloaded from the Anthology.

Arguments:
  FILE                     File (PDF or attachment) downloaded from the ACL Anthology,
                           with its original filename as stored on the server.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../data]
  --debug                  Output debug-level log messages.
  -h, --help               Display this helpful text.
"""

from collections import defaultdict
from docopt import docopt
from glob import glob
from lxml import etree
import logging as log
import os

from anthology.utils import SeverityTracker, compute_hash


def main(datadir, filelist):
    to_check = defaultdict(list)

    for filename in filelist:
        basename = os.path.basename(filename)
        collection_id = basename.split("-")[0]
        with open(filename, "rb") as f:
            checksum = compute_hash(f.read())

        to_check[collection_id].append((basename, checksum))

    for collection_id, checklist in to_check.items():
        xml_file = f"{datadir}/xml/{collection_id}.xml"
        tree = etree.parse(xml_file)
        root = tree.getroot()

        for filename, checksum in checklist:
            if filename.endswith(".pdf"):
                xpath = (
                    f'//attachment[text()="{filename}"] | '
                    f'//url[text()="{filename[:-4]}"] | '
                    f'//erratum[text()="{filename[:-4]}"] | '
                    f'//revision[@href="{filename[:-4]}"]'
                )
            else:
                xpath = f'//attachment[text()="{filename}"]'

            find = etree.XPath(xpath)(root)
            if not find:
                log.error(f"{filename}: couldn't find file in {collection_id}.xml")
                continue
            elif len(find) > 1:
                # this should never happen
                log.warning(
                    f"{filename}: multiple entries with that name in {collection_id}.xml"
                )

            expected = find[0].get("hash")
            if expected != checksum:
                log.error(f"{filename}: CRC32 mismatch -- {checksum} != {expected}")
            else:
                log.debug(f"{filename}: checksum verified")


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

    main(args["--importdir"], args["FILE"])

    if tracker.highest >= log.ERROR:
        exit(1)
