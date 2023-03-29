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
Normalizes the joint.yaml file in the the following format:

  venue:
    year:
      - volume 1
      - volume 2
      - ...
"""

import sys
import yaml

from anthology.utils import infer_year

try:
    from yaml import CLoader as Loader
    from yaml import CSafeDumper as Dumper
except ImportError:
    from yaml import Loader
    from yaml import SafeDumper as Dumper

data = None
with open("joint.yaml") as f:
    data = yaml.load(f, Loader=Loader)

for venue, venue_data in data.items():
    if type(venue_data) is list:
        newdata = {}
        for volume in venue_data:
            year = int(infer_year(volume.split("-")[0]))
            if year not in newdata:
                newdata[year] = []
            newdata[year].append(volume)
        data[venue] = newdata

yaml.dump(data, Dumper=Dumper, stream=sys.stdout)
