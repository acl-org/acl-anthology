#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Nathan Schneider (@nschneid)
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
Apply heuristics to determine which venues are "top" venues to be
featured on the homepage. Set the `is_toplevel` field in venues.json
accordingly.

Usage:
  compute_top_venues.py

Options:
    -h --help           Show this help message.
"""

import warnings
import logging as log
from docopt import docopt

from acl_anthology import Anthology
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.utils.logging import setup_rich_logging

FLAGSHIP = [
    "AACL",
    "ACL",
    "COLING",
    "CL",
    "EACL",
    "EMNLP",
    "Findings",
    "LREC",
    "NAACL",
    "TACL",
]


def compute_top_level() -> bool:
    changed = False
    num_top = 0
    anthology = Anthology.from_within_repo()

    for venue in anthology.venues.values():
        authors = set()
        num_papers = 0
        for vol in venue.volumes():
            for paper in vol.papers():
                num_papers += 1
                for ns in paper.authors:
                    authors.add(ns.resolve())
        num_authors = len(authors)
        earliest_vol_year = min(map(lambda vol: int(vol.year), venue.volumes()))

        current_is_toplevel = venue.is_toplevel
        if venue.acronym in FLAGSHIP:
            # flagship venues, always top-level
            venue.is_toplevel = True
        elif venue.type == "journal":
            venue.is_toplevel = num_papers >= 100 or earliest_vol_year <= 1985
        elif venue.type == "workshop":
            venue.is_toplevel = num_papers >= 1000 and num_authors >= 1000
        else:
            venue.is_toplevel = num_authors >= 1000 or earliest_vol_year <= 1985

        if venue.is_toplevel:
            num_top += 1

        if venue.is_toplevel != current_is_toplevel:
            changed = True
            anthology.save_all()

    log.info(f"{num_top} top venues including {len(FLAGSHIP)} flagship venues")

    return changed


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    with warnings.catch_warnings(action="ignore", category=NameSpecResolutionWarning):
        changed = compute_top_level()

        if not changed:
            log.info("No changes to top-level venues")
        print('Now run>>> git commit -a -m "Update top-level venues"')
