#!/usr/bin/env python3

"""
Takes a list of collection IDs as arguments, and outputs a TSV
(name, Anthology ID, paper title) containing every person who
is the first author of a paper and has no other papers in the
Anthology.

Place in acl-anthology/bin and run

   ./bin/new-authors.py 2020.acl

which returns all first authors who had their first paper at ACL
2020. Note that this doesn't ignore future volumes, so if run in
2024, this will no longer work for 2020.

Author: Matt Post
"""

import os
import sys

from anthology import Anthology
from anthology.utils import deconstruct_anthology_id

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("collections", nargs="+")
    args = parser.parse_args()

    anthology = Anthology(
        importdir=os.path.join(os.path.dirname(sys.argv[0]), "..", "data")
    )

    # header
    print("name", "id", "title", sep="\t")

    for id_, paper in anthology.papers.items():
        collection_id, volume_name, paper_id = deconstruct_anthology_id(id_)
        if collection_id in args.collections:
            authors = paper.attrib.get("author", [])
            if len(authors) > 0:
                # "authors" is a list of ("last name || first name", name-id or None) tuples
                first_author = authors[0][0]
                authors_papers = list(
                    anthology.people.name_to_papers[first_author].values()
                )
                authors_papers = authors_papers[0] + authors_papers[1]
                if len(authors_papers) == 1:
                    print(first_author.full, id_, paper.get_title('text'), sep="\t")
