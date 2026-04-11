#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright 2025 Matt Post

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

---
Reads an aclpub2 directory that has been already ingested and adds
ORCIDS to authors.

    python bin/ingest_orcids.py /path/to/papers.yml volume_id

e.g.,

    python bin/ingest_orcids.py 2025-naacl-long.yml 2025.naacl-long
"""

import click
import yaml
import sys
import os
import re
from pathlib import Path
import lxml.etree as etree
from typing import Dict, List

from anthology.utils import indent


def parse_paper_yaml(paper_path: str) -> List[Dict[str, str]]:
    """
    Reads papers.yml to get metadata. Skips non-archival papers.
    """
    # load the YAML file
    papers = []
    if not os.path.exists(paper_path):
        print(f"No such file: {paper_path}", file=sys.stderr)
        sys.exit(1)
    with open(paper_path, "r", encoding="utf-8") as f:
        papers = yaml.safe_load(f)

    for paper in papers:
        if "archival" not in paper:
            paper["archival"] = True

    # print(f"Loaded {len(papers)} papers from {paper_path}", file=sys.stderr)
    return papers


@click.command()
# add a positional argument for the paper YAML file
@click.argument(
    "paper_yaml",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
)
@click.argument(
    "full_volume_id",
    type=str,
    required=False,
)
def main(
    paper_yaml: str,
    full_volume_id: str = None,
):
    anthology_datadir = Path(sys.argv[0]).parent / ".." / "data"
    # anthology = Anthology(
    #     importdir=anthology_datadir, require_bibkeys=False
    # )

    # venue_index = VenueIndex(srcdir=anthology_datadir)
    # venue_keys = [venue["slug"].lower() for _, venue in venue_index.items()]

    # people = AnthologyIndex(srcdir=anthology_datadir)
    # people.bibkeys = load_bibkeys(anthology_datadir)

    if full_volume_id is None:
        full_volume_id = Path(paper_yaml).name.replace(".yaml", "")
        print(f"Taking full volume ID from file name: {full_volume_id}", file=sys.stderr)

    # Load the papers.yaml file, skipping non-archival papers
    papers = [p for p in parse_paper_yaml(paper_yaml) if p["archival"]]
    # print(f"Found {len(papers)} archival papers", file=sys.stderr)

    # for paper in papers:
    # print("PAPER:", paper['id'], file=sys.stderr)
    # for author in paper['authors']:
    #     print(
    #         f"  {author['first_name']} {author['last_name']} ({author.get('institution', '')})",
    #         file=sys.stderr,
    #     )

    collection_id, volume_name = full_volume_id.split("-")

    # open the paper XML file
    collection_file = anthology_datadir / "xml" / f"{collection_id}.xml"
    if not os.path.exists(collection_file):
        print(f"No such collection file {collection_file}", file=sys.stderr)
        sys.exit(1)

    root_node = etree.parse(collection_file).getroot()
    volume_node = root_node.find(f"./volume[@id='{volume_name}']")
    if volume_node is None:
        print(
            f"No volume node with id '{volume_name}' found in {collection_file}",
            file=sys.stderr,
        )
        sys.exit(1)

    assert len(papers) == len(volume_node.findall("./paper")), (
        f"Number of papers in YAML ({len(papers)}) does not match number in XML ({len(volume_node.findall('./paper'))})"
    )

    num_added = 0
    for paper, paper_node in zip(papers, volume_node.findall("./paper")):
        # paper_num = int(paper["id"])
        # paper_num = int(paper_node.attrib['id'])
        # print(f"PAPER: YAML={paper_num}", file=sys.stderr)

        def get_author_name_xml(author_xml):
            """
            Returns "Last, First Name" for matching.
            """
            names = []
            if (first := author_xml.find("first")) is not None:
                try:
                    names.append(first.text.lower())
                except AttributeError:
                    names.append("")
            else:
                names.append("")
            if (last := author_xml.find("last")) is not None:
                names.append(last.text.lower())
            else:
                names.append("")

            return tuple(names)

        yaml_authors = paper["authors"]
        xml_authors = paper_node.findall("./author")

        if len(yaml_authors) != len(xml_authors):
            print(
                f"* Author count mismatch for paper {paper['id']}: YAML={len(yaml_authors)} XML={len(xml_authors)}",
                file=sys.stderr,
            )
            continue

        def match_names(yaml_name_tuple, xml_name_tuple):
            """Match a YAML name tuple to the XML name tuple.

            Basic sanity check on name matching: we ensure that the YAML last name
            ends the XML string that concatenates names in both directions.

            e.g.,

            YAML: "Post"
            XML: ("Matt Post", "Post Matt")
            match: True

            We do both directions because of issues with Chinese names which have inconsistent
            conventions.
            """

            xml_name_forward = f"{xml_name_tuple[0]} {xml_name_tuple[1]}"
            xml_name_reverse = f"{xml_name_tuple[1]} {xml_name_tuple[0]}"

            yaml_first, yaml_last = yaml_name_tuple

            return xml_name_forward.endswith(yaml_last) or xml_name_reverse.endswith(
                yaml_last
            )

        for author_yaml, author_node in zip(
            paper["authors"], paper_node.findall("./author")
        ):
            # Check that the author names match
            # We want to do this robustly, since author order may have changed
            yaml_name_tuple = (
                author_yaml["first_name"].lower(),
                author_yaml["last_name"].lower(),
            )
            yaml_name = yaml_name_tuple[0] + " " + yaml_name_tuple[1]

            if not match_names(yaml_name_tuple, get_author_name_xml(author_node)):
                print(
                    f"* Author name mismatch for paper {paper['id']}: YAML={yaml_name} XML={get_author_name_xml(author_node)}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"- Author YAML={yaml_name} XML={get_author_name_xml(author_node)}",
                    file=sys.stderr,
                )
            if orcid := author_yaml.get("orcid"):
                # grab ORCID pattern from orcid: \d{4}-\d{4}-\d{4}-\d{3}[0-9X]
                orcid_pattern = r"\d{4}-\d{4}-\d{4}-\d{3}[0-9X]"
                match = re.search(orcid_pattern, orcid)
                if match:
                    # If the ORCID is in the expected format, use it directly
                    orcid = match.group(0)
                    num_added += 1
                else:
                    print(f"Invalid ORCID format: {orcid}", file=sys.stderr)
                    continue

                author_node.attrib["orcid"] = orcid

    indent(root_node)
    tree = etree.ElementTree(root_node)
    tree.write(collection_file, encoding="UTF-8", xml_declaration=True, with_tail=True)
    print(
        f"Added {num_added} ORCIDs for {full_volume_id} to {collection_file}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
