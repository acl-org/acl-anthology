#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add an author ID to NameSpecification entries using the acl_anthology module.

This script finds author/editor name specifications matching a given
first/last name where no explicit ID is present, sets the provided ID, and
saves the affected collection XML files.

Usage:
    ./add_author_id.py <id> --last-name <Last> [--first-name <First>] [--data-dir <path>]
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import chain
from typing import Set

from acl_anthology.anthology import Anthology
from acl_anthology.people import Name


def main(args: argparse.Namespace) -> None:
    anthology = Anthology(args.data_dir, verbose=True)

    last_name, first_name = args.name.split(",") if "," in args.name else (args.name, None)

    people = anthology.find_people(args.name)
    if not people:
        print(f"No person found matching name {args.name}")

    # find the person with the non-explicit ID
    for person in people:
        if not person.is_explicit:
            break
    print(f"Found person: {person}")

    if not person:
        print(f"No person found matching name {args.name} with an explicit ID")
        return

    for paper in person.papers():
        print("PAPER", paper.full_id)
        authors = paper.get_editors() if paper.is_frontmatter else paper.authors
        for author in authors:
            if author.name in person.names:
                print("-> Found", author)
                author.id = args.id
        # collection_paper_map[paper.collection_id].append(paper.full_id)

    # save the anthology (doesn't currently work)
    anthology.save_all()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Add an author ID to all of an author's papers")
    parser.add_argument("id", help="Author ID to add")
    parser.add_argument("--name", "-n", help="Author's name (last[, first])")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Path to anthology data directory (default: ../data relative to repository root)",
    )
    args = parser.parse_args()
    # Normalize data_dir to a Path string used by Anthology
    # If the user supplies a path, trust it; otherwise compute relative to this script
    if args.data_dir is None:
        from pathlib import Path
        args.data_dir = str(Path(__file__).parent.parent / "data")

    main(args)
