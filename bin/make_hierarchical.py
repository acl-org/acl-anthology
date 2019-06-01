#!/usr/bin/env python3

"""
Converts flat input format to hierarchical volumes,
removes padding from paper numbers, and adds the <url>
tag to <volume> if the PDF can be found.

OLD:

    <volume id="P18">
      <paper id="1001">
      ...
    </volume>

NEW:

    <collection id="P18">
      <proceedings id="1">
        <paper id="1">
        ...
      </proceedings>
    </root>

Usage: convert_to_hierarchical.py <infilename> <outfilename>
"""

import lxml.etree as etree
import re
import sys

from repair_url import test_url, get_anth_url

filename = sys.argv[1]
outfilename = sys.argv[2]
tree = etree.parse(filename)
root = tree.getroot()
root_id = root.attrib['id']

new_root = etree.Element('collection')
new_root.attrib['id'] = root_id
tree._setroot(new_root)

volume = None
prev_volume_id = None

for paper in root.findall("paper"):
    paper_id = paper.attrib['id']
    if root_id.startswith('W'):
        volume_id, paper_id = paper_id[0:2], int(paper_id[2:])
    else:
        volume_id, paper_id = paper_id[0:1], int(paper_id[1:])

    paper.attrib['id'] = '{}'.format(paper_id)
    if prev_volume_id is None or prev_volume_id != volume_id:
        volume = etree.Element('proceedings')
        volume.attrib['id'] = volume_id
        prev_volume_id = volume_id
        new_root.append(volume)

        # Now look for volumes -- (postponed until after hierarchical change)
        # for id_ in sorted(volumes):
        volume_url = get_anth_url(root_id, int(volume_id), width=len(volume_id))
        if test_url(volume_url):
            url = etree.Element('url')
            url.tail
            url.text = volume_url
            print("{}: inserting volume URL: {}".format(root_id, url.text), file=sys.stderr)
            volume.insert(0, url)

    volume.append(paper)

# Adapted from https://stackoverflow.com/a/33956544
def indent(elem, level=0):
    i = "\n" + level*"  "

    # Keep authors and editors on a single line
    if elem.tag in ['author', 'editor']:
        elem.tail = i
        return

    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

indent(new_root)

tree.write(outfilename, encoding='UTF-8', xml_declaration=True, with_tail=True)
