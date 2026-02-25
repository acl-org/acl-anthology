#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2025 Matt Post <post@cs.jhu.edu>
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
Takes a list of XML files on STDIN (ideally produced from a `git diff --name-only),
and print links to files that have changed. This is used to create Github-friendly
link previews.

Example usage:

    git diff --name-only master | ./bin/get_changes_from_git_diff.py https://preview.aclanthology.org/BRANCH

The argument to the script is the URL root for the preview.

"""

import sys
import argparse
import lxml.etree as etree

parser = argparse.ArgumentParser()
parser.add_argument("url_root")
args = parser.parse_args()

changeset = []
for filepath in sys.stdin:
    filepath = filepath.rstrip()

    # find volumes in this file
    if filepath.endswith(".xml"):
        tree = etree.parse(filepath.rstrip())
        root = tree.getroot()
        collection_id = root.attrib["id"]
        for volume in root.findall("./volume"):
            volume_name = volume.attrib["id"]
            volume_id = f"{collection_id}-{volume_name}"
            change = f"[{volume_id}]({args.url_root}/volumes/{volume_id})"
            changeset.append(change)

    # The FAQ has changed (no link to individual files)
    elif filepath.startswith("hugo/content/faq"):
        change = f"[FAQ]({args.url_root}/faq)"
        if change not in changeset:
            changeset.append(change)

    # Content pages have changed
    elif filepath.startswith("hugo/content/info"):
        name = filepath.split("/")[-1].replace(".md", "")
        change = f"[Info: {name}]({args.url_root}/info/{name})"
        changeset.append(change)

if len(changeset) > 50:
    changeset = changeset[0:50] + [f"(plus {len(changeset)-50} more...)"]

print(", ".join(changeset))
