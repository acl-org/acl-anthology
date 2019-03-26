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

from collections import defaultdict, namedtuple
from glob import glob
from slugify import slugify
import logging as log
import yaml
from .papers import to_volume_id

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


SIGEvent = namedtuple(
    "SIGEvent",
    ["anthology_id", "name", "url", "year"],
    defaults=[None, None, None, None],
)


def _sigevent_to_repr(event):
    if event.anthology_id is not None:
        # For some reason, SIG files point to the front matter, not to the
        # containing proceedings volume -- change that here
        return to_volume_id(event.anthology_id)
    return {"name": event.name, "url": event.url}


class SIGIndex:
    def __init__(self, srcdir=None):
        self.sigs = {}
        if srcdir is not None:
            self.load_from_dir(srcdir)

    def load_from_dir(self, directory):
        for filename in glob("{}/yaml/sigs/*.yaml".format(directory)):
            log.debug("Instantiating SIG from {}...".format(filename))
            with open(filename, "r") as f:
                data = yaml.load(f, Loader=Loader)
                sig = SIG.from_dict(data)
                self.sigs[sig.acronym] = sig

    def get_associated_sigs(self, anthology_id):
        return [
            acronym
            for acronym, sig in self.sigs.items()
            if sig.is_associated_with(anthology_id)
        ]

    def items(self):
        return self.sigs.items()


class SIG:
    def __init__(self, acronym, name, url):
        self.acronym = acronym
        self.name = name
        self.url = url
        self._data = {}
        self._associated_events = []
        self.events_by_year = {}

    def from_dict(dict_):
        sig = SIG(dict_["ShortName"], dict_["Name"], dict_.get("URL", None))
        sig.data = dict_
        return sig

    @property
    def associated_events(self):
        return self._associated_events

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, dict_):
        self._data = dict_
        self._associated_events = []
        self.events_by_year = defaultdict(list)
        for eventdicts in dict_["Meetings"]:
            for year, events in eventdicts.items():
                for event in events:
                    if isinstance(event, str):
                        ev = SIGEvent(anthology_id=event, year=year)
                    elif isinstance(event, dict):
                        ev = SIGEvent(
                            name=event["Name"], url=event.get("URL", None), year=year
                        )
                    else:
                        log.warning(
                            "In SIG '{}': Unknown event format: {}".format(
                                self.acronym, type(event)
                            )
                        )
                    self._associated_events.append(ev)
                    self.events_by_year[year].append(ev)

    @property
    def slug(self):
        return slugify(self.acronym)

    @property
    def volumes_by_year(self):
        return {
            y: [_sigevent_to_repr(e) for e in k] for y, k in self.events_by_year.items()
        }

    @property
    def years(self):
        return self.events_by_year.keys()

    def is_associated_with(self, anthology_id):
        return any(ev.anthology_id == anthology_id for ev in self._associated_events)
