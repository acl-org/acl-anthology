#!/usr/bin/env python3

"""Matt Post
June 2022

Takes the joint.yaml file and splits its entries out into the
individual conference files unders venues/. This is part of the
process of separating out joint events (where a particular volume
properly belongs to multiple venues) from colocated events (that
have separate proceedings but happen to have taken place at
the same time, e.g., workshops attached to a conference).
"""

import os
import sys
import yaml

try:
    from yaml import CLoader as Loader
    from yaml import CSafeDumper as Dumper
except ImportError:
    from yaml import Loader
    from yaml import SafeDumper as Dumper

with open("joint.yaml") as f:
    data = yaml.load(f, Loader=Loader)

    for venue, venue_data in data.items():
        if venue in ["acl", "naacl", "emnlp"]:
            continue
        venue_data = {"volumes": venue_data}
        print(venue, venue_data, file=sys.stderr)
        if not os.path.exists(f"venues/{venue}.yaml"):
            print(f"Can't find venues/{venue}.yaml", file=sys.stderr)
            continue
        with open(f"venues/{venue}.yaml", "at") as outf:
            yaml.dump(venue_data, Dumper=Dumper, stream=outf)
