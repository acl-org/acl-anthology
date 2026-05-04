#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
One-off script for the Dialogue & Discourse journal ingestion (2026-04-10).

Reads per-paper BibTeX files in
  <ingest_root>/DialogueAndDiscourse-YYYY/proceedings/cdrom/bib/YYYY.dnd-N.bib
extracts the (numeric) `month` field, and writes a TSV of
(anthology_id, month_name) pairs (anthology_id = "{YYYY}.dnd-1.{N}").

It then loads the Anthology and sets `paper.month` to the full English month
name for each paper, saving all changes via `anthology.save_all()`.

Usage:
  uv run python bin/oneoff/add_dnd_months.py [--ingest-root DIR] [--tsv PATH]
"""

import argparse
import os
import re
import sys
from glob import glob

from acl_anthology import Anthology

NUM_TO_MONTH = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

MONTH_RE = re.compile(r"^\s*month\s*=\s*\{?\s*([^},\s]+)\s*\}?", re.MULTILINE)


def extract_month(bib_path):
    with open(bib_path, encoding="utf-8") as fh:
        text = fh.read()
    m = MONTH_RE.search(text)
    if not m:
        return None
    raw = m.group(1).strip()
    try:
        return NUM_TO_MONTH[int(raw)]
    except (ValueError, KeyError):
        return raw


def build_tsv(ingest_root, years, tsv_path):
    rows = []
    for year in years:
        bib_dir = os.path.join(
            ingest_root,
            f"DialogueAndDiscourse-{year}",
            "proceedings",
            "cdrom",
            "bib",
        )
        if not os.path.isdir(bib_dir):
            print(f"[{year}] no bib dir at {bib_dir}, skipping", file=sys.stderr)
            continue
        for bib_path in sorted(glob(os.path.join(bib_dir, f"{year}.dnd-*.bib"))):
            base = os.path.basename(bib_path)
            m = re.match(rf"{year}\.dnd-(\d+)\.bib$", base)
            if not m:
                print(f"[{year}] unexpected bib filename {base}", file=sys.stderr)
                continue
            paper_num = m.group(1)
            month = extract_month(bib_path)
            if month is None:
                print(f"[{year}] no month found in {base}", file=sys.stderr)
                continue
            volume_id = year - 2009  # D&D journal volume = year - 2009
            anthology_id = f"{year}.dnd-{volume_id}.{paper_num}"
            rows.append((anthology_id, month))

    with open(tsv_path, "w", encoding="utf-8") as fh:
        for aid, month in rows:
            fh.write(f"{aid}\t{month}\n")
    print(f"wrote {len(rows)} rows to {tsv_path}")
    return rows


def apply_months(rows):
    anthology = Anthology.from_within_repo()
    updated = 0
    for anthology_id, month in rows:
        paper = anthology.get_paper(anthology_id)
        if paper is None:
            print(f"  ! paper not found: {anthology_id}", file=sys.stderr)
            continue
        paper.month = month
        updated += 1
    anthology.save_all()
    print(f"set month on {updated} papers and saved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ingest-root",
        default="/Users/mattpost/Downloads/2026-04-10-dnd-journal",
    )
    parser.add_argument("--tsv", default="dnd_months.tsv")
    parser.add_argument("--years", nargs="*", type=int, default=list(range(2010, 2027)))
    parser.add_argument(
        "--tsv-only",
        action="store_true",
        help="Only write the TSV; do not modify XML.",
    )
    args = parser.parse_args()

    rows = build_tsv(args.ingest_root, args.years, args.tsv)
    if args.tsv_only:
        return
    apply_months(rows)


if __name__ == "__main__":
    main()
