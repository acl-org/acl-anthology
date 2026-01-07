#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019–2025 Matt Post <post@cs.jhu.edu>
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

  add_revision.py [-e] [-i GITHUB_ISSUE] paper_id URL_OR_PATH.pdf "Short explanation".

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
import io

from git.repo.base import Repo

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
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

WATERMARK_FONT = "Times-Roman"
WATERMARK_SIZE = 16
WATERMARK_LEFT_OFFSET_PT = (
    27  # distance from left edge in points (50% increase for margin)
)
WATERMARK_GRAY = 0.55  # medium gray like arXiv


def _make_vertical_watermark_page(w, h, text):
    """Return a single-page PDF with vertical (rotated 90° CCW) watermark at left."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.saveState()
    c.setFont(WATERMARK_FONT, WATERMARK_SIZE)
    c.setFillGray(WATERMARK_GRAY)
    # Translate slightly from left then rotate so text reads bottom-to-top along left side.
    c.translate(WATERMARK_LEFT_OFFSET_PT, 0)
    c.rotate(90)
    text_w = c.stringWidth(text, WATERMARK_FONT, WATERMARK_SIZE)
    # Center along original page height (which becomes horizontal span after rotation)
    x_draw = (h - text_w) / 2.0
    y_draw = 0
    c.drawString(x_draw, y_draw, text)
    c.restoreState()
    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def add_revision_watermark(pdf_path, anth_id, revno, date):
    """Return path to temp PDF with watermark added to first page (revisions only)."""
    reader = PdfReader(pdf_path)
    if not reader.pages:
        return pdf_path
    writer = PdfWriter()
    first = reader.pages[0]
    w = float(first.mediabox.width)
    h = float(first.mediabox.height)
    # Format date as DD-Mon-YYYY (e.g., 17-Sep-2025) for watermark display only.
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        display_date = dt.strftime("%d %b %Y")
    except ValueError:
        # If already in some unexpected format, just use original string.
        display_date = date
    text = f"ACL Anthology ID {anth_id} / revision {revno} / {display_date}"
    overlay = PdfReader(_make_vertical_watermark_page(w, h, text)).pages[0]
    first.merge_page(overlay)
    writer.add_page(first)
    for p in reader.pages[1:]:
        writer.add_page(p)
    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    with open(tmp_path, "wb") as out_f:
        writer.write(out_f)
    return tmp_path


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

    # checksum will be computed after potential watermark insertion

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

        # Insert watermark for revisions before computing checksum / updating XML
        watermarked_temp_path = None
        if change_type == "revision":
            watermarked_temp_path = add_revision_watermark(pdf_path, anth_id, revno, date)
            pdf_path = watermarked_temp_path

        checksum = compute_hash_from_file(pdf_path)

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

    # Cleanup temp watermarked file if created
    if (
        'watermarked_temp_path' in locals()
        and watermarked_temp_path
        and os.path.exists(watermarked_temp_path)
    ):
        try:
            os.remove(watermarked_temp_path)
        except OSError:
            pass


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
        date=args.date,
    )

    if args.path.startswith("http"):
        os.remove(input_file_path)

    """
    If a Github issue was passed as an argument, do the following.
    First ensure, that we are on a branch named "corrections-YYYY-MM".
    Then, create a commit with the message "Add revision for {anthology_id} (closes {issue})"
    Use the Github module to create the brnach (if not existing), change to it,
    and create the commit.
    """
    if args.issue:
        repo = Repo(".", search_parent_directories=True)
        # Create the branch if it doesn't exist, based off main (or master)
        branch_name = args.branch
        existing_heads = [h.name for h in repo.heads]
        base_branch = "master"
        if branch_name not in existing_heads:
            repo.create_head(branch_name, getattr(repo.heads, base_branch).commit)
        # Change to the new branch
        repo.git.checkout(branch_name)
        # Stage changed files
        repo.git.add(get_xml_file(args.anthology_id))
        if repo.is_dirty(index=True, working_tree=True, untracked_files=True):
            repo.index.commit(
                f"Add {change_type} for {args.anthology_id} (closes #{args.issue})"
            )


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
        "--issue",
        "-i",
        type=int,
        default=None,
        help="GitHub issue number associated with this revision.",
    )
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
    parser.add_argument("--branch", "-b", default=None, help="Branch name.")

    args = parser.parse_args()

    if args.branch is None:
        args.branch = f"corrections-{args.date[:7]}"

    main(args)
