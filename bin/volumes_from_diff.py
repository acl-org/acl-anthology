#!/usr/bin/env python3

"""
Takes a list of XML files on STDIN, and prints all the volumes
within each of those files. e.g.,

    git diff --name-only master | ./bin/volumes_from_xml.py https://preview.aclanthology.org/BRANCH

Used to find the list of volumes to generate previews for.
"""

import sys
import argparse
import lxml.etree as etree


parser = argparse.ArgumentParser()
parser.add_argument("url_root")
args = parser.parse_args()

volumes = []
for filepath in sys.stdin:
    filepath = filepath.rstrip()
    if filepath.startswith("python/") or not filepath.endswith(".xml"):
        continue

    try:
        tree = etree.parse(filepath.rstrip())
    except Exception:
        continue

    root = tree.getroot()
    collection_id = root.attrib["id"]
    for volume in root.findall("./volume"):
        volume_name = volume.attrib["id"]
        volume_id = f"{collection_id}-{volume_name}"
        volumes.append(f"[{volume_id}]({args.url_root}/{volume_id})")

if len(volumes) > 50:
    volumes = volumes[0:50] + [f"(plus {len(volumes)-50} more...)"]

print(", ".join(volumes))
