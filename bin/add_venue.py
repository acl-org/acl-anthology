#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 Matt Post <post@cs.jhu.edu>
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

"""Adds a venue to the data/yaml/venues.yaml file.
Usage:

    add_venue.py acronym "name" [--url URL] [--acl]
"""

import argparse
import os
import sys

from slugify import slugify

from anthology.venues import VenueIndex


def main(args):
    datadir = os.path.join(os.path.dirname(sys.argv[0]), "..", "data")
    venues = VenueIndex(srcdir=datadir)

    print(f"Adding '{args.acronym}' ({args.name})")
    venues.add_venue(args.acronym, args.name, is_acl=args.acl, url=args.url)

    venues.dump(datadir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("acronym", help="Venue acronym (e.g., BlackboxNLP)")
    parser.add_argument(
        "name",
        help="Venue name (e.g., Workshop on analyzing and interpreting neural networks for NLP)",
    )
    parser.add_argument("--acl", action="store_true", help="Venue is an ACL venue")
    parser.add_argument("--url", help="Venue URL")
    args = parser.parse_args()

    main(args)
