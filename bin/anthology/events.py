# -*- coding: utf-8 -*-
#
# Copyright 2019-2020 Marcel Bollmann <marcel@bollmann.me>
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

from collections import defaultdict
from copy import deepcopy
from slugify import slugify
from typing import List
import logging as log
import os
import re


class EventIndex:
    """
    Keeps track of all events in the anthology and their relation to venues and volumes.
    Events are both explicitly represented in a collections <event> block, and are also
    implicit: every volume has one or more <venue> tags, as well as a year, and this information
    is used to add each volume to its event.

    In the future, we may wish to do away with this implicit association, and instead require
    that it all be made explicit.
    """

    def __init__(self, venue_index):
        self.events = {}
        self.venue_index = venue_index

    def register_event(self, event_xml):
        """
        Parses event XML and registers all colocated volumes.
        """
        event = event_xml.attrib["id"]
        for child_xml in event_xml:
            if child_xml.tag == "title":
                self.set_title(child_xml.text, event)
            elif child_xml.tag == "colocated":
                self.register_volume(child_xml.text, event)

    def set_title(self, title, event):
        if event not in self.events:
            self.events[event] = {
                "title": None,
                "volumes": [],
            }
        self.events[event]["title"] = title

    def register_volume(self, volume: str, event: str):
        """
        Adds a volume to an event.

        :param volume: The full volume ID (e.g., P19-1, 2022.acl-long)
        :param event: The event (e.g., acl-2019, acl-2022)
        """
        if event not in self.events:
            venue, year = event.split("-")
            venue_name = self.venue_index.get_venue(venue)["name"]
            self.events[event] = {
                "title": f"{venue_name} ({year})",
                "volumes": [],
            }

        if volume not in self.events[event]["volumes"]:
            self.events[event]["volumes"].append(volume)

    def items(self):
        return self.events.items()
