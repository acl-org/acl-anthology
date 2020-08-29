#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: create_bibtex.py [--importdir=DIR] [--exportdir=DIR] [-c] [--debug]

Creates .bib files for all papers in the Hugo directory.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../data/]
  --exportdir=DIR          Directory to write exported files to.   [default: {scriptdir}/../build/data-export/]
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from lxml import etree
from tqdm import tqdm
import gzip
import logging as log
import io
import os

from anthology import Anthology
from anthology.utils import SeverityTracker, deconstruct_anthology_id, infer_year
from create_hugo_pages import check_directory
from operator import itemgetter


def volume_sorter(volume_tuple):
    """
    Extracts the year so that we can sort by the year and then
    the collection ID.
    """
    volume_id = volume_tuple[0]
    collection_id, year, _ = deconstruct_anthology_id(volume_id)
    year = infer_year(collection_id)
    return year, volume_id


def create_bibtex(anthology, trgdir, clean=False):
    """Creates .bib files for all papers."""
    if not check_directory("{}/papers".format(trgdir), clean=clean):
        return
    if not check_directory("{}/volumes".format(trgdir), clean=clean):
        return

    log.info("Creating BibTeX files for all papers...")
    with gzip.open(
        "{}/anthology.bib.gz".format(trgdir), "wt", encoding="utf-8"
    ) as file_anthology, gzip.open(
        "{}/anthology+abstracts.bib.gz".format(trgdir), "wt", encoding="utf-8"
    ) as file_anthology_with_abstracts:
        for volume_id, volume in tqdm(
            sorted(anthology.volumes.items(), key=volume_sorter, reverse=True)
        ):
            volume_dir = trgdir
            if not os.path.exists(volume_dir):
                os.makedirs(volume_dir)
            with open("{}/volumes/{}.bib".format(trgdir, volume_id), "w") as file_volume:
                for paper in volume:
                    with open(
                        "{}/{}.bib".format(volume_dir, paper.full_id), "w"
                    ) as file_paper:
                        contents = paper.as_bibtex()
                        print(contents, file=file_paper)
                        print(contents, file=file_anthology_with_abstracts)

                        concise_contents = paper.as_bibtex(concise=True)
                        print(concise_contents, file=file_volume)
                        print(concise_contents, file=file_anthology)


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )
    if "{scriptdir}" in args["--exportdir"]:
        args["--exportdir"] = os.path.abspath(
            args["--exportdir"].format(scriptdir=scriptdir)
        )

    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    anthology = Anthology(importdir=args["--importdir"])
    create_bibtex(anthology, args["--exportdir"], clean=args["--clean"])

    if tracker.highest >= log.ERROR:
        exit(1)
