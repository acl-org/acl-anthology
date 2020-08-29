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

import logging as log
from copy import deepcopy
from lxml import etree
import codecs
import re

from . import latexcodec
from .texmath import TexMath
from .utils import stringify_children, remove_extra_whitespace


latexcodec.register()


_BIBTEX_MONTHS = {
    "january": "jan",
    "february": "feb",
    "march": "mar",
    "april": "apr",
    "may": "may",
    "june": "jun",
    "july": "jul",
    "august": "aug",
    "september": "sep",
    "october": "oct",
    "november": "nov",
    "december": "dec",
}


def bibtex_encode(text):
    """Encodes a text string for use in BibTeX.

    Assumes that the text does *not* contain any LaTeX commands!
    """
    if text is None:
        return ""
    text = codecs.encode(text, "latex")
    return text


def bibtex_convert_quotes(text):
    if re.match(r"(?<!\\)\"", text):
        log.warning(
            f'Straight quote (") found in text field ({text}); converting automatically, but please fix in XML'
        )
    text = re.sub(r"(?<!\\)\"\b", "``", text)
    text = re.sub(r"(?<!\\)\"", "''", text)
    return text


def bibtex_convert_month(text):
    """Converts a month string to BibTeX macros.

    If the string contains digits or is otherwise not parseable, it is returned
    unchanged with quotes around it.
    """
    text = text.lower()
    if text in _BIBTEX_MONTHS:  # most common case; map e.g. march -> mar
        return _BIBTEX_MONTHS[text]
    if text in _BIBTEX_MONTHS.values():  # already a month spec
        return text
    # Find embedded month strings
    text = '"{}"'.format(text)
    for month, macro in _BIBTEX_MONTHS.items():
        if month in text:
            text = text.replace(month, '" # {} # "'.format(macro))
            text = " # ".join(filter(lambda k: k != '""', text.split(" # ")))
    return text


def bibtex_make_entry(bibkey, bibtype, fields):
    lines = ["@{}{{{},".format(bibtype, bibkey)]
    for key, value in fields:
        if key == "author" and bibtype == "proceedings":
            key = "editor"
        if key in ("author", "editor") and "  and  " in value:
            # Print each author on a separate line
            value = "  and\n      ".join(value.split("  and  "))
        if key == "month":
            value = bibtex_convert_month(value)
        elif value is None:
            log.warning(f"Skipping empty value for {bibkey}/{key}")
            continue
        elif '"' in value:
            # Make sure not to use "" to quote values when they contain "
            value = "{{{}}}".format(value)
        else:
            # quote value
            value = '"{}"'.format(value)
        lines.append("    {} = {},".format(key, value))
    lines.append("}")
    return "\n".join(lines)


class MarkupFormatter:
    def __init__(self):
        self.texmath = TexMath()

    def as_xml(self, element):
        return remove_extra_whitespace(stringify_children(element))

    def as_text(self, element):
        element = deepcopy(element)
        for sub in element.iterfind(".//tex-math"):
            sub.text = self.texmath.to_unicode(sub)
        retval = etree.tostring(element, encoding="unicode", method="text")
        return remove_extra_whitespace(retval)

    def as_html(self, element, allow_url=False):
        element = deepcopy(element)
        # Transform elements to valid HTML
        for sub in element.iterfind(".//url"):
            if allow_url:
                sub.tag = "a"
                sub.attrib["href"] = sub.text
            else:
                sub.tag = "span"
            sub.attrib["class"] = "acl-markup-url"
        for sub in element.iterfind(".//fixed-case"):
            sub.tag = "span"
            sub.attrib["class"] = "acl-fixed-case"
        for sub in element.iterfind(".//tex-math"):
            parsed_elem = self.texmath.to_html(sub)
            parsed_elem.tail = sub.tail
            sub.getparent().replace(sub, parsed_elem)
        retval = stringify_children(element)
        return remove_extra_whitespace(retval)

    def as_latex(self, element):
        # following convert_xml_text_markup in anth2bib.py
        if element.tag in ["tex-math", "url"]:
            if len(element) > 0:
                log.warning("<{}> element has children".format(element.tag))
            text = element.text
        else:
            text = bibtex_encode(element.text)
        for nested_element in element:
            text += self.as_latex(nested_element)
            text += bibtex_encode(nested_element.tail)
        if element.tag == "fixed-case":
            text = "{{{}}}".format(text)
        elif element.tag == "b":
            text = "\\textbf{{{}}}".format(text)
        elif element.tag == "i":
            text = "\\textit{{{}}}".format(text)
        elif element.tag == "tex-math":
            text = "${}$".format(text)
        elif element.tag == "url":
            text = "\\url{{{}}}".format(text)
        text = bibtex_convert_quotes(text)
        return remove_extra_whitespace(text)

    def __call__(self, element, form, **kwargs):
        if element is None:
            return ""
        if form == "xml":
            return self.as_xml(element)
        elif form in ("plain", "text"):
            return self.as_text(element)
        elif form == "html":
            return self.as_html(element, **kwargs)
        elif form == "latex":
            return self.as_latex(element)
        raise ValueError("Unknown format: {}".format(form))
