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

from repair_url import test_url
from anthology.utils import infer_url, indent

filename = sys.argv[1]
outfilename = sys.argv[2]
tree = etree.parse(filename)
root = tree.getroot()
collection_id = root.attrib['id']

if root.tag == 'collection':
    print(f'{filename} is already nested!')
    sys.exit(1)

new_root = etree.Element('collection')
new_root.attrib['id'] = collection_id
tree._setroot(new_root)

def make_simple_element(tag, text):
    el = etree.Element(tag)
    el.text = text
    return el

volume = None
meta = None
prev_volume_id = None

for paper in root.findall("paper"):
    paper_id = paper.attrib['id']
    if collection_id.startswith('W') or collection_id == 'C69':
        volume_width = 2
        paper_width = 2
    else:
        volume_width = 1
        paper_width = 3

    volume_id, paper_id = int(paper_id[0:volume_width]), int(paper_id[volume_width:])
    full_volume_id = f'{collection_id}-{volume_id:0{volume_width}d}'
    full_paper_id = f'{collection_id}-{volume_id}{paper_id:0{paper_width}d}'

    paper.attrib['id'] = '{}'.format(paper_id)

    # new volume
    if prev_volume_id is None or prev_volume_id != volume_id:
        meta = etree.Element('meta')
        if collection_id == 'C69':
            meta.append(make_simple_element('month', 'September'))
            meta.append(make_simple_element('year', '1969'))
            meta.append(make_simple_element('address', 'Sånga Säby, Sweden'))

        volume = etree.Element('volume')
        volume.append(meta)
        volume.attrib['id'] = str(volume_id)
        prev_volume_id = volume_id
        new_root.append(volume)

        # Add volume-level <url> tag if PDF is present
        volume_url = infer_url(full_volume_id)
        if test_url(volume_url):
            url = make_simple_element('url', full_volume_id)
            print(f"{collection_id}: inserting volume URL: {full_volume_id}")
            meta.append(url)

    # Transform paper 0 to explicit frontmatter
    if paper_id == 0:
        paper.tag = 'frontmatter'
        del paper.attrib['id']
        title = paper.find('title')
        if title is not None:
            title.tag = 'booktitle'
            meta.insert(0, title)

        frontmatter_url = infer_url(full_paper_id)
        if test_url(frontmatter_url):
            url = paper.find('url')
            if url is not None:
                url.text = f'{full_paper_id}'
            else:
                url = make_simple_element('url', full_paper_id)
                paper.append(url)
            print(f"{collection_id}: inserting frontmatter URL: {full_paper_id}")
        else:
            if paper.find('url') is not None:
                paper.remove(paper.find('url'))
                print(f"{collection_id}: removing missing frontmatter PDF: {full_paper_id}")

        # Change authors of frontmatter to editors
        authors = paper.findall('author')
        if authors is not None:
            for author in authors:
                author.tag = 'editor'

        # Remove empty abstracts (corner case)
        abstract = paper.find('abstract')
        if abstract is not None:
            if abstract.text != None:
                print('* WARNING: non-empty abstract for', paper.full_id)
            else:
                paper.remove(abstract)

        # Transfer editor keys (once)
        if volume.find('editor') is None:
            editors = paper.findall('editor')
            if editors is not None:
                for editor in editors:
                    meta.append(editor)

        # Transfer the DOI key if it's a volume entry
        doi = paper.find('doi')
        if doi is not None:
            if doi.text.endswith(full_volume_id):
                print(f'* Moving DOI entry {doi.text} from frontmatter to metadata')
                meta.append(doi)

    # Remove bibtype and bibkey
    for key_name in 'bibtype bibkey'.split():
        node = paper.find(key_name)
        if node is not None:
            paper.remove(node)

    # Move to metadata
    for key_name in 'booktitle publisher volume address month year ISBN isbn'.split():
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
            elif node_paper.tag == node_meta.tag:
                paper.remove(node_paper)

    # Take volume booktitle from first paper title if it wasn't found in the
    # frontmatter paper (some volumes have no front matter)
    if collection_id == 'C69' and meta.find('booktitle') is None and paper.find('title') is not None:
        meta.insert(0, make_simple_element('booktitle', paper.find('title').text))

    volume.append(paper)

indent(new_root)

tree.write(outfilename, encoding='UTF-8', xml_declaration=True, with_tail=True)
