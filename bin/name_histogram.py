#!/usr/bin/env python3
#
# Copyright 2026 Matt Post
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

"""Summarize how many people share each name in the ACL Anthology."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from acl_anthology import Anthology


def main() -> None:
    # get the datadir relative to this script (up two)
    datadir = Path(__file__).parent.parent.parent / "data"
    anthology = Anthology(datadir=datadir)

    # Building the person index parses the entire Anthology once.
    anthology.people.load()
    name_index = anthology.people.by_name

    histogram = Counter(len(person_ids) for person_ids in name_index.values())

    # print the histogram
    if not histogram:
        print("No names found.")
        return

    max_names = max(histogram.values())
    scale = max(max_names // 50, 1)  # keep bars readable in plain text
    print("# people   count   visual")
    for shared_by in sorted(histogram):
        name_count = histogram[shared_by]
        bar = "#" * max(name_count // scale, 1)
        print(f"{shared_by:>8}{name_count:>8}   {bar}")

    # print the top names
    shared_names = [(name, len(person_ids)) for name, person_ids in name_index.items()]
    shared_names.sort(key=lambda item: (-item[1], item[0].as_last_first()))

    print()
    print("Names with counts:")
    for name, count in shared_names:
        print(count, name.as_last_first(), sep="\t")


if __name__ == "__main__":
    main()
