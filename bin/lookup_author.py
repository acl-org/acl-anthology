#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Look up author names in the ACL Anthology and print their person IDs.

Reads author names from STDIN (one per line) and prints results to STDOUT.

Usage:
    echo "Paul Rayson" | ./lookup_author.py
    cat editors.txt | ./lookup_author.py
    ./lookup_author.py < editors.txt

Copyright 2026 Matt Post.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from acl_anthology.anthology import Anthology
from acl_anthology.people.name import Name


def main(args: argparse.Namespace) -> None:
    anthology = Anthology(args.data_dir, verbose=True)
    anthology.load_all()

    for line in sys.stdin:
        name_str = line.strip()
        if not name_str:
            continue

        parts = name_str.rsplit(" ", 1)
        if len(parts) == 2:
            first, last = parts
        else:
            first, last = None, parts[0]

        name = Name(first=first, last=last)
        people = anthology.people.get_by_name(name)

        if people:
            for person in people:
                pid = person.id
                cname = person.canonical_name
                print(f"{name_str}\t{pid}\t{cname.first}\t{cname.last}")
        else:
            print(f"{name_str}\tNOT_FOUND")


if __name__ == "__main__":
    scriptdir = Path(__file__).resolve().parent
    default_datadir = scriptdir / ".." / "data"

    parser = argparse.ArgumentParser(
        description="Look up author names in the ACL Anthology."
    )
    parser.add_argument(
        "--data-dir",
        default=default_datadir,
        type=Path,
        help="Path to the Anthology data directory.",
    )
    args = parser.parse_args()
    main(args)
