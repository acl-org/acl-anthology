#!/usr/bin/env python3
# -*- coding: utf-8  -*-
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
Used once to add an explicit <venue> tag to the meta block of all volumes.
Part of the November 2022 splitting of venues and events.
(Github issues #1164 and #1896).
"""

import argparse
import os

from anthology.utils import indent

import lxml.etree as ET

from anthology.utils import (
    build_anthology_id,
    is_newstyle_id,
    make_simple_element,
    deconstruct_anthology_id,
)
from anthology.venues import VenueIndex
from anthology.utils import infer_year

venues = VenueIndex("/Users/mattpost/src/acl-anthology/data")


def get_main_venue(anthology_id):
    """Get a venue identifier from an Anthology ID.
    The Anthology ID can be a full paper ID or a volume ID.

    - 2020.acl-1 -> acl
    - W19-52 -> wmt
    - 2020.acl-long.100 -> acl

    The logic for this is straightforward for newstyle IDs, since the venue
    slug is contained in the name. For old-style IDs, we have to infer it,
    using the following steps:
    - if the volume letter is not W,
        - if the volume is not in the excluded map for the venue associated with
        that volume, return the venue
        - if it is excluded, return its explicit association
    - else, return the volume mapping (hopefully it's been manually associated
        with some venue)
    * else return "WS"
    """
    collection_id, volume_id, _ = deconstruct_anthology_id(anthology_id)
    if is_newstyle_id(collection_id):
        return collection_id.split(".")[1]
    else:  # old-style ID
        # The main venue is defined by the "oldstyle_letter" key in
        # the venue files.
        collection_id[0]

        # If there was no association with the letter, the volume should
        # be listed in one of the files in data/yaml/venues/*.yaml. For
        # example, W17-47 is associated with WMT.
        main_venue = venues.get_slug_by_letter(collection_id[0])
        if volume_id is not None:
            pass

        if main_venue is None:
            raise Exception(f"Old-style ID {anthology_id} isn't assigned any venue!")

        return main_venue


def main(args):
    for xml_file in os.listdir(args.data_dir):
        xml_file = args.data_dir + "/" + xml_file

        if not xml_file.endswith(".xml"):
            continue

        tree = ET.parse(xml_file)
        root = tree.getroot()

        collection_id = root.attrib["id"]
        infer_year(collection_id)

        changed_one = False
        for volume_xml in tree.getroot():
            volume_id = volume_xml.attrib["id"]

            full_volume_id = build_anthology_id(collection_id, volume_id)

            meta_xml = volume_xml.find("meta")
            venue_xml = meta_xml.find("venue")
            if venue_xml is None:
                venue = get_main_venue(full_volume_id)
                make_simple_element("venue", venue, parent=meta_xml)
                print(f"Setting venue({full_volume_id}) -> {venue}")
                changed_one = True

        if changed_one:
            indent(root)
            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data", "xml")
    )
    args = parser.parse_args()

    main(args)
