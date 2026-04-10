#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Matt Post <post@cs.jhu.edu>
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
Adds a single paper to an existing volume in the ACL Anthology.

Input is a YAML file with paper metadata in aclpub2 format:

    title: "Paper Title with {CaseProtected} Words"
    authors:
    - first_name: Jane
      last_name: Doe
      orcid: 0000-0001-2345-6789  # optional
    - first_name: John
      last_name: Smith
    abstract: "The abstract text..."
    language: eng  # optional, ISO 639-2
    pages: "1-10"  # optional

The paper ID will be auto-generated from the volume ID (e.g., "2025.isa-1").

Usage:
    python bin/add_paper.py 2025.isa-1 paper.yaml
"""

import click
import os
import shutil
import sys
import yaml
from datetime import datetime
from pathlib import Path

from acl_anthology import Anthology
from acl_anthology.files import PDFReference
from acl_anthology.people import Name, NameSpecification as NameSpec
from acl_anthology.text import MarkupText

from fixedcase.protect import protect


def parse_authors(authors_data):
    """Convert aclpub2-style author dicts to NameSpecification objects.

    aclpub2 uses first_name/last_name, while the Anthology library uses first/last.
    """
    namespecs = []
    for author in authors_data:
        first = author.get("first_name") or author.get("first")
        last = author.get("last_name") or author.get("last")
        orcid = author.get("orcid")
        namespecs.append(NameSpec(Name(first=first, last=last), orcid=orcid))

    return namespecs


@click.command()
@click.argument("volume_id")
@click.argument("yaml_file", type=click.Path(exists=True))
@click.option(
    "--anthology-dir",
    default=os.path.join(os.path.dirname(sys.argv[0]), ".."),
    help="Root path of the ACL Anthology repo",
)
@click.option(
    "--ingest-date",
    default=f"{datetime.now().year}-{datetime.now().month:02d}-{datetime.now().day:02d}",
    help="Ingestion date (default: today)",
)
@click.option(
    "--pdf",
    default=None,
    type=click.Path(exists=True),
    help="Path to the paper PDF; will be copied to the anthology-files tree",
)
@click.option(
    "--pdfs-dir",
    default=os.path.join(os.environ["HOME"], "anthology-files", "pdf"),
    help="Root path for PDF file storage (default: ~/anthology-files/pdf)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print what would be done without saving",
)
def main(volume_id, yaml_file, anthology_dir, ingest_date, pdf, pdfs_dir, dry_run):
    """Add a paper from YAML_FILE to an existing Anthology volume.

    VOLUME_ID is the ID of the volume (e.g., "2025.isa-1") to which the paper will be added.
    """
    # Load the YAML input
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)

    # Support both a single paper dict and a list with one paper
    if isinstance(data, list):
        if len(data) != 1:
            raise click.UsageError(
                f"YAML file must contain exactly one paper, found {len(data)}"
            )
        data = data[0]

    # Load the Anthology and build the people index so that
    # known authors are properly resolved (matched by name slug)
    anthology = Anthology.from_within_repo()

    volume = anthology.get_volume(volume_id)
    if volume is None:
        raise click.UsageError(
            f"Volume for paper '{volume_id}' not found in the Anthology"
        )

    collection = volume.parent

    # Validate required fields
    title_text = data.get("title")
    if not title_text:
        raise click.UsageError("Paper must have a 'title' field")

    authors_data = data.get("authors", [])
    if not authors_data:
        raise click.UsageError("Paper must have at least one author")

    # Build kwargs for create_paper
    create_kwargs = {}
    if data.get("abstract"):
        create_kwargs["abstract"] = MarkupText.from_latex_maybe(
            str(data["abstract"]).strip()
        )
    if data.get("pages"):
        create_kwargs["pages"] = str(data["pages"])
    if data.get("language"):
        create_kwargs["language"] = str(data["language"])

    # Create the paper (this handles case normalization, namespec
    # ingestion for ORCIDs, and person index updates)
    paper_obj = volume.create_paper(
        title=MarkupText.from_latex_maybe(str(title_text)),
        authors=parse_authors(authors_data),
        **create_kwargs,
    )

    # Apply case protection to the title
    xml_title = paper_obj.title.to_xml("title")
    protect(xml_title)
    paper_obj.title = MarkupText.from_xml(xml_title)

    # Copy PDF and set the url reference
    if pdf is not None:
        venue_dir = Path(pdfs_dir) / volume.collection_id.split(".")[1]
        destination = venue_dir / f"{paper_obj.full_id}.pdf"
        if not dry_run:
            venue_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf, destination)
            paper_obj.pdf = PDFReference.from_file(destination)
            print(f"  PDF: {destination}", file=sys.stderr)
        else:
            print(f"  PDF: {destination} (would copy)", file=sys.stderr)

    print(f"Created paper {paper_obj.full_id}", file=sys.stderr)
    print(f"  Title: {paper_obj.title.as_text()}", file=sys.stderr)
    for ns in paper_obj.authors:
        id_str = f" (id={ns.id})" if ns.id else ""
        print(f"  Author: {ns.name.as_first_last()}{id_str}", file=sys.stderr)
    print(f"  Bibkey: {paper_obj.bibkey}", file=sys.stderr)

    if dry_run:
        print("Dry run: not saving changes", file=sys.stderr)
    else:
        collection.save()
        print(f"Saved to {collection.path}", file=sys.stderr)


if __name__ == "__main__":
    main()
