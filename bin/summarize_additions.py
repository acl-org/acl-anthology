#! /usr/bin/env python3
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

"""
Takes a git diff on STDIN and pulls out all the attachments and revisions that
were produced, for distribution.

Usage:

  git diff 17fc308a97693a0ce6ec108e398871facb6be78b e9da44eb38de2adfe1bc3cd662ca6e17f124571c | ./bin/summarize_additions.py  | pbcopy

Prints a list to STDOUT.
"""

import argparse
import inflect
import os
import re
import sys

from anthology import Anthology
from anthology.data import ANTHOLOGY_ID_REGEX, ANTHOLOGY_URL

from collections import defaultdict


def main(args):
    scriptdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    anthology = Anthology(importdir=scriptdir)

    attachments = defaultdict(list)
    revisions = []
    errata = []
    for line in sys.stdin:
        if not line.startswith("+"):
            continue

        line = line[1:].strip()
        if line.startswith("<attachment"):
            try:
                match_str = rf'<attachment type="(\w+)">({ANTHOLOGY_ID_REGEX}).*'
                match = re.match(match_str, line)
                attach_type, anthology_id = match.groups()
            except:
                print(f"* Couldn't match '{match_str}' to '{line}'", file=sys.stderr)

            attachments[attach_type].append(
                (
                    anthology.papers[anthology_id].get_title('plain'),
                    ANTHOLOGY_URL.format(anthology_id),
                )
            )

        elif line.startswith("<revision"):
            try:
                match_str = rf'<revision.*href="({ANTHOLOGY_ID_REGEX}).*>.*'
                match = re.match(match_str, line)
                anthology_id = match.group(1)
            except:
                print(f"* Couldn't match '{match_str}' to '{line}'", file=sys.stderr)

            paper = anthology.papers[anthology_id]
            explanation = paper.attrib["revision"][-1]["explanation"]

            revisions.append(
                (
                    paper.get_title("plain"),
                    ANTHOLOGY_URL.format(anthology_id),
                    explanation,
                )
            )

        elif line.startswith("<errat"):
            try:
                match_str = rf"<errat.*?>({ANTHOLOGY_ID_REGEX}).*"
                match = re.match(match_str, line)
                anthology_id = match.group(1)
            except:
                print(f"* Couldn't match '{match_str}' to '{line}'", file=sys.stderr)

            errata.append(
                (
                    anthology.papers[anthology_id].get_title('plain'),
                    ANTHOLOGY_URL.format(anthology_id),
                )
            )

    inflector = inflect.engine()
    for attach_type, attachments in attachments.items():
        phrase = inflector.a(attach_type)
        print(f"\nAdded {phrase}:")
        for title, url in attachments:
            print("-", title, "\n ", url, "\n")

    if len(revisions):
        print(f"\nRevisions:")
        for title, url, explanation in revisions:
            print("-", title, "\n ", url, "\n ", explanation, "\n")

    if len(errata):
        print(f"\nErrata:")
        for title, url in errata:
            print("-", title, "\n ", url, "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    main(args)
