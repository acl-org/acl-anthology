#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Last updated 2024-08-07 by Matt Post

TODO:
- Ensure no LaTeX in titles
- If there is only a single name, it should be the last name, not the first
- Clean TeX from abstracts, too (e.g., 2023.findings-emnlp.439)

Sanity check for ACLPUB2 submissions to the ACL Anthology.
If this script doesn't pass, you're not ready to submit!
The expected format (default from aclpub2) is as follows:
    output
    ├── attachments
    │   ├── paper1.attachment.zip
    │   ├── …
    ├── inputs
    │   ├── conference_details.yml
    │   ├── organizing_committee.yml
    │   ├── papers
    │   │   ├── paper1.pax
    │   │   ├── paper1.pdf
    │   │   ├── paper1.attachement.zip
    │   │   ├── …
    │   ├── papers.yml
    │   ├── prefaces
    │   │   └── preface1.tex
    │   │   └── …
    │   ├── prefaces.yml
    │   ├── program.yml
    │   ├── sponsor_logos
    │   │   ├── logo1.png
    │   │   └── …
    │   └── sponsors.yml
    ├── proceedings.pdf
    └── watermarked_pdfs
        ├── 0.pdf
        ├── 0R1QRKvBNJ.pdf
        ├── …

From the above structure, the script will check the following:

Existence checks:
- output/inputs/papers.yml
- output/inputs/conference_details.yml
- output/proceedings.pdf (optional)
- PDFS, e.g., output/watermarked_pdfs/0.pdf (frontmatter)
- attachments, e.g., output/attachments/paper17.attachment.pdf (optional)

It will also check that each paper listed in papers.yml has
a corresponding PDF file under output/watermarked_pdfs, and that any
attachments listed in papers.yml also exist under output/attachments.

If you have a config.yml file in the root of your repository,
this script will use the import_dir field to look for the
above files in a different directory (instead of ./output). For example,
if you've built the Anthology files to a directory called "anthology",
then you can create a file named config.yml with the following
contents:

    import_dir: anthology

and this script will look for the above files relative to the
anthology directory.
"""

import sys
import yaml
import logging
from pathlib import Path

logging.basicConfig(format="%(message)s", level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Start a counter for the number of logged messages, and increment it each time there is a log message
class CounterHandler(logging.Handler):
    def __init__(self, level):
        super().__init__(level)
        self.count = 0

    def emit(self, record):
        self.count += 1
        print(self.format(record), file=sys.stderr)


def main(args):
    logger.addHandler(CounterHandler(logging.WARNING))
    logger.addHandler(CounterHandler(logging.ERROR))

    rootdir = Path(args.import_dir)

    if not rootdir.exists():
        logger.fatal(f"Import directory '{rootdir}' does not exist")
        sys.exit(1)

    # look for a configuration file that could specify an alternate import directory
    config_file = rootdir / "config.yml"
    if config_file.exists():
        config = yaml.safe_load(config_file.read_text())
        if "import_dir" in config:
            rootdir = Path(config["import_dir"])
            logger.info(f"Using import directory '{rootdir}'")

    # conference details
    if not (
        conference_details_path := rootdir / "inputs" / "conference_details.yml"
    ).exists():
        logger.error(f"x File '{conference_details_path}' does not exist")
    elif args.verbose:
        logger.info(f"✓ Found {conference_details_path}")

    # papers.yml
    if not (papers_path := rootdir / "inputs" / "papers.yml").exists():
        logger.fatal(f"File '{papers_path}' not found")
    elif args.verbose:
        logger.info(f"✓ Found {papers_path}")

    # Read through papers.yml. At the top level of the file is a list
    # of papers, whose path is present under the 'file' key. Make sure
    # that file exists. Also, if a paper has a file 'attachments', make
    # sure that exists.
    papers = yaml.safe_load(papers_path.read_text())
    for paper in papers:
        paper_id = paper["id"]

        # For each file, there should be a file {rootdir}/watermarked_pdfs/{id}.pdf
        if "archival" not in paper or paper['archival']:
            if not (
                pdf_path := rootdir / "watermarked_pdfs" / f'{paper["id"]}.pdf'
            ).exists():
                logger.error(f"Paper file '{pdf_path}' not found")
            elif args.verbose:
                logger.info(f"✓ Found PDF file {pdf_path}")

        for author in paper.get("authors", []):
            if "@" in author.get("name", ""):
                logger.error(
                    f"Paper ID {paper_id}: Author name '{author['name']}' contains an email address"
                )

        if "attachments" in paper:
            for attachment in paper["attachments"]:
                if not (
                    attachment_path := rootdir / "attachments" / attachment["file"]
                ).exists():
                    logger.error(f"Attachment file '{attachment_path}' not found")
                elif args.verbose:
                    logger.info(f"✓ Found attachment file {attachment_path}")

    # Check for frontmatter
    if not (frontmatter_path := rootdir / "watermarked_pdfs" / "0.pdf").exists():
        logger.error(f"Frontmatter {frontmatter_path} not found")
    elif args.verbose:
        logger.info(f"✓ Found frontmatter at {frontmatter_path}")

    # If there were any warnings or errors, exit with a non-zero status
    if logger.handlers:
        handler = logger.handlers[0]
        if isinstance(handler, CounterHandler):
            if handler.count > 0:
                print(
                    f"FAILURE: script found {handler.count} warnings or errors. Please fix them before submitting."
                )
                sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        "Script to check the integrity of a directory to be imported into the ACL Anthology"
    )
    parser.add_argument(
        "--import-dir",
        "-i",
        type=str,
        default=".",
        help="Root directory for Anthology import",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print successes in addition to errors.",
    )
    args = parser.parse_args()

    main(args)
