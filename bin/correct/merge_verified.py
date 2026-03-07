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
Given IDs for two or more existing verified Persons, merge them into a single Person,
updating any explicitly linked papers.
Specifically, the 2nd/subsequent listed authors will be merged into the first,
so the resulting author ID will be the same as the first one listed, and that Person's
canonical name will remain canonical for the merged Person.

Usage:
  merge_verified.py [--issue NUM] AUTHORID ...

Arguments:
    AUTHORID            Currently verified author ID.

Options:
    -h --help           Show this help message.
    --issue NUM         GitHub issue number to include in commit message.
"""

import warnings
import logging as log
from docopt import docopt

from acl_anthology import Anthology
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.utils.logging import setup_rich_logging


def merge_verified(author_ids):
    assert len(author_ids) > 1, 'Multiple author IDs required'

    author_id = author_ids[0]
    changes = f'Merging verified Persons under {author_id}'
    anthology = Anthology.from_within_repo()

    person = anthology.get_person(author_id)
    assert person is not None, f'Could not find person: {author_id}'
    assert person.is_explicit, f'Person is unverified: {author_id}'

    for author_id2 in author_ids[1:]:
        person2 = anthology.get_person(author_id2)
        assert person2 is not None, f'Could not find person: {author_id2}'
        assert person2.is_explicit, f'Person is unverified: {author_id2}'

        assert False, 'Not implemented'
        # TODO: merge person2 into person. awaiting library support for the merge
        # ensure the merging copies any metadata attached to the Person:
        # ORCID, degree, comment, etc.

    anthology.save_all()

    return changes


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG if not args.get("--quiet", False) else log.INFO
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    with warnings.catch_warnings(action="ignore", category=NameSpecResolutionWarning):

        msg = merge_verified(author_ids=args['AUTHORID'])

        if args['--issue']:
            msg += f' (closes #{args["--issue"]})'
        print(f'Now run>>> git commit -a -m "{msg}"')
