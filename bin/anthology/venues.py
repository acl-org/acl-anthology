# -*- coding: utf-8 -*-
#
# Copyright 2019-2020 Marcel Bollmann <marcel@bollmann.me>
#           2022 Matt Post <post@cs.jhu.edu>
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
from slugify import slugify
import logging as log
import os
import re
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from .data import VENUE_FORMAT


class VenueIndex:
    """
    Venues make use of the following identifiers:
    - acronym: a free-form acronym (e.g., WMT, Challenge-HML, NL4XAI, NLP+CSS)
    - name: a natural language name (e.g., Workshop on NLP and Computational Social Science)
    - slug: a variant of the acronym containing only lowercase letters and digits.

    The slug is used to form the Anthology ID (e.g., {year}.{slug}-{volume}.{paper})

    The data structures in here are a bit of a mess.
    """

    def __init__(self, srcdir=None):
        # acronym (slug) to dictionary
        self.venues_by_acronym = {}
        self.venues_by_slug = {}

        # maps from old-style letters to acronyms
        self.letters_to_acronym = {}
        self.letters_to_slug = {}

        # records volumes that are explicitly listed in data/yaml/venues/ files
        self.volume_map = defaultdict(list)

        # from acronyms (slugs) to venue (dictionary)
        self.acronyms = {}
        self.acronyms_by_slug = {}

        if srcdir is not None:
            self.load_from_dir(srcdir)

    @staticmethod
    def get_slug_from_acronym(acronym):
        """
        The acronym can contain a hyphen (e.g., Challenge-HML),
        whereas the slug must match VENUE_FORMAT (lowercase, no punc)
        """
        slug = slugify(acronym.replace("-", ""))
        assert (
            re.match(VENUE_FORMAT, slug) is not None
        ), f"Proposed slug '{slug}' of venue '{acronym}' doesn't match {VENUE_FORMAT}"
        return slug

    def get_venue(self, venue_slug):
        return self.venues_by_slug[venue_slug]

    def get_acronym_by_slug(self, venue_slug):
        return self.get_venue(venue_slug)["acronym"]

    def add_venue(self, directory, acronym, title, is_acl=False, url=None):
        """
        Adds a new venue.

        Everytime a new venue is created, the corresponding yaml file is created as welll.
        """
        slug = VenueIndex.get_slug_from_acronym(acronym)

        self.venues_by_slug[slug] = {"acronym": acronym, "name": title}
        if is_acl:
            self.venues_by_slug[slug]["is_acl"] = True
        if url is not None:
            self.venues_by_slug[slug]["url"] = url

        with open(f"{directory}/yaml/venues/{slug}.yaml", "w") as f:
            yaml.dump(self.venues_by_slug[slug], f)

    def load_from_dir(self, directory):
        for venue_file in os.listdir(f"{directory}/yaml/venues"):
            slug = venue_file.replace(".yaml", "")
            with open(f"{directory}/yaml/venues/{venue_file}", "r") as f:
                venue_dict = yaml.load(f, Loader=Loader)
                if "acronym" not in venue_dict:
                    raise Exception(
                        f"Venues must have 'acronym' - none defined in '{venue_file}'"
                    )
                if "name" not in venue_dict:
                    raise Exception(
                        f"Venues must have 'name' - none defined in '{venue_file}'"
                    )
                if venue_dict["acronym"] in self.venues_by_acronym:
                    raise Exception(
                        f"Venue acronyms must be unique - '{venue_dict['acronym']}' used"
                        f" for '{self.venues_by_acronym[venue_dict['acronym']]['slug']}' and '{slug}'"
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
                venue_dict["volumes"] = []

                # for legacy reasons, this dict is still indexed by acronym
                # rather than slug (that's what I get for not using proper
                # encapsulation --MB)
                self.venues_by_acronym[venue_dict["acronym"]] = venue_dict
                self.venues_by_slug[slug] = venue_dict

                self.acronyms_by_slug[slug] = venue_dict["acronym"]
                self.acronyms[venue_dict["acronym"]] = venue_dict

                if "oldstyle_letter" in venue_dict:
                    if not venue_dict["is_toplevel"]:
                        log.error(
                            f"Venues with old-style letter must be top-level - '{slug}' is not"
                        )
                    self.letters_to_acronym[venue_dict["oldstyle_letter"]] = venue_dict[
                        "acronym"
                    ]
                    self.letters_to_slug[venue_dict["oldstyle_letter"]] = slug

    def get_acronym_by_letter(self, letter):
        """Get a venue acronym by first letter (e.g., Q -> TACL)."""
        return self.letters_to_acronym.get(letter, None)

    def get_slug_by_letter(self, letter):
        """Get a venue slug by first letter (e.g., Q -> TACL)."""
        return self.letters_to_slug.get(letter, None)

    def get_dict_by_acronym(self, acronym):
        """Get a venue object by its acronym (assumes acronyms are unique)."""
        try:
            return self.acronyms[acronym]
        except KeyError:
            raise Exception(f"Unknown venue acronym: {acronym}")

    def register(self, volume):
        """Register a proceedings volume with all associated venues.

        For each volume, we determine the set of associated venues,
        and add this volume to that venue. Associations are made in
        three ways:

        * For modern IDs, the Anthology ID itself links to the venue (e.g., 2021.acl-1)
        * For old-style IDs, there is a default association for each letter (e.g., P17-02)
        * Explicit listings in the individual venue files under data/yaml/venues.yaml
          (e.g., "O17-1" is explicitly listed in rocling.yaml).

        We also skip volumes that were explicitly excluded in the
        venues file (these are volumes with default associations that
        are incorrect, such as EMNLP 2019's workshops using the "D"
        key).

        """
        venues = volume.get_venues()
        for venue in venues:
            if volume.full_id not in self.venues_by_slug[venue]["volumes"]:
                self.venues_by_slug[venue]["volumes"].append(volume.full_id)
            self.venues_by_slug[venue]["years"].add(volume.get("year"))

        return venues

    def items(self):
        return self.venues_by_slug.items()
