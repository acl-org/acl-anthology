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
    if anthology_id[0] == "W":
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


def infer_attachment_url(filename):
    # If filename has a network location, it's interpreted as a complete URL
    if urlparse(filename).netloc:
        return filename
    # Otherwise, treat it as an internal filename
    return data.ATTACHMENT_URL.format(filename[0], filename[:3], filename)


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
