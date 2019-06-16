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


def infer_attachment_url(filename, parent_id=None):
    # If filename has a network location, it's interpreted as a complete URL
    if urlparse(filename).netloc:
        return filename
    # Otherwise, treat it as an internal filename
    if parent_id is not None and not filename.startswith(parent_id):
        logging.error(
            "attachment must begin with paper ID '{}', but is '{}'".format(
                parent_id, filename
            )
        )
    return data.ATTACHMENT_URL.format(filename)


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


# Adapted from https://stackoverflow.com/a/33956544
def indent(elem, level=0, internal=False):
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
                elem.tail = ''

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
