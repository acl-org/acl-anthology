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
This script returns a list of all authors whose papers are entirely within the set
of provided volume IDs. The motivation of the script is to identify new first authors
at a conference, which is accomplished by providing a list of the newest volumes, e.g.,

e.g.,

    ./find_new_authors.py 2025.acl-{long,short,demo,srw,tutorials,industry} 2025.findings-acl

There is also a flag, --first-only, which will return only the authors who (a) are first authors
in the provided volume set and (b) have no papers outside the provided set.
"""

from collections import defaultdict
from pathlib import Path
import sys
from acl_anthology import Anthology



def find_new_people(volume_ids, first_only=False):
    """
    Given a list of volumes, returns people who have authored papers only within
    that list. If first_only==True, only new first-authors are returned.
    """

    anthology = Anthology(datadir=Path(__file__).parent / ".." / "data")
    new_people = defaultdict(list)
    # setup_rich_logging()

    # First, build a list of the people publishing in the provided volume set.
    for volume_id in volume_ids:
        volume = anthology.get_volume(volume_id)
        if not volume:
            print(f"Volume {volume_id} not found in the anthology.", file=sys.stderr)
            continue

        for paper in volume.papers():
            for author in paper.authors:
                person = anthology.resolve(author)
                new_people[person].append(paper.full_id)
                # If we're only looking for first authors, we can stop here
                if first_only:
                    break

    def has_no_papers_outside_volumes(person):
        """Return true if all a person's papers are inside the specified volume set."""
        return all(paper.parent.full_id in volume_ids for paper in person.papers())

    # From the generated list of people who have a paper _inside_ the volume set,
    # filter out all those who have papers outside the volume set.
    return {
        person: item_ids
        for (person, item_ids) in new_people.items()
        if has_no_papers_outside_volumes(person)
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Find new authors in specified volumes")
    parser.add_argument("volumes", nargs="+", help="List of volumes to consider")
    parser.add_argument(
        "--first-only", "-f", action="store_true", help="Only return new first authors"
    )
    args = parser.parse_args()

    new_people = find_new_people(args.volumes, args.first_only)
    for person in new_people:
        papers = [f"https://aclanthology.org/{id}" for id in new_people[person]]
        print(
            person.canonical_name.as_last_first(),
            f"https://aclanthology.org/people/{person.id}",
            *papers,
            sep="\t",
        )
