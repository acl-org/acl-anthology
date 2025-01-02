#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 Matt Post <post@cs.jhu.edu>
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
A Python CGI script. Takes the anthology_id parameter, finds the volume,
and then loads that file from ../{volume_id}.bib, which it opens to
search for the appropriate BibTeX entry. This is then printed to STDOUT.

The volume bibtex has lines like the following:

@proceedings{acl-2024-long,
    title = "Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
    editor = "Ku, Lun-Wei  and
      Martins, Andre  and
      Srikumar, Vivek",
    month = aug,
    year = "2024",
    address = "Bangkok, Thailand",
    publisher = "Association for Computational Linguistics",
    url = "https://preview.aclanthology.org/dont-generate-bib-files/2024.acl-long.0/"
}

To find the appropriate entry, walk through the file, reading an entry at a time.
If the entry has a "url" field containing the anthology_id, return that entry.

To test, you can pass the query string in as an environment variable:

    QUERY_STRING="anthology_id=2024.acl-long.1" python generate_bib.cgi

This needs to be done in a sister directory of the volumes/ directory.
"""

import os
import sys
import acl_anthology


def parse_query_string(query_string):
    """
    Parse the query string into a dictionary.
    """
    return dict(q.split("=") for q in query_string.split("&"))


def bib_entries(f):
    """
    Create an iterator that iterates over bib entries in a file.
    """
    entry = ""
    for line in f:
        if line.strip() == "}":
            entry += line
            yield entry
            entry = ""
        else:
            entry += line


def get_bibtex_entry(anthology_id):
    # Get the volume_id from the anthology_id
    parsed = acl_anthology.utils.parse_id(anthology_id)
    volume_id = f"{parsed[0]}-{parsed[1]}"
    with open(f"../volumes/{volume_id}.bib") as f:
        # iterate through the file, reading bibtex entries
        for entry in bib_entries(f):
            if f'/{anthology_id}/' in entry:
                return entry
    return None


if __name__ == "__main__":
    print("Content-Type: text/plain\n")

    # Get the anthology_id from the query string
    params = parse_query_string(os.environ.get("QUERY_STRING", ""))
    anthology_id = params.get("anthology_id")
    if not anthology_id:
        print("Error: anthology_id not provided")
        sys.exit(1)

    bibtex_entry = get_bibtex_entry(anthology_id)
    print(bibtex_entry)
