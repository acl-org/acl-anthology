#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Matt Post <post@cs.jhu.edu>
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
Used to add revisions to the Anthology.
Assumes all files have a base format like ANTHOLOGY_ROOT/P/P18/P18-1234.pdf format.
The revision process is as follows.

- The original paper is named as above.
- When a first revision is created, the original paper is archived to PYY-XXXXv1.pdf.
- The new revision is copied to PYY-XXXXvN, where N is the next revision ID (usually 2).
  The new revision is also copied to PYY-XXXX.pdf.
  This causes it to be returned by the anthology when the base paper format is queried.

Usage:

  add_revision.py [-e] paper_id URL_OR_PATH.pdf "Short explanation".

`-e` denotes erratum instead of revision.
By default, a dry run happens.
When you are ready, add `--do`.
"""

import argparse
import filetype
import os
import shutil
import sys
import tempfile

from anthology.utils import (
    deconstruct_anthology_id,
    make_simple_element,
    indent,
    compute_hash_from_file,
    infer_url,
    retrieve_url,
    get_pdf_dir,
    get_xml_file,
)

import lxml.etree as ET

from datetime import datetime


def validate_file_type(path):
    """Ensure downloaded file mime type matches its extension (e.g., PDF)"""
    detected = filetype.guess(path)
    if detected is None or not detected.mime.endswith(detected.extension):
        mime_type = 'UNKNOWN' if detected is None else detected.mime
        print(
            f"FATAL: file {path} has MIME type {mime_type}",
            file=sys.stderr,
        )
        sys.exit(1)


def add_revision(
    anth_id, pdf_path, explanation, change_type="revision", dry_run=True, date=None
):
    """
    Takes an Anthology ID. It then adds a revision to the Anthology XML,
    updating and writing the XML file, and copies the PDFs into place.
    For PDFs, the revised PDF is saved to {anth_id}.pdf and {anth_id}v{version}.pdf.
    For the first revision, we first copy {anth_id}.pdf to {anth_id}v1.pdf.
    """
    if date is None:
        now = datetime.now()
        date = f"{now.year}-{now.month:02d}-{now.day:02d}"

    def maybe_copy(file_from, file_to):
        if not dry_run:
            print("-> Copying from {} -> {}".format(file_from, file_to), file=sys.stderr)
            shutil.copy(file_from, file_to)
            os.chmod(file_to, 0o644)
        else:
            print(
                "-> DRY RUN: Copying from {} -> {}".format(file_from, file_to),
                file=sys.stderr,
            )

    # The new version
    revno = None

    change_letter = "e" if change_type == "erratum" else "v"

    checksum = compute_hash_from_file(pdf_path)

    # Files for old-style IDs are stored under anthology-files/pdf/P/P19/*
    # Files for new-style IDs are stored under anthology-files/pdf/2020.acl/*
    output_dir = get_pdf_dir(anth_id)

    # Make sure directory exists
    if not os.path.exists(output_dir):
        print(f"-> Creating directory {output_dir}", file=sys.stderr)
        os.makedirs(output_dir)

    canonical_path = os.path.join(output_dir, f"{anth_id}.pdf")

    # Update XML
    xml_file = get_xml_file(anth_id)
    collection_id, volume_id, paper_id = deconstruct_anthology_id(anth_id)
    tree = ET.parse(xml_file)
    if paper_id == "0":
        paper = tree.getroot().find(f"./volume[@id='{volume_id}']/frontmatter")
    else:
        paper = tree.getroot().find(
            f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']"
        )
    if paper is not None:
        revisions = paper.findall(change_type)
        revno = 1 if change_type == "erratum" else 2
        for revision in revisions:
            revno = int(revision.attrib["id"]) + 1

        if not dry_run:
            # Update the URL hash on the <url> tag
            if change_type != "erratum":
                url = paper.find("./url")
                if url is not None:
                    url.attrib["hash"] = checksum

            if change_type == "revision" and revno == 2:
                if paper.find("./url") is not None:
                    current_version_url = infer_url(paper.find("./url").text) + ".pdf"

                # Download original file
                # There are no versioned files the first time around, so create the first one
                # (essentially backing up the original version)
                revised_file_v1_path = os.path.join(
                    output_dir, f"{anth_id}{change_letter}1.pdf"
                )

                retrieve_url(current_version_url, revised_file_v1_path)
                validate_file_type(revised_file_v1_path)

                old_checksum = compute_hash_from_file(revised_file_v1_path)

                # First revision requires making the original version explicit
                revision = make_simple_element(
                    change_type,
                    None,
                    attrib={
                        "id": "1",
                        "href": f"{anth_id}{change_letter}1",
                        "hash": old_checksum,
                    },
                    parent=paper,
                )

            revision = make_simple_element(
                change_type,
                explanation,
                attrib={
                    "id": str(revno),
                    "href": f"{anth_id}{change_letter}{revno}",
                    "hash": checksum,
                    "date": date,
                },
                parent=paper,
            )
            indent(tree.getroot())

            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            print(
                f'-> Added {change_type} node "{revision.text}" to XML', file=sys.stderr
            )

    else:
        print(
            f"-> FATAL: paper ID {anth_id} not found in the Anthology",
            file=sys.stderr,
        )
        sys.exit(1)

    revised_file_versioned_path = os.path.join(
        output_dir, f"{anth_id}{change_letter}{revno}.pdf"
    )

    # Copy the file to the versioned path
    maybe_copy(pdf_path, revised_file_versioned_path)

    # Copy it over the canonical path
    if change_type == "revision":
        maybe_copy(pdf_path, canonical_path)


def main(args):
    change_type = "erratum" if args.erratum else "revision"

    print(f"Processing {change_type} to {args.anthology_id}...")

    # TODO: make sure path exists, or download URL to temp file
    if args.path.startswith("http"):
        _, input_file_path = tempfile.mkstemp()
        retrieve_url(args.path, input_file_path)
    else:
        input_file_path = args.path

    validate_file_type(input_file_path)

    add_revision(
        args.anthology_id,
        input_file_path,
        args.explanation,
        change_type=change_type,
        dry_run=args.dry_run,
    )

    if args.path.startswith("http"):
        os.remove(input_file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "anthology_id", help="The Anthology paper ID to revise (e.g., P18-1001)"
    )
    parser.add_argument(
        "path", type=str, help="Path to the revised paper ID (can be URL)"
    )
    parser.add_argument("explanation", help="Brief description of the changes.")
    parser.add_argument(
        "--erratum",
        "-e",
        action="store_true",
        help="This is an erratum instead of a revision.",
    )
    now = datetime.now()
    today = f"{now.year}-{now.month:02d}-{now.day:02d}"
    parser.add_argument(
        "--date",
        "-d",
        type=str,
        default=today,
        help="The date of the revision (ISO 8601 format)",
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true", default=False, help="Just a dry run."
    )
    args = parser.parse_args()

    main(args)
