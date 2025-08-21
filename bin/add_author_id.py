#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add an author ID to NameSpecification entries using the acl_anthology module.

This script adds the name ID to all papers matching the first and last name.

Usage:
    ./add_author_id.py <id> "Last name[, First name]"
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import chain
from typing import Set
from pathlib import Path

from acl_anthology.anthology import Anthology

# old library since we're still editing XML files
from anthology.utils import indent
import lxml.etree as ET


def main(args: argparse.Namespace) -> None:
    anthology = Anthology(args.data_dir, verbose=True)

    last_name, first_name = args.name.split(", ") if ", " in args.name else (args.name, None)

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

    # Build a collection of the set of papers to modify within each XML file
    collection_to_paper_map = defaultdict(list)
    for paper in person.papers():
        collection_to_paper_map[paper.collection_id].append(paper.full_id_tuple)

    print(collection_to_paper_map)

    # Now iterate over those files and the papers within them
    for collection_id, paper_id_tuples in collection_to_paper_map.items():
        xml_file = Path(args.data_dir) / "xml" / f"{collection_id}.xml"

        tree = ET.parse(xml_file)

        for paper_tuple in paper_id_tuples:
            _, volume_id, paper_id = paper_tuple

            # Get the paper
            paper_xml = tree.getroot().find(f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']")

            for author_xml in chain(
                paper_xml.findall("./author"), paper_xml.findall("./editor")
            ):
                if "id" in author_xml.attrib:
                    continue
                try:
                    author_first_name = author_xml.find("./first").text
                except AttributeError:
                    author_first_name = None
                author_last_name = author_xml.find("./last").text

                print("Found", first_name, last_name)

                if author_last_name == last_name and author_first_name == first_name:
                    paper_id = (
                        paper_xml.attrib["id"] if paper_xml.text == "paper" else "0"
                    )
                    anth_id = f"{xml_file}/{paper_id}"
                    print(f"Adding {args.id} to {anth_id}...")
                    author_xml.attrib["id"] = args.id

        indent(tree.getroot())
        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)

    """
    Once we have the module published, we should be able to modify this to use
    it to write the changed XML files, instead of the above.    
    """
    # for paper in person.papers():
    #     print("PAPER", paper.full_id)
    #     authors = paper.get_editors() if paper.is_frontmatter else paper.authors
    #     for author in authors:
    #         if author.name in person.names:
    #             print("-> Found", author)
    #             author.id = args.id
    #     # collection_paper_map[paper.collection_id].append(paper.full_id)

    # # save the anthology (doesn't currently work)
    # anthology.save_all()


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
        args.data_dir = str(Path(__file__).parent.parent / "data")

    main(args)
