#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 Matt Post <post@cs.jhu.edu>
# Copyright 2025 Marcel Bollmann <marcel@bollmann.me>
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

"""Add awards to papers in the Anthology.

Usage:
  add_award.py PAPER_ID AWARD_TITLE
  add_award.py -f TXTFILE

Arguments:
  PAPER_ID               The Anthology ID of the paper to assign the award to.
  AWARD_TITLE            The name of the award.

Options:
  -f, --from-file FILE   A file that lists one Anthology ID + award title per line.

Examples:
  If you use --from-file, the expected format is like this:

    2021.naacl-main.119 Best Long Paper
    2021.naacl-main.31 Outstanding Long Paper
    2021.naacl-main.185 Outstanding Long Paper
"""

from docopt import docopt
from pathlib import Path
import logging as log

from acl_anthology import Anthology
from acl_anthology.collections import Collection
from acl_anthology.utils.logging import setup_rich_logging


def add_award(anthology: Anthology, paper_id: str, title: str) -> Collection:
    if (paper := anthology.get_paper(paper_id)) is None:
        log.error(f"Couldn't find paper: {paper_id}")
        return

    if title.lower() in (award.lower() for award in paper.awards):
        log.warning(f"Award '{title}' already listed for {paper_id}, skipping")
        return

    paper.awards.append(title)
    return paper.parent.parent


if __name__ == "__main__":
    args = docopt(__doc__)
    anthology = Anthology(datadir=Path(__file__).parent / ".." / "data")
    tracker = setup_rich_logging()
    modified_collections = set()

    if (filename := args["--from-file"]) is not None:
        with open(filename, "r") as f:
            awards = [line.strip().split(maxsplit=1) for line in f]
    else:
        awards = [[args["PAPER_ID"], args["AWARD_TITLE"]]]

    for paper_id, award in awards:
        c = add_award(anthology, paper_id, award)
        if c:
            modified_collections.add(c.id)

    for collection_id in modified_collections:
        anthology.get(collection_id).save()

    if tracker.highest >= log.ERROR:
        exit(1)
