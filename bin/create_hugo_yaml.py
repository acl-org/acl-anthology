#!/usr/bin/env python3
# Marcel Bollmann <marcel@bollmann.me>, 2019

"""Usage: create_hugo_yaml.py [--importdir=DIR] [--exportdir=DIR] [--debug] [--dry-run]

Creates YAML files containing all necessary Anthology data for the static website generator.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../import/]
  --exportdir=DIR          Directory to write YAML files to.   [default: {scriptdir}/../hugo/data/]
  --debug                  Output debug-level log messages.
  -n, --dry-run            Do not write YAML files (useful for debugging).
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from collections import defaultdict
from tqdm import tqdm
import logging as log
import os
import yaml

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

from anthology import Anthology


def export_anthology(anthology, outdir, dryrun=False):
    # Create directories
    for subdir in ("", "papers"):
        target_dir = "{}/{}".format(outdir, subdir)
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)

    # Dump paper index
    papers = defaultdict(dict)
    for id_, paper in anthology.papers.items():
        log.debug("export_anthology: processing paper '{}'".format(id_))
        data = paper.attrib
        data["paper_id"] = paper.paper_id
        data["parent_volume_id"] = paper.parent_volume_id
        if "author" in data:
            data["author"] = [name.id_ for name in data["author"]]
        if "editor" in data:
            data["editor"] = [name.id_ for name in data["editor"]]
        papers[paper.top_level_id][paper.full_id] = data
    if not dryrun:
        progress = tqdm(total=len(papers) + 30)
        for top_level_id, paper_list in papers.items():
            with open("{}/papers/{}.yaml".format(outdir, top_level_id), "w") as f:
                print(yaml.dump(paper_list, Dumper=Dumper), file=f)
            progress.update()

    # Dump volume index
    volumes = {}
    for id_, volume in anthology.volumes.items():
        log.debug("export_anthology: processing volume '{}'".format(id_))
        data = volume.attrib
        data["papers"] = volume.paper_ids
        if "author" in data:
            data["author"] = [name.id_ for name in data["author"]]
        if "editor" in data:
            data["editor"] = [name.id_ for name in data["editor"]]
        volumes[volume.full_id] = data
    if not dryrun:
        with open("{}/volumes.yaml".format(outdir), "w") as f:
            print(yaml.dump(volumes, Dumper=Dumper), file=f)
        progress.update(10)

    # Dump author index
    people = {}
    for name_repr, name, papers in anthology.people.items():
        data = name.as_dict()
        data.update(papers)
        people[name_repr] = data
    if not dryrun:
        with open("{}/people.yaml".format(outdir), "w") as f:
            print(yaml.dump(people, Dumper=Dumper), file=f)
        progress.update(20)
        progress.close()


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )
    if "{scriptdir}" in args["--exportdir"]:
        args["--exportdir"] = os.path.abspath(
            args["--exportdir"].format(scriptdir=scriptdir)
        )

    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)

    log.info("Reading the Anthology data...")
    anthology = Anthology(importdir=args["--importdir"])
    log.info("Exporting to YAML...")
    export_anthology(anthology, args["--exportdir"], dryrun=args["--dry-run"])
