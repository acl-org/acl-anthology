#!/usr/bin/env python3

"""
Recompute the page numberings for a volume by looping through the PDFs.

Given a volume (e.g., 2025.emnlp-main), this script will go through all PDFs
in that volume (under ~/anthology-files/pdf/emnlp/2025.emnlp-main.*.pdf), extract
the page counts, and update the Anthology XML accordingly.

Is smart enough to skip revisions by looking for v1 first, then falling back.

Uses the library!

Author: Matt Post, January 2026
"""

import os

from acl_anthology import Anthology
from pathlib import Path
from PyPDF2 import PdfReader


def main(args):
    data_dir = Path(__file__).parent.resolve().parent.parent
    anthology = Anthology(datadir=data_dir / "data")

    volume = anthology.get_volume(args.volume_id)
    if volume is None:
        print(f"Volume {args.volume_id} not found in the Anthology.")
        return

    pdf_dir = args.pdf_dir

    collection_id = volume.parent.id.split(".")[1]
    year = volume.year

    cur_page = 1
    updated = False
    for paper in volume.papers():
        if paper.is_frontmatter:
            continue

        # look for v1 first, to get page numbers right
        for version in ["v1", ""]:
            pdf_path = os.path.join(
                pdf_dir,
                collection_id,
                f"{year}.{collection_id}-{volume.id}.{paper.id}{version}.pdf",
            )
            if os.path.isfile(pdf_path):
                break
        else:
            print(f"PDF not found for paper {paper.id} at {pdf_path}. Skipping.")
            continue

        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                num_pages = len(reader.pages)
        except Exception as e:
            print(f"Error reading PDF for paper {paper.id}: {e}")
            continue

        stop_page = cur_page + num_pages - 1
        page_range = f"{cur_page}-{stop_page}"

        if paper.pages != page_range:
            paper.pages = page_range
            updated = True

        print(paper.id, page_range)

        cur_page = stop_page + 1

    if updated:
        volume.parent.save()
        print(f"Updated volume {args.volume_id} in the Anthology XML.")
    else:
        print(f"No updates made for volume {args.volume_id}.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Recompute page numberings for a volume."
    )
    parser.add_argument(
        "volume_id",
        type=str,
        help="The volume ID to recompute (e.g., 2025.emnlp-main).",
    )
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default=os.path.expanduser("~/anthology-files/pdf/"),
        help="Directory where PDFs are stored.",
    )
    args = parser.parse_args()

    main(args)
