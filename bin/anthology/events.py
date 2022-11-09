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
    """
    def __init__(self):
        self.events = {}

    def add_from_xml(self,
                     event_xml,
                     venue,
                     year):

        event_name = f"{venue}-{year}"
        if not event_name in self.events:
            self.events[event_name] = {}
        self.events[event_name]["colocated"] = []

        if event_xml.findall("colocated") is not None:
            for colocated in event_xml.findall("colocated"):
                self.events[event_name]["colocated"].append(colocated.text)
