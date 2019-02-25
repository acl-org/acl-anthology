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


def check_directory(cdir, clean=False):
    if not os.path.isdir(cdir) and not os.path.exists(cdir):
        os.mkdir(cdir)
        return True
    entries = os.listdir(cdir)
    if "_index.md" in entries:
        entries.remove("_index.md")
    if entries and not clean:
        log.critical("Directory already exists and has content files: {}".format(cdir))
        log.info("Call this script with the -c/--clean flag to automatically DELETE existing files")
        return False
    for entry in entries:
        entry = "{}/{}".format(cdir, entry)
        if os.path.isdir(entry):
            shutil.rmtree(entry)
        else:
            os.remove(entry)
    return True


def create_papers(srcdir, clean=False):
    """Creates page stubs for all papers in the Anthology."""
    log.info("Creating stubs for papers...")
    if not check_directory("{}/content/papers".format(srcdir), clean=clean):
        return

    # Go through all paper volumes
    for yamlfile in glob("{}/data/papers/*.yaml".format(srcdir)):
        log.debug("Processing volume {}".format(yamlfile))
        with open(yamlfile, "r") as f:
            data = yaml.load(f, Loader=Loader)
        # Create a paper stub for each entry in the volume
        for anthology_id, entry in data.items():
            paper_dir = "{}/content/papers/{}/{}".format(srcdir, anthology_id[0], anthology_id[:3])
            if not os.path.exists(paper_dir):
                os.makedirs(paper_dir)
            with open("{}/{}.md".format(paper_dir, anthology_id), "w") as f:
                print("---", file=f)
                print(yaml.dump({'anthology_id': anthology_id, 'title': entry['title']}, default_flow_style=False), file=f)
                print("---", file=f)


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--dir"]:
        args["--dir"] = os.path.abspath(args["--dir"].format(scriptdir=scriptdir))

    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)

    create_papers(args["--dir"], clean=args["--clean"])
