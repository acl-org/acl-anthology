#!/usr/bin/env python3
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

"""Usage: split_sitemap.py SITEMAP

Split up a sitemap.xml file into multiple files containing at most 50,000 entries each.  (This is Google's upper limit for re-indexing sites via sitemaps.)

Outputs files named SITEMAP.1, SITEMAP.2, etc.

Arguments:
  SITEMAP                  A sitemap file in XML format.
  -h, --help               Display this helpful text.
"""

from copy import deepcopy
from docopt import docopt
from lxml import etree
import os
import sys


SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        sitemap = etree.parse(args["SITEMAP"])
    except Exception as e:
        print("Error parsing sitemap:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        exit(1)

    root = sitemap.getroot()
    chunk_size = 50000
    i = chunk_size
    all_roots, new_root = [], None

    for url in root:
        if i >= chunk_size:
            if new_root is not None:
                all_roots.append(new_root)
            new_root = etree.Element(root.tag, nsmap={None: SITEMAP_NAMESPACE})
            i = 0
        new_root.append(deepcopy(url))
        i += 1

    if new_root is not None:
        all_roots.append(new_root)

    if len(all_roots) > 1:
        print(
            "Split {} entries into {} chunks.".format(
                chunk_size * (len(all_roots) - 1) + i, len(all_roots)
            ),
            file=sys.stderr,
        )

        basename = os.path.splitext(args["SITEMAP"])[0]
        for n, root in enumerate(all_roots):
            with open("{}_{}.xml".format(basename, n + 1), "w") as f:
                print('<?xml version="1.0" encoding="utf-8" standalone="yes" ?>', file=f)
                print(etree.tostring(root, encoding="unicode", pretty_print=True), file=f)
    else:
        print(f"Only found {i} entries, no need to split.", file=sys.stderr)
