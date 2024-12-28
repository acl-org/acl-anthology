#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2024 Marcel Bollmann <marcel@bollmann.me>
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

Creates page stubs for the full anthology based on the Hugo data files.

This script can only be run after create_hugo_data.py!

Options:
  --dir=DIR                Hugo project directory. [default: {scriptdir}/../../build/]
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from glob import glob
import logging as log
import msgspec
import os
from rich.progress import track
import shutil

from acl_anthology.utils.logging import setup_rich_logging


DECODER = msgspec.json.Decoder()
ENCODER = msgspec.json.Encoder()


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
    log.debug("Creating paper pages...")
    if not check_directory("{}/content/papers".format(srcdir), clean=clean):
        return

    # Go through all paper volumes
    for datafile in track(
        glob("{}/data/papers/*.json".format(srcdir)),
        description="Creating paper pages... ",
    ):
        log.debug("Processing {}".format(datafile))
        with open(datafile, "rb") as f:
            data = DECODER.decode(f.read())
        # Create a paper stub for each entry in the volume
        for anthology_id, entry in data.items():
            paper_dir = "{}/content/papers/{}".format(srcdir, anthology_id.split("-")[0])
            if not os.path.exists(paper_dir):
                os.makedirs(paper_dir)
            with open("{}/{}.md".format(paper_dir, anthology_id), "wb") as f:
                f.write(
                    ENCODER.encode(
                        {
                            "anthology_id": anthology_id,
                            "title": entry["title"],
                            "date": entry["ingest_date"],
                        }
                    )
                )


def create_volumes(srcdir, clean=False):
    """Creates page stubs for all proceedings volumes in the Anthology."""
    log.debug("Creating volume pages...")
    if not check_directory("{}/content/volumes".format(srcdir), clean=clean):
        return

    datafile = "{}/data/volumes.json".format(srcdir)
    log.debug("Processing {}".format(datafile))
    with open(datafile, "rb") as f:
        data = DECODER.decode(f.read())
    # Create a paper stub for each proceedings volume
    for anthology_id, entry in data.items():
        with open("{}/content/volumes/{}.md".format(srcdir, anthology_id), "wb") as f:
            f.write(
                ENCODER.encode(
                    {
                        "anthology_id": anthology_id,
                        "title": entry["title"],
                    }
                )
            )

    return data


def create_people(srcdir, clean=False):
    """Creates page stubs for all authors/editors in the Anthology."""
    log.debug("Creating people pages...")
    if not check_directory("{}/content/people".format(srcdir), clean=clean):
        return

    for datafile in track(
        glob("{}/data/people/*.json".format(srcdir)),
        description="Creating people pages...",
    ):
        log.debug("Processing {}".format(datafile))
        with open(datafile, "rb") as f:
            data = DECODER.decode(f.read())
        # Create a page stub for each person
        for name, entry in data.items():
            person_dir = "{}/content/people/{}".format(srcdir, name[0])
            if not os.path.exists(person_dir):
                os.makedirs(person_dir)
            data_out = {"name": name, "title": entry["full"], "lastname": entry["last"]}
            with open("{}/{}.md".format(person_dir, name), "wb") as f:
                f.write(ENCODER.encode(data_out))

    return data


def create_venues(srcdir, clean=False):
    """Creates page stubs for all venues in the Anthology."""
    datafile = "{}/data/venues.json".format(srcdir)
    print("Creating venue pages...")
    with open(datafile, "rb") as f:
        data = DECODER.decode(f.read())

    if not check_directory("{}/content/venues".format(srcdir), clean=clean):
        return
    # Create a paper stub for each venue (e.g. ACL)
    for venue, venue_data in data.items():
        venue_str = venue_data["slug"]
        with open("{}/content/venues/{}.md".format(srcdir, venue_str), "wb") as f:
            data_out = {
                "venue": venue_data["slug"],
                "acronym": venue_data["acronym"],
                "title": venue_data["name"],
            }
            if "url" in venue_data:
                data_out["venue_url"] = venue_data["url"]
            f.write(ENCODER.encode(data_out))


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
    file hugo/layout/events/single.html to lookup data written in build/data/events.json
    (created by create_hugo_data.py, the previous step), which knows about the volumes to list.
    The stub lists only the event slug and the event title
    """
    datafile = f"{srcdir}/data/events.json"
    print("Creating event pages...")
    with open(datafile, "rb") as f:
        data = DECODER.decode(f.read())

    if not check_directory(f"{srcdir}/content/events", clean=clean):
        return
    # Create a paper stub for each event
    for event, event_data in data.items():
        with open(f"{srcdir}/content/events/{event}.md", "wb") as f:
            f.write(ENCODER.encode({"event_slug": event, "title": event_data["title"]}))


def create_sigs(srcdir, clean=False):
    """Creates page stubs for all SIGs in the Anthology."""
    datafile = "{}/data/sigs.json".format(srcdir)
    print("Creating SIG pages...")
    with open(datafile, "rb") as f:
        data = DECODER.decode(f.read())

    if not check_directory("{}/content/sigs".format(srcdir), clean=clean):
        return
    # Create a paper stub for each SIGS (e.g. SIGMORPHON)
    for sig, sig_data in data.items():
        sig_str = sig_data["slug"]
        with open("{}/content/sigs/{}.md".format(srcdir, sig_str), "wb") as f:
            f.write(
                ENCODER.encode(
                    {
                        "acronym": sig,
                        "short_acronym": sig[3:] if sig.startswith("SIG") else sig,
                        "title": sig_data["name"],
                    }
                )
            )


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--dir"]:
        args["--dir"] = args["--dir"].format(scriptdir=scriptdir)
    dir_ = os.path.abspath(args["--dir"])

    log_level = log.DEBUG if args["--debug"] else log.INFO
    tracker = setup_rich_logging(level=log_level)

    create_papers(dir_, clean=args["--clean"])
    create_volumes(dir_, clean=args["--clean"])
    create_people(dir_, clean=args["--clean"])
    create_venues(dir_, clean=args["--clean"])
    create_events(dir_, clean=args["--clean"])
    create_sigs(dir_, clean=args["--clean"])

    if tracker.highest >= log.ERROR:
        exit(1)
