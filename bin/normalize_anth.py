#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 David Wei Chiang <dchiang@nd.edu>
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

"""Try to convert ACL Anthology XML format to a standard form, in
which:
- All single and double quotes are curly
- Some characters (e.g., fullwidth chars) are mapped to standard equivalents
- Combining accents and characters are composed into single characters
- Letters that are capital "by nature" are protected with <fixed-case>
- With the `-t` option:
  - Outside of formulas, no LaTeX is used; only Unicode
  - Formulas are tagged as <tex-math> and use LaTeX

Usage: python3 normalize_anth.py [-t] <infile> <outfile>

Bugs:

- Doesn't preserve line breaks and indentation within text fields.
"""

import lxml.etree as etree
import re
import difflib
import logging
import unicodedata
import html
from latex_to_unicode import latex_to_xml
from fixedcase.protect import protect

location = ""
logging.basicConfig(format="%(levelname)s:%(location)s %(message)s", level=logging.INFO)


def filter(r):
    r.location = location
    return True


logging.getLogger().addFilter(filter)


def replace_node(old, new):
    save_tail = old.tail
    old.clear()
    old.tag = new.tag
    old.attrib.update(new.attrib)
    old.text = new.text
    old.extend(new)
    old.tail = save_tail


def maptext(node, f):
    if node.tag in ["tex-math", "url"]:
        return
    if node.text is not None:
        node.text = f(node.text)
    for child in node:
        maptext(child, f)
        if child.tail is not None:
            child.tail = f(child.tail)


def curly_quotes(s):
    # Two single quotes after a word: LaTeX for a right curly quote.
    s = re.sub(r'(\w[^\s"]*)\'\'', r"\1”", s)
    # Two single quotes (or backticks) before a word: LaTeX for a left curly quote.
    s = re.sub(r"(``|\'\')(\w)", r"“\2", s)

    # Straight double quote: If preceded by a word (possibly with
    # intervening punctuation), it's a right quote.
    s = re.sub(r'(\w[^\s"]*)"', r"\1”", s)
    # Else, if followed by a word, it's a left quote
    s = re.sub(r'"(\w)', r"“\1", s)
    if '"' in s:
        logging.warning(f"couldn't convert straight double quote in [{s}]")

    # Straight single quote
    # Exceptions for words that start with apostrophe
    s = re.sub(
        r"'(em|round|n|tis|twas|til|cause|scuse|\d0)\b", r"’\1", s, flags=re.IGNORECASE
    )
    # Otherwise, treat the same as straight double quote
    s = re.sub(r"(\w[^\s']*)'", r"\1’", s)
    s = re.sub(r"'(\w)", r"‘\1", s)
    if "'" in s:
        logging.warning(f"couldn't convert straight single quote in [{s}]")

    return s


def clean_unicode(s):
    s = s.replace("\u00ad", "")  # soft hyphen
    s = s.replace("\u2010", "-")  # hyphen

    # Some sources encode an i with an accent above using dotless i,
    # which must be converted to normal i
    s = list(s)
    for i in range(len(s) - 1):
        # bug: we should only be looking for accents above, not
        # below
        if s[i] == "ı" and unicodedata.category(s[i + 1]) == "Mn":
            s[i] = "i"
    s = "".join(s)

    # Selectively apply compatibility decomposition.
    # This converts, e.g., ﬁ to fi and ： to :, but not ² to 2.
    # Unsure: … to ...
    # More classes could be added here.
    def decompose(c):
        d = unicodedata.decomposition(c)
        if d and d.split(None, 1)[0] in ["<compat>", "<wide>", "<narrow>", "<noBreak>"]:
            return unicodedata.normalize("NFKD", c)
        else:
            return c

    s = "".join(map(decompose, s))

    # Convert combining characters when possible
    s = unicodedata.normalize("NFC", s)

    return s


def normalize(oldnode, informat):
    """
    Receives an XML 'paper' node and normalizes many of its fields, including:
    - Unescaping HTML
    - Normalizing quotes and other punctuation
    - Mapping many characters to unicode
    In addition, if the 'informat' is "latex", it will convert many LaTeX characters
    to unicode equivalents. Note that these latter LaTeX operations are not idempotent.
    """

    if oldnode.tag in [
        "url",
        "href",
        "mrf",
        "doi",
        "bibtype",
        "bibkey",
        "revision",
        "erratum",
        "attachment",
        "paper",
        "presentation",
        "dataset",
        "software",
        "video",
    ]:
        return
    elif oldnode.tag in ["author", "editor"]:
        for oldchild in oldnode:
            normalize(oldchild, informat=informat)
    else:
        if informat == "latex":
            if len(oldnode) > 0:
                logging.error(
                    "field has child elements {}".format(
                        ", ".join(child.tag for child in oldnode)
                    )
                )
            oldtext = "".join(oldnode.itertext())
            newnode = latex_to_xml(
                oldtext,
                trivial_math=True,
                fixed_case=oldnode.tag in ["title", "booktitle"],
            )
            newnode.tag = oldnode.tag
            newnode.attrib.update(oldnode.attrib)
            replace_node(oldnode, newnode)

        maptext(oldnode, html.unescape)
        maptext(oldnode, curly_quotes)
        maptext(oldnode, clean_unicode)
        if oldnode.tag in ["title", "booktitle"]:
            protect(oldnode)


if __name__ == "__main__":
    import sys
    import argparse

    ap = argparse.ArgumentParser(description="Convert Anthology XML to standard format.")
    ap.add_argument("infile", help="XML file to read")
    ap.add_argument("outfile", help="XML file to write")
    ap.add_argument(
        "-t",
        "--latex",
        action="store_true",
        help="Assume input fields are in LaTeX (not idempotent",
    )
    args = ap.parse_args()

    if args.latex:
        informat = "latex"
    else:
        informat = "xml"

    tree = etree.parse(args.infile)
    root = tree.getroot()
    if not root.tail:
        # lxml drops trailing newline
        root.tail = "\n"
    for paper in root.findall(".//paper"):
        papernum = "{} vol {} paper {}".format(
            root.attrib["id"], paper.getparent().attrib["id"], paper.attrib["id"]
        )
        for oldnode in paper:
            location = "{}:{}".format(papernum, oldnode.tag)
            normalize(oldnode, informat=informat)

    tree.write(args.outfile, encoding="UTF-8", xml_declaration=True)
