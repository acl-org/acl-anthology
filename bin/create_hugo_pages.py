#!/usr/bin/env python3
# Marcel Bollmann <marcel@bollmann.me>, 2019

"""Usage: create_hugo_pages.py [--dir=DIR] [-c] [--debug]

Creates page stubs for the full anthology based on the YAML data files.

This script can only be run after create_hugo_yaml.py!

Options:
  --dir=DIR                Hugo project directory. [default: {scriptdir}/../hugo/]
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from glob import glob
import logging as log
import os
import shutil
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def initialize_directory(trgdir, clean=False):
    if os.path.exists(trgdir):
        if os.listdir(trgdir):
            if clean:
                log.debug("Cleaning up directory: {}".format(trgdir))
                import shutil

                shutil.rmtree(trgdir)
            else:
                log.critical(
                    "Directory already exists and is not empty: {}".format(trgdir)
                )
                log.info(
                    "Call this script with the -c/--clean flag to automatically delete existing directories"
                )
                exit(1)
    else:
        os.mkdir(trgdir)


def create_papers(srcdir, clean=False):
    """Creates page stubs for all papers in the Anthology."""
    # Make sure we start from a clean slate
    for entry in glob("{}/content/papers/*".format(srcdir)):
        if os.path.isdir(entry):
            if clean:
                shutil.rmtree(entry)
            else:
                log.critical("Directory already exists: {}".format(entry))
                log.info(
                    "Call this script with the -c/--clean flag to automatically DELETE existing subdirectories"
                )
                return

    # Go through all paper volumes
    for yamlfile in glob("{}/data/papers/*.yaml".format(srcdir)):
        log.debug("Processing volume {}".format(yamlfile))
        with open(yamlfile, "r") as f:
            data = yaml.load(f, Loader=Loader)
        # Create a paper stub for each entry in the volume
        for anthology_id in data:
            paper_dir = "{}/content/papers/{}".format(srcdir, anthology_id)
            os.mkdir(paper_dir)
            with open("{}/{}.md".format(paper_dir, anthology_id.lower()), "w") as f:
                print("---", file=f)
                print("anthology_id: {}".format(anthology_id), file=f)
                print("---", file=f)


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--dir"]:
        args["--dir"] = os.path.abspath(args["--dir"].format(scriptdir=scriptdir))

    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)

    create_papers(args["--dir"], clean=args["--clean"])
