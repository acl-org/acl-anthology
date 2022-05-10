#!/usr/bin/env python3

import sys
import yaml

try:
    from yaml import CLoader as Loader
    from yaml import CSafeDumper as Dumper
except ImportError:
    from yaml import Loader
    from yaml import SafeDumper as Dumper

with open("venues.yaml") as f:
    data = yaml.load(f, Loader=Loader)

    for venue, venue_data in data.items():
        print(venue, venue_data)
        with open(f"venues/{venue}.yaml", "w") as outf:
            yaml.dump(venue_data, Dumper=Dumper, stream=outf)

