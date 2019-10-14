#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Matt Post <post@cs.jhu.edu>
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

"""Usage: build_pdf_sitemap.py [--importdir=DIR] [--debug]

Builds a sitemap from all local PDFs (linked to via <url> tags in the XML).

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../data/]
  --debug                  Output debug-level log messages.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from collections import defaultdict
from tqdm import tqdm
import logging as log
import os
import yaml, yamlfix

try:
    from yaml import CSafeDumper as Dumper
except ImportError:
    from yaml import SafeDumper as Dumper

from anthology import Anthology
from anthology.utils import SeverityTracker
from anthology import data


def export_anthology(anthology):
    print('<?xml version="1.0" encoding="utf-8" standalone="yes" ?>')
    print('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # Prepare paper index
    papers = defaultdict(dict)
    for id_, paper in anthology.papers.items():
        log.debug("export_anthology: processing paper '{}'".format(id_))
        try:
            pdf = paper.get('pdf')
            if pdf is None:
                print(f'{paper.full_id} has null pdf')
            if pdf is not None and pdf.startswith(data.ANTHOLOGY_PREFIX):
                print(f'  <url>\n    <loc>{pdf}</loc>\n  </url>')
        except KeyError:
            continue

    print('</urlset>')

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

    log.info("Reading the Anthology data...")
    anthology = Anthology(importdir=args["--importdir"])
    log.info("Exporting to YAML...")
    export_anthology(anthology)

    if tracker.highest >= log.ERROR:
        exit(1)
