# Marcel Bollmann <marcel@bollmann.me>, 2019

import logging as log
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class VenueIndex:
    def __init__(self, srcdir=None):
        self.venues, self.letters, self.ws_map, self.joint_map = {}, {}, {}, {}
        if srcdir is not None:
            self.load_from_dir(srcdir)

    def load_from_dir(self, directory):
        with open("{}/venues.yaml".format(directory), "r") as f:
            self.venues = yaml.load(f, Loader=Loader)
        with open("{}/venues_letters.yaml".format(directory), "r") as f:
            self.letters = yaml.load(f, Loader=Loader)
        with open("{}/venues_ws_map.yaml".format(directory), "r") as f:
            self.ws_map = yaml.load(f, Loader=Loader)
        with open("{}/venues_joint_map.yaml".format(directory), "r") as f:
            self.joint_map = yaml.load(f, Loader=Loader)

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
            venues.append(self.joint_map[anthology_id])
        if anthology_id[0] == "W" and anthology_id in self.ws_map:
            venues.append(self.ws_map[anthology_id])
        return sorted(set(venues))
