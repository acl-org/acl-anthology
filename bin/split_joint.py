#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#
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

"""
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
        # assume these are colocated, which is usually the case
        if venue in ["acl", "naacl", "emnlp", "coling", "lrec"]:
            continue

        # the rest of the entries we assume are truly joint
        # (i.e, different names for the same event, or links to the real name)
        venue_data = {"volumes": venue_data}
        print(venue, venue_data, file=sys.stderr)
        if not os.path.exists(f"venues/{venue}.yaml"):
            print(f"Can't find venues/{venue}.yaml", file=sys.stderr)
            continue
        with open(f"venues/{venue}.yaml", "at") as outf:
            yaml.dump(venue_data, Dumper=Dumper, stream=outf)
