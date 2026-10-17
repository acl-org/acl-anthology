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
  unlink_items.py [--issue NUM] [--keep] [--orid ORID] [--remove-orcid] AUTHORID PAPERID ...

Arguments:
    AUTHORID            Currently verified author ID.
    PAPERID             List of paper or volume IDs associated with the verified author.
                        '*' to target all items under the author (possibly subject to other filters).

Options:
    -h --help           Show this help message.
    --issue NUM         GitHub issue number to include in commit message.
    --keep              Keep only the specified items; unlink all others.
    --orid ORID         OpenReview ID to use as a filter.
    --remove-orcid      For any paper being unlinked, remove the ORCID attribute if present on the namespec.
"""

import logging as log
from docopt import docopt
from typing import Optional

from acl_anthology import Anthology
from acl_anthology.collections import Paper
from acl_anthology.utils.logging import setup_rich_logging


def unlink_items(author_id, paper_ids: Optional[list[str]], keep_only_these_papers=False, openreview=None, remove_orcid=False):
    changes = ""
    anthology = Anthology.from_within_repo(
        suppress_warnings=("NameSpecResolutionWarning",)
    )

    person = anthology.get_person(author_id)
    items = [(paper.full_id, paper) for paper in person.anthology_items()]

    numPapers = len(items)
    log.info(f"Author {person.id} has {numPapers} implicitly or explicitly linked")

    if paper_ids:
        # Filter target items by explicit IDs
        items = []
        for paper_id in paper_ids:
            paper = anthology.get(paper_id)
            assert paper, f"Unknown item ID: {paper_id}"
            items.append((paper_id, paper))

    paper_and_namespec = []
    for paper_id, paper in items:
        # match the author of the paper by name slug
        namespecs = paper.editors if isinstance(paper, Paper) and paper.is_frontmatter else paper.namespecs
        matches = [namespec for namespec in namespecs if namespec.id == author_id]
        assert len(matches) == 1, (
            f"In {paper_id}, looking for exactly 1 author with id={author_id}, found: {matches}"
        )
        matched_namespec = matches[0]
        if openreview and matched_namespec.openreview != openreview:
            continue
        log.info(f"In {paper_id}, matched author {matched_namespec.name} openreview={openreview or ''!r}")
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
                            if remove_orcid:
                                ns.orcid = None
                            else:
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

    assert args['PAPERID'], args['PAPERID']
    targets = None if args['PAPERID'] == ["*"] else args['PAPERID']

    msg = unlink_items(
        author_id=args["AUTHORID"],
        paper_ids=targets,
        keep_only_these_papers=args["--keep"],
        openreview=args["--orid"],
        remove_orcid=args["--remove-orcid"],
    )

    if args["--issue"]:
        msg += f" (closes #{args['--issue']})"
    print(f'Now run>>> git commit -a -m "{msg}"')
