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
For an existing verified author, remove explicit linking to specified papers
(that list the person ID).

See also: disable_name_matching.py (to turn off implicit linking)

Usage:
  unlink_items.py [--issue NUM] [--keep] AUTHORID PAPERID ...

Arguments:
    AUTHORID            Currently verified author ID.
    PAPERID             List of paper or volume IDs associated with the verified author.

Options:
    -h --help           Show this help message.
    --issue NUM         GitHub issue number to include in commit message.
    --keep              Keep only the specified items; unlink all others.
"""

import warnings
import logging as log
from docopt import docopt

from acl_anthology import Anthology
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.utils.logging import setup_rich_logging


def unlink_items(author_id, paper_ids, keep_only_these_papers=False):
    changes = ""
    anthology = Anthology.from_within_repo()

    person = anthology.get_person(author_id)

    numPapers = len(list(person.anthology_items()))
    log.info(f"Author {person.id} has {numPapers} implicitly or explicitly linked")

    paper_and_namespec = []
    for paper_id in paper_ids:
        paper = anthology.get(paper_id)
        assert paper, f"Unknown item ID: {paper_id}"

        # match the author of the paper by name slug
        matches = [namespec for namespec in paper.namespecs if namespec.id == author_id]
        assert len(matches) == 1, (
            f"In {paper_id}, looking for exactly 1 author with id={author_id}, found: {matches}"
        )
        matched_namespec = matches[0]
        log.info(f"In {paper_id}, matched author {matched_namespec.name}")
        paper_and_namespec.append((paper, matched_namespec))

    numUnlinked = 0

    if keep_only_these_papers:
        # unlink any other papers
        if numPapers > len(paper_and_namespec):
            included_items = list(zip(*paper_and_namespec))[0]
            all_items = list(person.anthology_items())
            for item in all_items:
                if item not in included_items:
                    for ns in item.namespecs:
                        if ns.id == person.id:
                            log.info(f"Unlinking {item.full_id} {ns}")
                            assert ns.orcid is None, "ORCID expected to be None"
                            ns.id = None
                            numUnlinked += 1
    else:  # unlink the specified papers
        for item, ns in paper_and_namespec:
            log.info(f"Unlinking {item.full_id} {ns}")
            assert ns.orcid is None, "ORCID expected to be None"
            ns.id = None
            numUnlinked += 1

    if numUnlinked > 0:
        changes = (
            f"Unlinked {numUnlinked} explicit papers/volumes from author {author_id}"
        )
        log.info(changes)
        anthology.save_all()
        anthology.people.reset()
        person = anthology.get_person(person.id)  # refreshed after reset
        numPapers = len(list(person.anthology_items()))
        log.info(f"Now {numPapers} implicitly or explicitly linked")

    return changes


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG if not args.get("--quiet", False) else log.INFO
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    with warnings.catch_warnings(action="ignore", category=NameSpecResolutionWarning):
        msg = unlink_items(
            author_id=args["AUTHORID"],
            paper_ids=args["PAPERID"],
            keep_only_these_papers=args["--keep"],
        )

        if args["--issue"]:
            msg += f" (closes #{args['--issue']})"
        print(f'Now run>>> git commit -a -m "{msg}"')
