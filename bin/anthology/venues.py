# -*- coding: utf-8 -*-
#
# Copyright 2019-2020 Marcel Bollmann <marcel@bollmann.me>
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

from collections import defaultdict
from copy import deepcopy
from slugify import slugify
from typing import List
import logging as log
import os
import re
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from .utils import is_newstyle_id, build_anthology_id, deconstruct_anthology_id
from anthology.data import VENUE_FORMAT


class VenueIndex:
    def __init__(self, srcdir=None):
        self.venues = {}
        self.letters = {}
        self.volume_map = defaultdict(list)
        self.excluded_volume_map = defaultdict(list)
        self.acronyms = {}  # acronym -> venue
        self.acronyms_by_slug = {}  # slug -> acronym
        self.venue_dict = None
        if srcdir is not None:
            self.load_from_dir(srcdir)

    @staticmethod
    def get_slug(acronym):
        """The acronym can contain a hyphen, whereas the slug must match VENUE_FORMAT."""
        slug = slugify(acronym.replace("-", ""))
        assert (
            re.match(VENUE_FORMAT, slug) is not None
        ), f"Proposed slug '{slug}' of venue '{acronym}' doesn't match {VENUE_FORMAT}"
        return slug

    def add_venue(self, acronym, title, is_acl=False, url=None):
        """
        Adds a new venue.
        """
        slug = VenueIndex.get_slug(acronym)

        self.venue_dict[slug] = {"acronym": acronym, "name": title}
        if is_acl:
            self.venue_dict[slug]["is_acl"] = True
        if url is not None:
            self.venue_dict[slug]["url"] = url

    def dump(self, directory):
        """
        Dumps the venue database to file.
        """
        with open(f"{directory}/yaml/venues.yaml", "wt") as f:
            print(yaml.dump(self.venue_dict, allow_unicode=True), file=f)

    @staticmethod
    def read_leaves(data) -> List[str]:
        """Reads the leaves of a possibly superfluously-hierarchical data structure.
        For example:

        { "2019": ["this", "that"] } -> ["this", "that"]
        ["this", "that"] => ["this", "that"]
        """
        leaves = []
        if isinstance(data, dict):
            for subdata in data.values():
                leaves += VenueIndex.read_leaves(subdata)
        elif isinstance(data, list):
            for subdata in data:
                leaves += VenueIndex.read_leaves(subdata)
        else:
            leaves = [data]

        return leaves

    def load_from_dir(self, directory):
        self.venue_dict = {}
        for venue_file in os.listdir(f"{directory}/yaml/venues"):
            slug = venue_file.replace(".yaml", "")
            with open(f"{directory}/yaml/venues/{venue_file}", "r") as f:
                venue_dict = yaml.load(f, Loader=Loader)
                if "acronym" not in venue_dict:
                    raise Exception(
                        f"Venues must have 'acronym' - none defined for '{slug}'"
                    )
                if "name" not in venue_dict:
                    raise Exception(
                        f"Venues must have 'name' - none defined for '{slug}'"
                    )
                if venue_dict["acronym"] in self.venues:
                    raise Exception(
                        f"Venue acronyms must be unique - '{venue_dict['acronym']}' used"
                        f" for '{self.venues[venue_dict['acronym']]['slug']}' and '{slug}'"
                    )

                if "is_toplevel" not in venue_dict:  # defaults to False
                    venue_dict["is_toplevel"] = False
                if "is_acl" not in venue_dict:  # defaults to False
                    venue_dict["is_acl"] = False
                if "joint" in venue_dict:
                    if isinstance(venue_dict["joint"], str):
                        venue_dict["joint"] = [venue_dict["joint"]]
                venue_dict["years"] = set()
                venue_dict["slug"] = slug
                # for legacy reasons, this dict is still indexed by acronym
                # rather than slug (that's what I get for not using proper
                # encapsulation --MB)
                self.venues[venue_dict["acronym"]] = venue_dict
                self.acronyms_by_slug[slug] = venue_dict["acronym"]
                self.acronyms[venue_dict["acronym"]] = venue_dict

                if "oldstyle_letter" in venue_dict:
                    if not venue_dict["is_toplevel"]:
                        log.error(
                            f"Venues with old-style letter must be top-level - '{slug}' is not"
                        )
                    self.letters[venue_dict["oldstyle_letter"]] = venue_dict["acronym"]

                # explicit links from volumes to venues (joint volumes)
                venue_dict["volumes"] = VenueIndex.read_leaves(
                    venue_dict.get("volumes", [])
                )
                for volume in venue_dict["volumes"]:
                    acronym = self.acronyms_by_slug[slug]
                    self.volume_map[volume].append(acronym)

                # List of venues excluded from each volume
                venue_dict["excluded_volumes"] = VenueIndex.read_leaves(
                    venue_dict.get("excluded_volumes", [])
                )
                for volume in venue_dict["excluded_volumes"]:
                    acronym = self.acronyms_by_slug[slug]
                    self.excluded_volume_map[volume].append(acronym)

                self.venue_dict[slug] = venue_dict

        # with open(f"{directory}/yaml/joint.yaml", "r") as f:
        #     map_dict = yaml.load(f, Loader=Loader)
        #     for venue, data in map_dict.items():
        #         acronym = self.acronyms_by_slug[venue]
        #         if isinstance(data, dict):
        #             idlist = [id_ for ids in data.values() for id_ in ids]
        #         elif isinstance(data, list):
        #             idlist = data
        #         else:
        #             log.exception(
        #                 f"Values in joint.yaml must be dict or list, found: {type(data)}"
        #             )
        #         for id_ in idlist:
        #             self.joint_map[id_].append(acronym)

    def get_by_letter(self, letter):
        """Get a venue acronym by first letter (e.g., Q -> TACL)."""
        return self.letters.get(letter, None)

    def get_by_acronym(self, acronym):
        """Get a venue object by its acronym (assumes acronyms are unique)."""
        try:
            return self.acronyms[acronym]
        except KeyError:
            raise Exception(f"Unknown venue acronym: {acronym}")

    def get_main_venue(self, anthology_id):
        """Get a venue acronym by anthology volume ID.
        The Anthology ID can be a full paper ID or a volume ID.

        - 2020.acl-1 -> acl
        - W19-52 -> wmt
        - 2020.acl-long.100 -> acl
        """
        collection_id, volume_id, _ = deconstruct_anthology_id(anthology_id)
        if is_newstyle_id(collection_id):
            return self.acronyms_by_slug[collection_id.split(".")[-1]]
        else:  # old-style ID
            # The main venue is defined by the "oldstyle_letter" key in
            # the venue files.
            main_venue = self.get_by_letter(collection_id[0])
            if main_venue is None:
                # If there was no association with the letter, use joint.yaml to
                # get the venue.  As of 06/2021 this is only used for "O"
                # (ROCLING/IJCLCLP).
                try:
                    main_venue = self.volume_map[
                        build_anthology_id(collection_id, volume_id, None)
                    ][0]
                except (KeyError, IndexError):
                    raise Exception(
                        f"Old-style ID {anthology_id} isn't assigned any venue!"
                    )
            return main_venue

    def get_associated_venues(self, anthology_id):
        """Get a list of all venue acronyms for a given (volume) anthology ID."""
        main_venue = self.get_main_venue(anthology_id)
        venues = [main_venue]

        # TODO 06/2022: this should be updated for events, instead of "joint"
        if "joint" in self.venues[main_venue]:
            venues += self.venues[main_venue]["joint"]
        if anthology_id in self.volume_map:
            venues += self.volume_map[anthology_id]

        # Subtract out excluded volumes
        return sorted(set(venues) - set(self.excluded_volume_map.get(anthology_id, [])))

    def register(self, volume):
        """Register a proceedings volume with all associated venues.

        For each volume, we determine the set of associated venues, and add this volume to that
        venue. Associations are made by default links from the venue ID (e.g., "2021.acl-1" and
        P17-02 are associated with "acl"), and also by explicit listings in the individual venues
        files (e.g., "O17-1" is explicitly listed in rocling.yaml). We also skip volumes that
        were explicitly excluded in the venues file (these are volumes with default associations
        that are incorrect, such as EMNLP 2019's workshops using the "D" key).
        """
        venues = self.get_associated_venues(volume.full_id)
        for venue in venues:
            if volume.full_id not in self.venues[venue]["volumes"] and \
               volume.full_id not in self.venues[venue]["excluded_volumes"]:
                self.venues[venue]["volumes"].append(volume.full_id)
                self.venues[venue]["years"].add(volume.get("year"))

        return venues

    def items(self):
        return self.venues.items()
