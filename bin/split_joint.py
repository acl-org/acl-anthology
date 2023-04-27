#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#
# Copyright 2022 Matt Post <post@cs.jhu.edu>
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

"""
Joint.yaml contains three types of events, without distinguishing them:

* Colocated volumes, which are volumes that were both presented in
  the same conference. For example, a main conference and all its workshops.
* Joint volumes, which are volumes that are colisted by multiple venues
  (e.g., ACL'98 was joint with COLING)
* Associations between an old-style ID and a venue (e.g., W17-47 was wmt)

This files takes these, identifies them heuristically, and places them
in the following places:

* The most important piece is to attach old-style generic volumes (W17-47) with
  their main venue. This is done with an annotation in the <meta> block, e.g.,

    <volume>
        <meta>
            <venue>wmt</venue>
        </meta>
    </volume>

  Every volume must have exactly one main-venue association.
  Joint volumes are handled manually in post-processing.

* Colocated volumes (volumes presented at an event other than
  their main venue, e.g., a workshop presented at a main conference
  event) are handled by adding <colocated> tags to the <event> block.

    <collection id="2022.emnlp">
        <event>>
            <colocated>wmt</colocated>
        </event>
    </volume>

   A particularly important (pseudo-)event is the "ws" event, which ensures
   that all workshops appear in a single place.
"""

import sys
import yaml

import lxml.etree as ET
from pathlib import Path
from collections import defaultdict

from anthology.utils import build_anthology_id, infer_year

sys.path.append("/Users/mattpost/src/acl-anthology/bin")
from anthology.utils import make_simple_element, indent, is_newstyle_id  # noqa: E402
from anthology.venues import VenueIndex  # noqa: E402

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


IMPORT_DIR = Path("/Users/mattpost/src/acl-anthology/data")
XML_DIR = IMPORT_DIR / "xml"
YAML_DIR = IMPORT_DIR / "yaml"

venue_index = VenueIndex(IMPORT_DIR)

collections = {}


def get_xml(collection_id):
    if collection_id not in collections:
        xml_file = XML_DIR / f"{collection_id}.xml"

        if xml_file.exists():
            tree = ET.parse(xml_file)
        else:
            root_node = make_simple_element("collection", attrib={"id": collection_id})
            tree = ET.ElementTree(root_node)

        collections[collection_id] = tree

    return collections[collection_id].getroot()


def set_main_venue(full_volume_id, venue):
    """
    Takes a volume ID, finds the collection, and sets {venue} as the main
    venue for that volume. Idempotent.
    """
    if is_newstyle_id(full_volume_id):
        return

    collection_id, volume_id = full_volume_id.split("-")
    root_node = get_xml(collection_id)

    volume_id = str(int(volume_id))  # get rid of leading 0s
    volume_xml = root_node.find(f"./volume[@id='{volume_id}']")
    if volume_xml is None:
        print("* Fatal: no", volume_id, "in", volume_collection_id)
        sys.exit(1)
    meta_xml = volume_xml.find("./meta")
    main_venue = meta_xml.find("./venue")
    if main_venue is not None:
        main_venue.text = venue
    else:
        make_simple_element("venue", venue, parent=meta_xml)


with open(YAML_DIR / "joint.yaml") as f:
    all_venue_data = yaml.load(f, Loader=Loader)

# Build a list of volumes to venues. This will help us find workshops
# that are only associated with one venue, which we assume are identifiers
# for those workshops, rather than joint events
volume_to_venues_map = defaultdict(list)
for venue, venue_data in all_venue_data.items():
    for year, volumes in venue_data.items():
        for volume in volumes:
            volume_to_venues_map[volume].append(venue)


def venue_size(venue):
    """
    Ideally we'd use the actual paper counts, but this gets the job done.
    This is used to sort (and prefer) the smallest assigned venue to a volume.
    """
    if venue == "ws":
        return 100
    elif venue in ["acl", "aacl", "naacl", "emnlp", "coling", "lrec"]:
        return 50
    else:
        return 1


def infer_main_venue(volume):
    """
    Make a guess about the main venue.
    """
    if is_newstyle_id(volume):
        return volume.split(".")[1]
    elif len(volume_to_venues_map[volume]):
        # if there are associations, find the "lowest ranking" one
        return sorted(volume_to_venues_map[volume], key=venue_size)[0]
    else:
        return venue_index.get_slug_by_letter(volume[0])


def is_singleton(volume):
    return len(volume_to_venues_map[volume]) == 1


def is_oldstyle_workshop(volume):
    return not is_newstyle_id(volume) and (
        volume[0] == "W" or (volume[0:3] == "D19" and int(volume[4]) >= 5)
    )


for venue, venue_data in all_venue_data.items():
    for year, volumes in venue_data.items():
        collection_id = f"{year}.{venue}"

        event_name = f"{venue}-{year}"

        for volume in volumes:
            """Find the volume's XML file, and add its main venue"""

            if len(volumes) == 1:
                # IDENTIFIED
                if is_singleton(volume) and is_oldstyle_workshop(volume):
                    set_main_venue(volume, venue)

            else:
                # COLOCATED

                # 1. List each volume as colocated with the event under whose name it appears
                collection_xml = get_xml(collection_id)
                event_xml = collection_xml.find("event")
                if event_xml is None:
                    event_xml = make_simple_element(
                        "event", attrib={"id": event_name}, parent=collection_xml
                    )
                # only add if not present
                for colocated_xml in event_xml.findall("./colocated"):
                    if colocated_xml.text == volume:
                        break
                else:
                    make_simple_element("colocated", volume, parent=event_xml)

                # 2. Make sure a main venue is assigned to the volume itself
                volume_collection_id, volume_id = volume.split("-")
                if volume_id.startswith("0"):
                    volume_id = volume_id[1:]

                volume_collection_xml = get_xml(volume_collection_id)
                volume_xml = volume_collection_xml.find(f"./volume[@id='{volume_id}']")
                if volume_xml is None:
                    print(
                        "* Fatal: no volume",
                        volume_id,
                        "in",
                        volume_collection_id,
                        file=sys.stderr,
                    )
                    sys.exit(1)
                meta_xml = volume_xml.find("./meta")
                if meta_xml.find("./venue") is None:
                    main_venue = infer_main_venue(volume)
                    print(
                        f"Setting main venue({volume}) -> {main_venue} since none currently set",
                        file=sys.stderr,
                    )
                    set_main_venue(volume, main_venue)

# Now, add all workshops to the "workshop event" pages.  These will
# not naturally appear, because many/most of the workshops within them
# have been assigned to different main venues. But we want them to
# appear on the workshop venue pages so people can browse all
# workshops for a given year.
for xml_file in XML_DIR.glob("*.xml"):
    if not (xml_file.name.startswith("W") or xml_file.name.startswith("D19")):
        continue

    collection_id = xml_file.name[0:3]
    year = infer_year(collection_id)
    event_name = f"ws-{year}"

    # the volume we'll iterate over
    collection_xml = ET.parse(xml_file)

    # the volume we're adding events to
    event_collection_id = f"{year}.ws"
    event_collection_xml = get_xml(event_collection_id)
    event_xml = event_collection_xml.find("./event")
    if event_xml is None:
        event_xml = make_simple_element(
            "event", attrib={"id": event_name}, parent=event_collection_xml
        )

    for volume_xml in collection_xml.findall("./volume"):
        volume_id = volume_xml.attrib["id"]

        # skip EMNLP main
        if collection_id == "D19" and int(volume_id) < 50:
            continue

        volume_full_id = build_anthology_id(collection_id, volume_id)

        # make sure the volume isn't already listed
        for colocated_xml in event_xml.findall("./colocated"):
            if volume_full_id == colocated_xml.text:
                break
        else:
            make_simple_element("colocated", volume_full_id, parent=event_xml)

for i, (collection_id, tree) in enumerate(collections.items(), 1):
    indent(tree.getroot())

    xml_file = XML_DIR / f"{collection_id}.xml"
    tree.write(xml_file, encoding="UTF-8", xml_declaration=True)

    print("Writing", xml_file)
