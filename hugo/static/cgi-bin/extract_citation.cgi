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


def parse_id(anthology_id):
    """
    Parses an Anthology ID into its constituent collection ID, volume ID, and paper ID
    parts.

    Copied and trimmed from the Anthology python module to avoid the import.
    """

    if isinstance(anthology_id, tuple):
        return anthology_id

    if "-" not in anthology_id:
        return (anthology_id, None, None)

    collection_id, rest = anthology_id.split("-")
    if collection_id[0].isdigit():
        # post-2020 IDs
        if "." in rest:
            return (collection_id, *(rest.split(".")))  # type: ignore
        else:
            return (collection_id, rest, None)
    else:
        # pre-2020 IDs
        if len(rest) < 4:
            # probably volume-only identifier
            return (collection_id, rest.lstrip("0"), None)
        elif (
            collection_id.startswith("W")
            or collection_id == "C69"
            or (collection_id == "D19" and int(rest[0]) >= 5)
        ):
            paper_id = rest[2:].lstrip("0")
            return (collection_id, rest[0:2].lstrip("0"), paper_id if paper_id else "0")
        else:
            paper_id = rest[1:].lstrip("0")
            return (collection_id, rest[0], paper_id if paper_id else "0")


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
    """
    Opens the volumes file and retrieves the bibtex entry corresponding
    to the requested Anthology ID.
    """
    parsed = parse_id(anthology_id)
    volume_id = f"{parsed[0]}-{parsed[1]}"
    with open(f"../volumes/{volume_id}.bib") as f:
        # iterate through the file, reading bibtex entries
        for entry in bib_entries(f):
            if f'/{anthology_id}/' in entry:
                return entry
    return None


def get_mods_xml_entry(anthology_id):
    return None


def get_endnote_entry(anthology_id):
    return None


def get_entry(anthology_id, format):
    if format == "bib":
        return get_bibtex_entry(anthology_id)
    elif format == "xml":
        return get_mods_xml_entry(anthology_id)
    elif format == "endf":
        return get_endnote_entry(anthology_id)
    else:
        return ""


if __name__ == "__main__":
    # Get the anthology_id from the query string
    params = parse_query_string(os.environ.get("QUERY_STRING", ""))
    anthology_id = params.get("anthology_id")
    format = params.get("format")
    entry = get_entry(anthology_id, format)
    if not entry:
        print("Status: 404 Not Found")
        print("Content-Type: text/plain")
        print()
    else:
        print("Content-Type: text/plain")
        print()
        print(entry)