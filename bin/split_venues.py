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
Takes each venue and writes its data to a new file under venues/
"""

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
