# Copyright 2019-2023 Marcel Bollmann <marcel@bollmann.me>
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

"""Classes and functions for text markup manipulation."""

from __future__ import annotations

from attrs import define, field
from collections import defaultdict
from copy import deepcopy
from lxml import etree
from typing import Iterator

from ..utils import (
    latex_encode,
    latex_convert_quotes,
    remove_extra_whitespace,
    stringify_children,
)
from .texmath import TexMath


MARKUP_LATEX_CMDS = defaultdict(
    lambda: "{text}",
    {
        "fixed-case": "{{{text}}}",
        "b": "\\textbf{{{text}}}",
        "i": "\\textit{{{text}}}",
        "tex-math": "${text}$",
        "url": "\\url{{{text}}}",
    },
)


def markup_to_latex(element: etree._Element) -> str:
    tag = str(element.tag)
    if tag in ("tex-math", "url"):
        # These tags cannot have child elements
        return MARKUP_LATEX_CMDS[tag].format(text=element.text)

    text = latex_encode(element.text)
    for nested_element in element:
        text += markup_to_latex(nested_element)
        if nested_element.tail:
            text += latex_encode(nested_element.tail)

    text = MARKUP_LATEX_CMDS[tag].format(text=text)
    text = latex_convert_quotes(text)
    return text


@define(repr=False)
class MarkupText:
    """Text with optional markup.

    This class **should not be instantiated directly,** but only through its class method constructors.  This is because the internal representation of the markup text may change at any time.
    """

    _content: etree._Element = field()

    def __str__(self) -> str:
        return self.as_text()

    def __repr__(self) -> str:
        return f"MarkupText({self.as_html()!r})"

    def __rich_repr__(self) -> Iterator[str]:
        yield self.as_html()

    def as_text(self) -> str:
        """
        Returns:
            The plain text with any markup stripped. The only transformation that will be performed is replacing TeX-math expressions with their corresponding Unicode representation, if possible.
        """
        element = deepcopy(self._content)
        for sub in element.iterfind(".//tex-math"):
            sub.text = TexMath.to_unicode(sub)
            sub.tail = None  # tail is contained within the return value of to_unicode()
        text = etree.tostring(element, encoding="unicode", method="text")
        text = remove_extra_whitespace(text)
        return text

    def as_html(self, allow_url: bool = True) -> str:
        """
        Returns:
            Text with markup transformed into HTML.

        Arguments:
            allow_url: Defaults to True. If False, URLs are **not** wrapped in
                `<a href="...">` tags, but in simply `<span>` tags.
        """
        element = deepcopy(self._content)
        for sub in element.iter():
            if sub.tag == "url":
                if allow_url:
                    sub.tag = "a"
                    sub.attrib["href"] = str(sub.text)
                else:
                    sub.tag = "span"
                sub.attrib["class"] = "acl-markup-url"
            elif sub.tag == "fixed-case":
                sub.tag = "span"
                sub.attrib["class"] = "acl-fixed-case"
            elif sub.tag == "tex-math":
                parsed_elem = TexMath.to_html(sub)
                parsed_elem.tail = sub.tail
                sub.getparent().replace(sub, parsed_elem)  # type: ignore
        html = remove_extra_whitespace(stringify_children(element))
        return html

    def as_latex(self) -> str:
        """
        Returns:
            Text with markup transformed into LaTeX commands."""
        text = markup_to_latex(self._content)
        text = remove_extra_whitespace(text)
        return text

    def as_xml(self) -> etree._Element:
        """
        Returns:
            Text with markup represented according to the Anthology's XML schema.
        """
        return self._content

    @classmethod
    def from_string(cls, text: str) -> MarkupText:
        """
        Arguments:
            text: A simple text string without any markup.

        Returns:
            Instantiated MarkupText object corresponding to the string.
        """
        element = etree.Element("span")
        element.text = text
        return cls(element)

    @classmethod
    def from_xml(cls, element: etree._Element) -> MarkupText:
        """
        Arguments:
            element: An XML element containing valid MarkupText according to the schema.

        Returns:
            Instantiated MarkupText object corresponding to the element.
        """
        return cls(deepcopy(element))
