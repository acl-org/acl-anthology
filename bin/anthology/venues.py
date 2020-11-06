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
import logging as log
import re
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from .utils import is_newstyle_id, deconstruct_anthology_id
from anthology.data import VENUE_FORMAT


class VenueIndex:
    def __init__(self, srcdir=None):
        self.venues, self.letters, self.joint_map = {}, {}, defaultdict(list)
        self.acronyms_by_key = {}
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
        with open("{}/yaml/venues.yaml".format(directory), "wt") as f:
            print(yaml.dump(self.venue_dict, allow_unicode=True), file=f)

    def load_from_dir(self, directory):
        with open("{}/yaml/venues.yaml".format(directory), "r") as f:
            self.venue_dict = yaml.load(f, Loader=Loader)
            venue_dict = deepcopy(self.venue_dict)
            for key, val in venue_dict.items():
                if "acronym" not in val:
                    log.critical(f"Venues must have 'acronym' - none defined for '{key}'")
                if "name" not in val:
                    log.error(f"Venues must have 'name' - none defined for '{key}'")
                if val["acronym"] in self.venues:
                    log.critical(
                        f"Venue acronyms must be unique - '{val['acronym']}' used"
                        f" for '{self.venues[val['acronym']]['slug']}' and '{key}'"
                    )

                if "is_toplevel" not in val:  # defaults to False
                    val["is_toplevel"] = False
                if "is_acl" not in val:  # defaults to False
                    val["is_acl"] = False
                if "joint" in val:
                    if isinstance(val["joint"], str):
                        val["joint"] = [val["joint"]]
                val["years"] = set()
                val["volumes"] = list()
                val["slug"] = key
                # for legacy reasons, this dict is still indexed by acronym
                # rather than key (that's what I get for not using proper
                # encapsulation --MB)
                self.venues[val["acronym"]] = val
                self.acronyms_by_key[key] = val["acronym"]

                if "oldstyle_letter" in val:
                    if not val["is_toplevel"]:
                        log.error(
                            f"Venues with old-style letter must be top-level - '{key}' is not"
                        )
                    self.letters[val["oldstyle_letter"]] = val["acronym"]

        with open("{}/yaml/joint.yaml".format(directory), "r") as f:
            map_dict = yaml.load(f, Loader=Loader)
            for venue, data in map_dict.items():
                acronym = self.acronyms_by_key[venue]
                if isinstance(data, dict):
                    idlist = [id_ for ids in data.values() for id_ in ids]
                elif isinstance(data, list):
                    idlist = data
                else:
                    log.exception(
                        f"Values in joint.yaml must be dict or list, found: {type(data)}"
                    )
                for id_ in idlist:
                    self.joint_map[id_].append(acronym)

    def get_by_letter(self, letter):
        """Get a venue acronym by first letter (e.g., Q -> TACL)."""
        try:
            return self.letters[letter]
        except KeyError:
            log.critical("Unknown venue letter: {}".format(letter))

    def get_main_venue(self, anthology_id):
        """Get a venue acronym by anthology ID (e.g., acl -> ACL)."""
        collection_id, *_ = deconstruct_anthology_id(anthology_id)
        if is_newstyle_id(collection_id):
            return self.acronyms_by_key[collection_id.split(".")[-1]]
        else:
            return self.get_by_letter(collection_id[0])

    def get_associated_venues(self, anthology_id):
        """Get a list of all venue acronyms for a given (volume) anthology ID."""
        main_venue = self.get_main_venue(anthology_id)
        venues = [main_venue]
        if "joint" in self.venues[main_venue]:
            venues += self.venues[main_venue]["joint"]
        if anthology_id in self.joint_map:
            venues += self.joint_map[anthology_id]
        return sorted(set(venues))

    def register(self, volume):
        """Register a proceedings volume with all associated venues."""
        venues = self.get_associated_venues(volume.full_id)
        for venue in venues:
            self.venues[venue]["volumes"].append(volume.full_id)
            self.venues[venue]["years"].add(volume.get("year"))
        return venues

    def items(self):
        return self.venues.items()
