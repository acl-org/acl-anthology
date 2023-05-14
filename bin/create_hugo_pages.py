#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: create_hugo_pages.py [--dir=DIR] [-c] [--debug]

Creates page stubs for the full anthology based on the YAML data files.

This script can only be run after create_hugo_yaml.py!

Options:
  --dir=DIR                Hugo project directory. [default: {scriptdir}/../build/]
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from glob import glob
from tqdm import tqdm
import logging as log
import os
import shutil
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    log.info("Can't load yaml C bindings, reverting to slow pure Python version")
    from yaml import Loader

from anthology.utils import SeverityTracker


def check_directory(cdir, clean=False):
    if not os.path.isdir(cdir) and not os.path.exists(cdir):
        os.makedirs(cdir)
        return True
    entries = os.listdir(cdir)
    if "_index.md" in entries:
        entries.remove("_index.md")
    if entries and not clean:
        log.critical("Directory already exists and has content files: {}".format(cdir))
        log.info(
            "Call this script with the -c/--clean flag to automatically DELETE existing files"
        )
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
    for yamlfile in tqdm(glob("{}/data/papers/*.yaml".format(srcdir))):
        log.debug("Processing {}".format(yamlfile))
        with open(yamlfile, "r") as f:
            data = yaml.load(f, Loader=Loader)
        # Create a paper stub for each entry in the volume
        for anthology_id, entry in data.items():
            paper_dir = "{}/content/papers/{}".format(srcdir, anthology_id.split("-")[0])
            if not os.path.exists(paper_dir):
                os.makedirs(paper_dir)
            with open("{}/{}.md".format(paper_dir, anthology_id), "w") as f:
                print("---", file=f)
                yaml.dump(
                    {"anthology_id": anthology_id, "title": entry["title"]},
                    default_flow_style=False,
                    stream=f,
                )
                print("---", file=f)


def create_volumes(srcdir, clean=False):
    """Creates page stubs for all proceedings volumes in the Anthology."""
    log.info("Creating stubs for volumes...")
    if not check_directory("{}/content/volumes".format(srcdir), clean=clean):
        return

    yamlfile = "{}/data/volumes.yaml".format(srcdir)
    log.debug("Processing {}".format(yamlfile))
    with open(yamlfile, "r") as f:
        data = yaml.load(f, Loader=Loader)
    # Create a paper stub for each proceedings volume
    for anthology_id, entry in data.items():
        with open("{}/content/volumes/{}.md".format(srcdir, anthology_id), "w") as f:
            print("---", file=f)
            yaml.dump(
                {
                    "anthology_id": anthology_id,
                    "title": entry["title"],
                },
                default_flow_style=False,
                stream=f,
            )
            print("---", file=f)

    return data


def create_people(srcdir, clean=False):
    """Creates page stubs for all authors/editors in the Anthology."""
    log.info("Creating stubs for people...")
    if not check_directory("{}/content/people".format(srcdir), clean=clean):
        return

    for yamlfile in tqdm(glob("{}/data/people/*.yaml".format(srcdir))):
        log.debug("Processing {}".format(yamlfile))
        with open(yamlfile, "r") as f:
            data = yaml.load(f, Loader=Loader)
        # Create a page stub for each person
        for name, entry in data.items():
            person_dir = "{}/content/people/{}".format(srcdir, name[0])
            if not os.path.exists(person_dir):
                os.makedirs(person_dir)
            yaml_data = {"name": name, "title": entry["full"], "lastname": entry["last"]}
            with open("{}/{}.md".format(person_dir, name), "w") as f:
                print("---", file=f)
                # "lastname" is dumped to allow sorting by it in Hugo
                yaml.dump(yaml_data, default_flow_style=False, stream=f)
                print("---", file=f)

    return data


def create_venues(srcdir, clean=False):
    """Creates page stubs for all venues in the Anthology."""
    yamlfile = "{}/data/venues.yaml".format(srcdir)
    log.debug("Processing {}".format(yamlfile))
    with open(yamlfile, "r") as f:
        data = yaml.load(f, Loader=Loader)

    log.info("Creating stubs for venues...")
    if not check_directory("{}/content/venues".format(srcdir), clean=clean):
        return
    # Create a paper stub for each venue (e.g. ACL)
    for venue, venue_data in data.items():
        venue_str = venue_data["slug"]
        with open("{}/content/venues/{}.md".format(srcdir, venue_str), "w") as f:
            print("---", file=f)
            yaml_data = {
                "venue": venue_data["slug"],
                "acronym": venue_data["acronym"],
                "title": venue_data["name"],
            }
            if "url" in venue_data:
                yaml_data["venue_url"] = venue_data["url"]
            yaml.dump(yaml_data, default_flow_style=False, stream=f)
            print("---", file=f)


def create_events(srcdir, clean=False):
    """
    Creates page stubs for all events in the Anthology.

    Expects that the EventIndex has as sequence of dictionaries,
    keyed by the event name, with the following fields:

    [
        "acl-2022": {
            "title": "Annual Meeting of the Association for Computational Linguistics (2022)",
            "volumes": ["2022.acl-main", "2022.acl-srw", ...]
        },
        ...
    ]

    Here, a "{event_slug}.md" stub is written for each paper. This is used with the Hugo template
    file hugo/layout/events/single.html to lookup data written in build/data/events.yaml
    (created by create_hugo_yaml.py, the previous step), which knows about the volumes to list.
    The stub lists only the event slug and the event title
    """
    yamlfile = f"{srcdir}/data/events.yaml"
    log.debug(f"Processing {yamlfile}")
    with open(yamlfile, "r") as f:
        yaml_data = yaml.load(f, Loader=Loader)

    log.info("Creating stubs for events...")
    if not check_directory(f"{srcdir}/content/events", clean=clean):
        return
    # Create a paper stub for each event
    for event, event_data in yaml_data.items():
        with open(f"{srcdir}/content/events/{event}.md", "w") as f:
            print("---", file=f)
            yaml_data = {"event_slug": event, "title": event_data["title"]}
            yaml.dump(yaml_data, default_flow_style=False, stream=f)
            print("---", file=f)


def create_sigs(srcdir, clean=False):
    """Creates page stubs for all SIGs in the Anthology."""
    yamlfile = "{}/data/sigs.yaml".format(srcdir)
    log.debug("Processing {}".format(yamlfile))
    with open(yamlfile, "r") as f:
        data = yaml.load(f, Loader=Loader)

    log.info("Creating stubs for SIGs...")
    if not check_directory("{}/content/sigs".format(srcdir), clean=clean):
        return
    # Create a paper stub for each SIGS (e.g. SIGMORPHON)
    for sig, sig_data in data.items():
        sig_str = sig_data["slug"]
        with open("{}/content/sigs/{}.md".format(srcdir, sig_str), "w") as f:
            print("---", file=f)
            yaml.dump(
                {
                    "acronym": sig,
                    "short_acronym": sig[3:] if sig.startswith("SIG") else sig,
                    "title": sig_data["name"],
                },
                default_flow_style=False,
                stream=f,
            )
            print("---", file=f)


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--dir"]:
        args["--dir"] = args["--dir"].format(scriptdir=scriptdir)
    dir_ = os.path.abspath(args["--dir"])

    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    create_papers(dir_, clean=args["--clean"])
    create_volumes(dir_, clean=args["--clean"])
    create_people(dir_, clean=args["--clean"])
    create_venues(dir_, clean=args["--clean"])
    create_events(dir_, clean=args["--clean"])
    create_sigs(dir_, clean=args["--clean"])

    if tracker.highest >= log.ERROR:
        exit(1)
