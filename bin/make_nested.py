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
      <volume id="1">
        <meta>
          <booktitle>...</booktitle>
          <year>...</year>
          <month>...</month>
          <publish>...</publisher>
          <address>...</address>
        </meta>
        <paper id="1">
        ...
      </volume>
    </root>

Also removes many keys from papers, since they are more properly
inherited from their volumes:

- booktitle
- editor
- year
- month
- publisher
- address

Usage: convert_to_hierarchical.py <infilename> <outfilename>
"""

import lxml.etree as etree
import re
import sys

from repair_url import test_url, get_anth_url
from anthology.utils import is_journal

filename = sys.argv[1]
outfilename = sys.argv[2]
tree = etree.parse(filename)
root = tree.getroot()
root_id = root.attrib['id']

new_root = etree.Element('collection')
new_root.attrib['id'] = root_id
tree._setroot(new_root)

volume = None
meta = None
prev_volume_id = None

for paper in root.findall("paper"):
    paper_id = paper.attrib['id']
    if root_id.startswith('W'):
        volume_width = 2
        paper_width = 2
    else:
        volume_width = 1
        paper_width = 3

    volume_id, paper_id = int(paper_id[0:volume_width]), int(paper_id[volume_width:])

    paper.attrib['id'] = '{}'.format(paper_id)

    # new volume
    if prev_volume_id is None or prev_volume_id != volume_id:
        meta = etree.Element('meta')
        volume = etree.Element('volume')
        volume.append(meta)
        volume.attrib['id'] = str(volume_id)
        prev_volume_id = volume_id
        new_root.append(volume)

        # Add volume-level <url> tag if PDF is present
        volume_url = get_anth_url(root_id, int(volume_id), width=volume_width)
        if test_url(volume_url):
            url = etree.Element('url')
            url.tail
            url.text = volume_url.split('/')[-1]
            print("{}: inserting volume URL: {}".format(root_id, url.text), file=sys.stderr)
            meta.append(url)

    # Transform paper 0 to explicit frontmatter
    if paper_id == 0:
        paper.tag = 'frontmatter'
        del paper.attrib['id']
        paper.remove(paper.find('title'))
        url = paper.find('url')
        frontmatter_url = get_anth_url(root_id, int(volume_id), width=volume_width)
        if url is not None and test_url(volume_url):
            url.text = f'{root_id}-{volume_id:0{volume_width}d}{paper_id:0{paper_width}d}'

    # Transfer editor keys (once)
    if volume.find('editor') is None:
        editors = paper.findall('editor')
        if editors is not None:
            for editor in editors:
                meta.append(editor)

    # Remove bibtype and bibkey
    for key_name in 'bibtype bibkey'.split():
        node = paper.find(key_name)
        if node is not None:
            paper.remove(node)

    # Move to metadata
    for key_name in 'booktitle publisher address month year'.split():
        # Move the key to the volume if not present in the volume
        node_paper = paper.find(key_name)
        if node_paper is not None:
            node_meta = meta.find(key_name)
            # If not found in the volume, move it
            if node_meta is None:
                node_meta = node_paper
                if key_name == 'booktitle':
                    meta.insert(0, node_paper)
                else:
                    meta.append(node_paper)
            # If found in the volume, move only if it's redundant
            elif node_paper.text == node_meta.text:
                paper.remove(node_paper)

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
