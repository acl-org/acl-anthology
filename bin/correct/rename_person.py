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
For an existing verified author, change the author ID to a new one.
This will update any papers explicitly linked to the author.
The new ID cannot belong to an existing verified author
(but see merge_verified.py).

Usage:
  rename_person.py [--issue NUM] AUTHORID NEWID

Arguments:
    AUTHORID            Currently verified author ID.
    NEWID               New ID to assign to the Person.

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


def rename_person(author_id, new_id):
    changes = f"Renaming author ID: {author_id} -> {new_id}"
    anthology = Anthology.from_within_repo()

    person = anthology.get_person(author_id)
    assert person is not None, f"Could not find person: {author_id}"
    person.change_id(new_id)

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
        msg = rename_person(author_id=args["AUTHORID"], new_id=args["NEWID"])

        if args["--issue"]:
            msg += f" (closes #{args['--issue']})"
        print(f'Now run>>> git commit -a -m "{msg}"')
