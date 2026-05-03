# /// script
# dependencies = [
#   "acl-anthology @ git+https://github.com/acl-org/acl-anthology/#egg=pkg&subdirectory=python",
#   "docopt",
#   "lxml",
#   "msgspec",
#   "PyYAML",
# ]
# ///
#
# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: transition_to_json.py [options]

Changes YAML data files into JSON format.

Options:
  --debug                  Output debug-level log messages.
  -d, --datadir=DIR        Directory with data files. [default: {scriptdir}/../../data]
  -h, --help               Display this helpful text.
"""

from collections import defaultdict
from docopt import docopt
import logging as log
from lxml import etree
from lxml.builder import E
import msgspec
import os
from pathlib import Path
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:  # pragma: no cover
    from yaml import Loader  # type: ignore

from acl_anthology import Anthology
from acl_anthology.sigs import SIGMeeting
from acl_anthology.utils.logging import setup_rich_logging
from acl_anthology.utils.xml import indent


def write_json(filename, data):
    target_path = anthology.datadir / "json" / filename
    with open(target_path, "wb") as f:
        encoded = msgspec.json.encode(data)
        f.write(msgspec.json.format(encoded))
        f.write(b"\n")

    log.info(f"Wrote {target_path}")


def remove_sig_tags(datadir):
    for xmlfile in datadir.glob("xml/*.xml"):
        tree = etree.parse(xmlfile)
        for sig in tree.findall(".//volume/meta/sig"):
            sig.getparent().remove(sig)
        root = tree.getroot()
        indent(root)
        with open(xmlfile, "wb") as f:
            f.write(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))


def convert_people_yaml(anthology):
    with open(anthology.people.path, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=Loader)

    new_data = {}
    insert_order = (
        "names",
        "comment",
        "degree",
        "disable_name_matching",
        "orcid",
        "similar",
    )
    for pid, values in data.items():
        new_values = {}
        for key in insert_order:
            if key in values:
                new_values[key] = values[key]
        new_data[pid] = new_values

    write_json("people.json", new_data)


def convert_venues_yaml(anthology):
    venues = {}

    # Nothing changes about the data format, but we gather all YAML files into one dict
    for yaml_path in sorted(anthology.datadir.glob("yaml/venues/*.yaml")):
        venue_id = yaml_path.name[:-5]
        with open(yaml_path, "r", encoding="utf-8") as f:
            venues[venue_id] = yaml.load(f, Loader=Loader)

    write_json("venues.json", venues)


def convert_sigs_yaml(anthology):
    sigs = {}
    collections_to_update = defaultdict(list)

    def sigmeeting_to_dict(sigmeeting):
        data = {
            "year": sigmeeting.year,
            "name": sigmeeting.name,
        }
        if sigmeeting.url:
            data["url"] = sigmeeting.url
        return data

    for sig in anthology.sigs.values():
        sigs[sig.id] = {
            "acronym": sig.acronym,
            "name": sig.name,
            "external_meetings": [
                sigmeeting_to_dict(meeting)
                for meeting in sig.meetings
                if isinstance(meeting, SIGMeeting)
            ],
        }
        if sig.url:
            sigs[sig.id]["url"] = sig.url
        for volume in sig.volumes():
            collections_to_update[volume.collection.path].append((volume.id, sig.id))

    write_json("sigs.json", sigs)

    # Write <sig> tags to XML files
    num_changed = 0
    for path, updates in collections_to_update.items():
        tree = etree.parse(path)
        for volume_id, sig_id in updates:
            venue = tree.find(f".//volume[@id='{volume_id}']/meta/venue")
            venue.addprevious(E.sig(sig_id))
        root = tree.getroot()
        indent(root)
        with open(path, "wb") as f:
            f.write(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))
        num_changed += 1

    log.info(f"Updated {num_changed} XML files")


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG if args["--debug"] else log.INFO
    tracker = setup_rich_logging(level=log_level)

    if "{scriptdir}" in args["--datadir"]:
        args["--datadir"] = os.path.abspath(
            args["--datadir"].format(scriptdir=os.path.dirname(os.path.abspath(__file__)))
        )
    datadir = Path(args["--datadir"])
    log.info(f"Using data directory {datadir}")

    remove_sig_tags(datadir)

    anthology = Anthology(datadir=datadir)
    anthology.load_all()

    os.makedirs(anthology.datadir / "json", exist_ok=True)

    convert_people_yaml(anthology)
    convert_venues_yaml(anthology)
    convert_sigs_yaml(anthology)

    if tracker.highest >= log.ERROR:
        log.warning("There were errors; aborting")
        exit(1)
