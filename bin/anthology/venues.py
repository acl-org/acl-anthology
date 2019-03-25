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

from slugify import slugify
import logging as log
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class VenueIndex:
    def __init__(self, srcdir=None):
        self.venues, self.letters, self.joint_map = {}, {}, {}
        if srcdir is not None:
            self.load_from_dir(srcdir)

    def load_from_dir(self, directory):
        with open("{}/yaml/venues.yaml".format(directory), "r") as f:
            venue_dict = yaml.load(f, Loader=Loader)
            for acronym, name_str in venue_dict.items():
                name, venue_type = name_str.split(":")
                self.venues[acronym] = {
                    "name": name,
                    "is_acl": (venue_type == "ACL"),
                    "is_toplevel": False,
                    "slug": slugify(acronym),
                    "type": venue_type,
                    "years": set(),
                    "volumes": [],
                }
        with open("{}/yaml/venues_letters.yaml".format(directory), "r") as f:
            self.letters = yaml.load(f, Loader=Loader)
            for letter, acronym in self.letters.items():
                self.venues[acronym]["is_toplevel"] = True
                self.venues[acronym]["main_letter"] = letter
        with open("{}/yaml/venues_joint_map.yaml".format(directory), "r") as f:
            map_dict = yaml.load(f, Loader=Loader)
            for id_, joint in map_dict.items():
                if isinstance(joint, str):
                    joint = [joint]
                self.joint_map[id_] = joint

    def get_by_letter(self, letter):
        """Get a venue acronym by first letter (e.g., Q -> TACL)."""
        try:
            return self.letters[letter]
        except KeyError:
            log.critical("Unknown venue letter: {}".format(letter))
            log.critical(
                "Maybe '{}' needs to be defined in venues_letters.yaml?".format(letter)
            )

    def get_associated_venues(self, anthology_id):
        """Get a list of all venue acronyms for a given (volume) anthology ID."""
        venues = [self.get_by_letter(anthology_id[0])]
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
