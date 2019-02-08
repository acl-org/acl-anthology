#!/usr/bin/env python3
# Marcel Bollmann <marcel@bollmann.me>, 2019

"""Usage: xml_to_yaml.py [--importdir=DIR] [--exportdir=DIR]

Work in progress.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../import/]
  --exportdir=DIR          Directory to write YAML files to.   [default: {scriptdir}/../hugo/data/]
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

from anthology import Anthology, PersonIndex


def export_anthology(anthology, outdir):
    # Create directories
    for subdir in ("", "volumes"):
        target_dir = "{}/{}".format(outdir, subdir)
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)

    pidx = PersonIndex()
    for volume, ids in anthology.volumes.items():
        papers = {}
        for id_ in ids:
            paper = anthology.papers[id_]
            data = paper.attrib
            # Index personal names while we're going through the papers
            if "author" in data:
                data["author"] = [
                    pidx.register(person, id_, "author") for person in data["author"]
                ]
            if "editor" in data:
                data["editor"] = [
                    pidx.register(person, id_, "editor") for person in data["editor"]
                ]
            papers[paper.paper_id] = data

        # Dump all papers of a volume into a single file (as with the XML)
        with open("{}/volumes/{}.yaml".format(outdir, volume), "w") as f:
            print(yaml.dump(papers, Dumper=Dumper), file=f)

    # Dump author index
    people = {}
    for name_repr, name, papers in pidx.items():
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

    anthology = Anthology(importdir=args["--importdir"])
    export_anthology(anthology, args["--exportdir"])
