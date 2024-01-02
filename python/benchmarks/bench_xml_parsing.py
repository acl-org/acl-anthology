# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
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

import os
from copy import deepcopy
from lxml import etree
from pathlib import Path

REPEAT = 3
SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))
XMLFILE = Path(f"{SCRIPTDIR}/../tests/toy_anthology/xml/2022.acl.xml")

# Names of XML elements that may appear multiple times, and should be accumulated as a list
LIST_ELEMENTS = (
    "attachment",
    "author",
    "editor",
    "video",
    "revision",
    "erratum",
    "award",
    "pwcdataset",
    "video",
    "venue",
)

# Names of XML elements that should not be parsed, so that they can be interpreted later in
# a context-specific way
DONT_PARSE_ELEMENTS = (
    "abstract",
    "title",
    "booktitle",
)


def parse_element(xml_element):
    attrib = {}
    for element in xml_element:
        # parse value
        tag = element.tag.lower()
        if tag in DONT_PARSE_ELEMENTS:
            tag = f"xml_{tag}"
            value = deepcopy(element)
        elif tag == "url":
            tag = element.attrib.get("type", "xml_url")
            value = element.text
        elif tag in ("author", "editor"):
            id_ = element.attrib.get("id", None)
            for subelement in element:
                tag = subelement.tag
                # These are guaranteed to occur at most once by the schema
                if tag == "first":
                    first = subelement.text or ""
                elif tag == "last":
                    last = subelement.text or ""
            value = (first, last, id_)
        elif tag == "pwccode":
            value = {
                "url": element.get("url"),
                "additional": element.get("additional"),
                "name": element.text,
            }
        else:
            value = element.text

        # these items get built as lists (default is to overwrite)
        if tag in LIST_ELEMENTS:
            try:
                attrib[tag].append(value)
            except KeyError:
                attrib[tag] = [value]
        else:
            attrib[tag] = value

    return attrib


def parse_single_element(element):
    tag = element.tag.lower()

    if tag in DONT_PARSE_ELEMENTS:
        tag = f"xml_{tag}"
        value = deepcopy(element)
    elif tag == "url":
        tag = element.attrib.get("type", "xml_url")
        value = element.text
    elif tag in ("author", "editor"):
        id_ = element.attrib.get("id", None)
        for subelement in element:
            tag = subelement.tag
            # These are guaranteed to occur at most once by the schema
            if tag == "first":
                first = subelement.text or ""
            elif tag == "last":
                last = subelement.text or ""
        value = (first, last, id_)
    elif tag == "pwccode":
        value = {
            "url": element.get("url"),
            "additional": element.get("additional"),
            "name": element.text,
        }
    else:
        value = element.text

    return (tag, value)


def parse_via_parse_element():
    """
    Parses <paper> elements by passing them to `parse_element()`, which
    returns a key-value hash.
    """
    for _, element in etree.iterparse(XMLFILE):
        if element.tag == "paper":
            paper = parse_element(element)
    return paper


def parse_via_parse_single_element():
    """
    Parses <paper> elements by looping over their children and passing
    them to `parse_single_element()`, then using the return value to
    build a key-value hash.

    This should result in a lot more function calls, albeit with smaller
    (simpler) XML elements.
    """
    for _, element in etree.iterparse(XMLFILE):
        if element.tag == "paper":
            paper = {}
            for subelement in element:
                tag, value = parse_single_element(subelement)
                if tag in LIST_ELEMENTS:
                    try:
                        paper[tag].append(value)
                    except KeyError:
                        paper[tag] = [value]
                else:
                    paper[tag] = value
    return paper


def parse_via_parse_and_clear_element():
    """
    Parses <paper> elements by passing them to `parse_element()`, but
    also clears them afterwards to potentially save memory.
    """
    for _, element in etree.iterparse(XMLFILE):
        if element.tag == "paper":
            paper = parse_element(element)
            element.clear()
    return paper


def bench_with_parse_element():
    for _ in range(REPEAT):
        parse_via_parse_element()


def bench_with_parse_single_element():
    for _ in range(REPEAT):
        parse_via_parse_single_element()


def bench_with_parse_and_clear_element():
    for _ in range(REPEAT):
        parse_via_parse_and_clear_element()


__benchmarks__ = [
    (
        bench_with_parse_element,
        bench_with_parse_single_element,
        "XML: parse entire <paper> vs. parse one child per function call",
    ),
    (
        bench_with_parse_element,
        bench_with_parse_and_clear_element,
        "XML: parse <paper> without vs. with clearing them afterwards",
    ),
]
