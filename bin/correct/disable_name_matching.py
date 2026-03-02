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
Takes a list of existing author IDs and sets the `disable_name_matching` flag for each.

Usage: disable_name_matching.py AUTHORID ...

Arguments:
    AUTHORID            One or more author IDs
"""


import warnings
import logging as log
from docopt import docopt

from acl_anthology import Anthology


def disable_name_matching(author_ids):
    changes = 0
    anthology = Anthology.from_within_repo()

    for author_id in author_ids:
        person = anthology.get_person(author_id)
        if person is None:
            log.error(f'The author ID {author_id} cannot be found. Skipping')
        else:
            log.info(f'Disabling name matching for {author_id} ({person.orcid})')
            person.disable_name_matching = True
            changes += 1

    if changes:
        anthology.save_all()

    return changes


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG if not args.get("--quiet", False) else log.INFO
    log.basicConfig(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)
    # tracker = setup_rich_logging(level=log_level)

    with warnings.catch_warnings(action="ignore"):  # NameSpecResolutionWarning
        disable_name_matching(author_ids=args['AUTHORID'])
