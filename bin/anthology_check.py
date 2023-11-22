#!/usr/bin/env python3

"""
Sanity check for ACLPUB2 submissions to the ACL Anthology.
If this script doesn't pass, you're not ready to submit!

This script will check that the following files exist, in
the root of your repository:
 
- papers.yml
- conference_details.yml
- front_matter.pdf
- proceedings.pdf

It will also check that each paper listed in papers.yml has
a corresponding PDF file, and that any attachments listed
in papers.yml also exist.

If you have a config.yml file in the root of your repository,
this script will use the import_dir field to look for the
above files in a different directory. For example, if you've
built the Anthology files to a directory called "proceedings",
then you can create a file named config.yml with the following
contents:

    import_dir: proceedings
    
and this script will look for the above files relative to the
proceedings directory.
"""

import sys
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def main(args):
    rootdir = Path(args.import_dir)

    # Start a counter for the number of logged messages, and increment it each time there is a log message
    class CounterHandler(logging.Handler):
        def __init__(self, level):
            super().__init__(level)
            self.count = 0

        def emit(self, record):
            self.count += 1
            print(self.format(record), file=sys.stderr)
    
    logger.addHandler(CounterHandler(logging.WARNING))

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

    # make sure all the following files exist
    for file in ["conference_details.yml", "front_matter.pdf", "proceedings.pdf"]:
        if not (path := rootdir / file).exists():
            logger.error(f"File '{path}' does not exist")

    if not (rootdir / "papers.yml").exists():
        logger.fatal(f"File '{rootdir / 'papers.yml'}' not found")

    # Read through papers.yml. At the top level of the file is a list
    # of papers, whose path is present under the 'file' key. Make sure
    # that file exists. Also, if a paper has a file 'attachments', make
    # sure that exists.
    papers = yaml.safe_load((rootdir / "papers.yml").read_text())
    for paper in papers:
        # For each file, there should be a file {rootdir}/watermarked_pdfs/{id}.pdf
        path = rootdir / "watermarked_pdfs"/ f'{paper["id"].pdf}'
        if not path.exists():
            logger.error(f"Paper file '{path}' not found")

        if "attachments" in paper:
            dirs_to_try = [rootdir, rootdir / "attachments"]
            for attachment in paper["attachments"]:
                for dir in dirs_to_try:
                    if not (path := rootdir / dir / attachment["file"]).exists():
                        break
                else:
                    logger.error(f"Attachment file '{attachment['file']}' not found in any of {dirs_to_try}")

    # If there were any warnings or errors, exit with a non-zero status
    if logger.handlers:
        handler = logger.handlers[0]
        if isinstance(handler, CounterHandler):
            if handler.count > 0:
                print(f"Script found {handler.count} warnings or errors. Please fix them before submitting.")
                sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("Script to check the integrity of a directory to be imported into the ACL Anthology")
    parser.add_argument("--import-dir", type=str, default=".", help="Root directory for Anthology import")
    args = parser.parse_args()

    main(args)
