#!/usr/bin/env python3
# Marcel Bollmann <marcel@bollmann.me>, 2019

"""Usage: xml_to_yaml.py [--importdir=DIR] [--exportdir=DIR] [--debug]

Work in progress.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../import/]
  --exportdir=DIR          Directory to write YAML files to.   [default: {scriptdir}/../hugo/data/]
  --debug                  Output debug-level log messages.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
import logging as log
import os
import yaml

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

from anthology import Anthology


def export_anthology(anthology, outdir):
    # Create directories
    for subdir in ("",):
        target_dir = "{}/{}".format(outdir, subdir)
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)

    # Dump paper index
    papers = {}
    for id_, paper in anthology.papers.items():
        log.debug("export_anthology: processing paper '{}'".format(id_))
        data = paper.attrib
        data["paper_id"] = paper.paper_id
        data["parent_volume_id"] = paper.parent_volume_id
        if "author" in data:
            data["author"] = [name.id_ for name in data["author"]]
        if "editor" in data:
            data["editor"] = [name.id_ for name in data["editor"]]
        papers[paper.full_id] = data
    with open("{}/papers.yaml".format(outdir), "w") as f:
        print(yaml.dump(papers, Dumper=Dumper), file=f)

    # Dump volume index
    volumes = {}
    for id_, volume in anthology.volumes.items():
        log.debug("export_anthology: processing volume '{}'".format(id_))
        data = volume.attrib
        data["papers"] = volume.paper_ids
        volumes[volume.full_id] = data
    with open("{}/volumes.yaml".format(outdir), "w") as f:
        print(yaml.dump(volumes, Dumper=Dumper), file=f)

    # Dump author index
    people = {}
    for name_repr, name, papers in anthology.people.items():
        data = name.as_dict()
        data.update(papers)
        people[name_repr] = data
    with open("{}/people.yaml".format(outdir), "w") as f:
        print(yaml.dump(people, Dumper=Dumper), file=f)


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

    anthology = Anthology(importdir=args["--importdir"])
    export_anthology(anthology, args["--exportdir"])
