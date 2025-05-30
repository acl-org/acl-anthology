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
    with open(paper_path, 'r', encoding='utf-8') as f:
        papers = yaml.safe_load(f)

    for paper in papers:
        if "archival" not in paper:
            paper["archival"] = True

    # print(f"Loaded {len(papers)} papers from {paper_path}", file=sys.stderr)
    return papers


@click.command()
# add a positional argument for the paper YAML file
@click.argument(
    'paper_yaml',
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
)
@click.argument(
    'full_volume_id',
    type=str,
    required=True,
)
def main(
    paper_yaml: str,
    full_volume_id: str,
):
    anthology_datadir = Path(sys.argv[0]).parent / ".." / "data"
    # anthology = Anthology(
    #     importdir=anthology_datadir, require_bibkeys=False
    # )

    # venue_index = VenueIndex(srcdir=anthology_datadir)
    # venue_keys = [venue["slug"].lower() for _, venue in venue_index.items()]

    # people = AnthologyIndex(srcdir=anthology_datadir)
    # people.bibkeys = load_bibkeys(anthology_datadir)

    # Load the papers.yaml file, skipping non-archival papers
    papers = [p for p in parse_paper_yaml(paper_yaml) if p["archival"]]
    print(f"Found {len(papers)} archival papers", file=sys.stderr)

    for paper in papers:
        print("PAPER:", paper['id'], file=sys.stderr)
        for author in paper['authors']:
            print(
                f"  {author['first_name']} {author['last_name']} ({author.get('institution', '')})",
                file=sys.stderr,
            )

    collection_id, volume_name = full_volume_id.split('-')

    # open the paper XML file
    collection_file = anthology_datadir / 'xml' / f'{collection_id}.xml'
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

    assert len(papers) == len(
        volume_node.findall('./paper')
    ), f"Number of papers in YAML ({len(papers)}) does not match number in XML ({len(volume_node.findall('./paper'))})"

    for paper, paper_node in zip(papers, volume_node.findall('./paper')):
        # paper_num = int(paper["id"])
        paper_num = int(paper_node.attrib['id'])
        print(f"PAPER: YAML={paper_num}", file=sys.stderr)

        # assert paper_num == paper_id_xml, (
        #     f"Paper ID mismatch: YAML={paper_num}, XML={paper_id_xml}"
        # )

        def get_author_xml(author_xml):
            name = ""
            if (first := author_xml.find('first')) is not None:
                name += first.text or ""
            if (last := author_xml.find('last')) is not None:
                if name:
                    name += " "
                name += last.text or ""
            return name

        for author_yaml, author_node in zip(
            paper['authors'], paper_node.findall('./author')
        ):
            print(
                f"- Author YAML={author_yaml['first_name']} {author_yaml['last_name']} XML={get_author_xml(author_node)}",
                file=sys.stderr,
            )
            if orcid := author_yaml.get('orcid'):
                # grab ORCID pattern from orcid: \d{4}-\d{4}-\d{4}-\d{3}[0-9X]
                orcid_pattern = r'\d{4}-\d{4}-\d{4}-\d{3}[0-9X]'
                match = re.match(orcid_pattern, orcid)
                if match:
                    # If the ORCID is in the expected format, use it directly
                    orcid = match.group(0)
                else:
                    print(f"Invalid ORCID format: {orcid}", file=sys.stderr)
                    continue

                author_node.attrib['orcid'] = orcid

    indent(root_node)
    tree = etree.ElementTree(root_node)
    tree.write(collection_file, encoding='UTF-8', xml_declaration=True, with_tail=True)


if __name__ == '__main__':
    main()
