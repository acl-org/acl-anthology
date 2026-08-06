#!/usr/bin/env python3

"""
One-time script that converted the old revision style

    <revision id="2">P18-1001v2</revision>

to the new revision style that mandates an explanation

    <revision id="2" href="P18-1001v2">Added new references.</revision>
"""

import lxml.etree as etree
import sys

from anthology.utils import indent

import pathlib; input_path = pathlib.Path(sys.argv[1]); filename = str(input_path.resolve())
output_path = pathlib.Path(sys.argv[2]); outfilename = str(output_path.resolve())
tree = etree.parse(filename)
root = tree.getroot()
collection_id = root.attrib["id"]

papers = list(root.findall(".//paper")) + list(root.findall(".//frontmatter"))

for paper in papers:
    for revision in paper.findall("revision"):
        revision.attrib["href"] = revision.text
        revision.text = "No description of the changes were recorded."

indent(root)
tree.write(outfilename, encoding="UTF-8", xml_declaration=True, with_tail=True)
