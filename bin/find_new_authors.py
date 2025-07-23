#!/usr/bin/env python3
# Copyright 2025 Matt Post <post@cs.jhu.edu>
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
This script returns a list of all authors who have at least one paper outside the
provided list of volume IDs. The purpose is to find new authors, i.e., by providing
a list of the newest volumes.

e.g., 

    ./find_new_authors.py 2025.acl-{long,short,demo,srw,tutorials,industry} 2025.findings-acl

will output all authors who have a paper in at least one of the above volumes and nowhere else.
"""

from collections import defaultdict
from pathlib import Path
import sys
from acl_anthology import Anthology


def find_new_people(volumes):
    anthology = Anthology(datadir=Path(__file__).parent / ".." / "data")
    new_people = defaultdict(list)
    # setup_rich_logging()

    for volume_name in volumes:
        volume = anthology.get_volume(volume_name)
        if not volume:
            print(f"Volume {volume_name} not found in the anthology.", file=sys.stderr)
            continue

        for paper in volume.papers():
            if not paper.authors:
                continue

            # Check if the author is new in this volume
            for author in paper.authors:
                person = anthology.resolve(author)
                new_people[person].append(paper.full_id)

    # Now, iterate through the new authors
    new_people_list = list(new_people.keys())
    for person in new_people_list:
        new_papers = new_people[person]
        for existing_paper_tuple in person.item_ids:
            paper = anthology.get_paper(existing_paper_tuple)
            if not paper:
                # print(f"Paper {existing_paper_tuple} not found for author {author.name}.", file=sys.stderr)
                continue
            full_id = paper.full_id
            if full_id not in new_papers:
                # This author has papers outside the specified volumes
                del new_people[person]
                break

    return new_people


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Find new authors in specified volumes")
    parser.add_argument("volumes", nargs="+", help="List of volumes to consider")
    args = parser.parse_args()

    new_people = find_new_people(args.volumes)
    for person in new_people:
        papers = [f"https://aclanthology.org/{id}" for id in new_people[person]]
        print(
            person.canonical_name.as_last_first(),
            f"https://aclanthology.org/people/{person.id}",
            *papers,
            sep="\t",
        )
