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

from lxml import etree
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape
import itertools as it
import logging
import re

from .people import PersonName
from . import data


xml_escape_or_none = lambda t: None if t is None else xml_escape(t)


def is_journal(anthology_id):
    return anthology_id[0] in ("J", "Q")


def is_volume_id(anthology_id):
    return (
        anthology_id[-3:] == "000"
        or (anthology_id[0] == "W" and anthology_id[-2:] == "00")
        or (anthology_id[:3] == "C69" and anthology_id[-2:] == "00")
    )


def to_volume_id(anthology_id):
    if anthology_id[0] == "W" or anthology_id[:3] == "C69":
        return anthology_id[:6]
    return anthology_id[:5]


def build_anthology_id(collection_id, volume_id, paper_id):
    """
    Transforms collection id, volume id, and paper id to a width-padded
    Anthology ID. e.g., ('P18', '1', '1') -> P18-1001.
    """
    if collection_id.startswith('W') or collection_id == 'C69':
        return '{}-{:02d}{:02d}'.format(collection_id, int(volume_id), int(paper_id))
    else:
        return '{}-{:01d}{:03d}'.format(collection_id, int(volume_id), int(paper_id))


def test_url(url):
    """
    Tests a URL, returning True if the URL exists, and False otherwise.
    """
    import requests

    #sys.stderr.write("retrieving {}: ".format(url))
    r = requests.head(url, allow_redirects=True)
    #sys.stderr.write("{}\n".format(r.status_code))
    return r.status_code == requests.codes.ok


def deconstruct_anthology_id(anthology_id):
    """
    Transforms an Anthology id into its constituent collection id, volume id, and paper id
    parts. e.g,

        P18-1007 -> ('P18', '1', '7')
        W18-6310 -> ('W18', '63', '10')

    Also can deconstruct Anthology volumes 

        P18-1 -> ('P18', '1', None)
        W18-63 -> ('W18', '63', None)
    """

    collection_id, rest = anthology_id.split('-')
    assert len(collection_id) == 3, "Collection IDs should be 1 letter prefix + 2 digit year"
    if collection_id.startswith('W') or collection_id.startswith('C69'):
        if (len(rest) >= 2):
            return (collection_id, str(int(rest[0:2])), str(int(rest[2:])))
        else:                   # Possible Volume only identifier
            return (collection_id, str(int(rest[0:2])), None)
    else:
        if (len(rest) >= 2):
            return (collection_id, str(int(rest[0:1])), str(int(rest[1:])))
        else:                   # Possible Volume only identifier
            return (collection_id, str(int(rest[0:1])), None)

def stringify_children(node):
    """Returns the full content of a node, including tags.

    Used for nodes that can have mixed text and HTML elements (like <b> and <i>)."""
    return "".join(
        chunk
        for chunk in it.chain(
            (xml_escape_or_none(node.text),),
            it.chain(
                *(
                    (
                        etree.tostring(child, with_tail=False, encoding=str),
                        xml_escape_or_none(child.tail),
                    )
                    for child in node.getchildren()
                )
            ),
            (xml_escape_or_none(node.tail),),
        )
        if chunk
    ).strip()


def remove_extra_whitespace(text):
    return re.sub(" +", " ", text.replace("\n", "").strip())


def infer_url(filename, prefix=data.ANTHOLOGY_URL):
    """If URL is relative, return the full Anthology URL.
    """
    if urlparse(filename).netloc:
        return filename
    return prefix.format(filename)


def infer_attachment_url(filename, parent_id=None):
    if urlparse(filename).netloc:
        return filename
    # Otherwise, treat it as an internal filename
    if parent_id is not None and not filename.startswith(parent_id):
        logging.error(
            "attachment must begin with paper ID '{}', but is '{}'".format(
                parent_id, filename
            )
        )
    return infer_url(filename, data.ATTACHMENT_URL)


_MONTH_TO_NUM = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def month_str2num(text):
    """Convert a month string to a number, e.g. February -> 2

    Returns None if the string doesn't correspond to a month.

    Not using Python's datetime here since its behaviour depends on the system
    locale."""
    return _MONTH_TO_NUM.get(text.lower(), None)


class SeverityTracker(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level=level)
        self.highest = logging.NOTSET

    def emit(self, record):
        if record.levelno > self.highest:
            self.highest = record.levelno


def clean_whitespace(text, strip='left'):
    old_text = text
    if text is not None:
        text = text.replace('\n', '')
        text = re.sub(r'\s+', ' ', text)
        if strip == 'left' or strip == 'both':
            text = text.lstrip()
        if strip == 'right' or strip == 'both':
            text = text.rstrip()
    return text


def indent(elem, level=0, internal=False):
    """
    Enforces canonical indentation: two spaces,
    with each tag on a new line, except that 'author', 'editor',
    'title', and 'booktitle' tags are placed on a single line.

    Adapted from https://stackoverflow.com/a/33956544 .
    """
    # tags that have no internal linebreaks (including children)
    oneline = elem.tag in ('author', 'editor', 'title', 'booktitle')

    elem.text = clean_whitespace(elem.text)

    if len(elem): # children
        # Set indent of first child for tags with no text
        if not oneline and (not elem.text or not elem.text.strip()):
            elem.text = '\n' + (level + 1) * '  '

        if not elem.tail or not elem.tail.strip():
            if level:
                elem.tail = '\n' + level * '  '
            else:
                elem.tail = '\n'

        # recurse
        for child in elem:
            indent(child, level + 1, internal=oneline)

        # Clean up the last child
        if oneline:
            child.tail = clean_whitespace(child.tail, strip='right')
        elif (not child.tail or not child.tail.strip()):
            child.tail = '\n' + level * '  '
    else:
        elem.text = clean_whitespace(elem.text, strip='both')

        if internal:
            elem.tail = clean_whitespace(elem.tail, strip='none')
        elif not elem.tail or not elem.tail.strip():
            elem.tail = '\n' + level * '  '

def parse_element(xml_element):
    attrib = {}
    if xml_element is None:
        return attrib

    for element in xml_element:
        # parse value
        tag = element.tag.lower()
        if tag in ("abstract", "title", "booktitle"):
            tag = "xml_{}".format(tag)
            value = element
        elif tag == "attachment":
            value = {
                "filename": element.text,
                "type": element.get("type", "attachment"),
                "url": element.text,
            }
        elif tag in ("author", "editor"):
            id_ = element.attrib.get("id", None)
            value = (PersonName.from_element(element), id_)
        elif tag in ("erratum", "revision"):
            value = {
                "value": element.text,
                "id": element.get("id"),
                "url": element.text,
            }
        elif tag == "mrf":
            value = {"filename": element.text, "src": element.get("src")}
        elif tag == "video":
            # Treat videos the same way as other attachments
            tag = "attachment"
            value = {
                "filename": element.get("href"),
                "type": element.get("tag", "video"),
                "url": element.get("href"),
            }
        elif tag in ("dataset", "software"):
            value = {
                "filename": element.text,
                "type": tag,
                "url": element.text,
            }
            tag = "attachment"
        else:
            value = element.text

        if tag == "url":
            # Convert relative URLs to canonical ones
            value = element.text if element.text.startswith('http') else data.ANTHOLOGY_URL.format(element.text)

        if tag in data.LIST_ELEMENTS:
            try:
                attrib[tag].append(value)
            except KeyError:
                attrib[tag] = [value]
        else:
            attrib[tag] = value

    return attrib


def make_simple_element(tag, attrib=None, text=None):
    """Convenience function to create an LXML node"""
    el = etree.Element(tag)
    if text:
        el.text = text
    if attrib:
        for key, value in attrib.items():
            el.attrib[key] = value
    return el


def make_nested(root):
    """
    Converts an XML tree root to the nested format (if not already converted).
    """

    collection_id = root.attrib['id']

    if root.tag == 'collection':
        return root

    new_root = make_simple_element('collection')
    new_root.attrib['id'] = collection_id
    new_root.tail = '\n'

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
        full_paper_id = f'{full_volume_id}{paper_id:0{paper_width}d}'

        paper.attrib['id'] = '{}'.format(paper_id)

        # new volume
        if prev_volume_id is None or prev_volume_id != volume_id:
            meta = make_simple_element('meta')
            if collection_id == 'C69':
                meta.append(make_simple_element('month', 'September'))
                meta.append(make_simple_element('year', '1969'))
                meta.append(make_simple_element('address', 'Sånga Säby, Sweden'))

            volume = make_simple_element('volume')
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

        # Canonicalize URL
        url = paper.find('url')
        if url is not None:
            url.text = re.sub(r'https?://(www.)?aclweb.org/anthology/', '', url.text)

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

    return new_root
