# Marcel Bollmann <marcel@bollmann.me>, 2019

from collections import namedtuple
import logging as log
import yaml
from .data import SIG_FILES

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


SIGEvent = namedtuple(
    "SIGEvent",
    ["anthology_id", "name", "url", "year"],
    defaults=[None, None, None, None],
)


class SIGIndex:
    def __init__(self, srcdir=None):
        self.sigs = {}
        if srcdir is not None:
            self.load_from_dir(srcdir)

    def load_from_dir(self, directory):
        for filename in SIG_FILES:
            log.debug("Instantiating SIG from {}...".format(filename))
            with open("{}/{}".format(directory, filename), "r") as f:
                data = yaml.load(f, Loader=Loader)
                sig = SIG.from_dict(data)
                self.sigs[sig.acronym] = sig

    def get_associated_sigs(self, anthology_id):
        return [
            acronym
            for acronym, sig in self.sigs.items()
            if sig.is_associated_with(anthology_id)
        ]


class SIG:
    def __init__(self, acronym, name, url):
        self.acronym = acronym
        self.name = name
        self.url = url
        self._data = {}
        self._associated_events = []

    def from_dict(dict_):
        sig = SIG(dict_["ShortName"], dict_["Name"], dict_.get("URL", None))
        sig.data = dict_
        return sig

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, dict_):
        self._data = dict_
        self._associated_events = []
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

    def is_associated_with(self, anthology_id):
        return any(ev.anthology_id == anthology_id for ev in self._associated_events)
