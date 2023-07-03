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

import lxml
from attrs import define, field
from collections import defaultdict
from copy import deepcopy

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


def markup_to_latex(element: lxml.etree._Element) -> str:
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


@define
class MarkupText:
    """Text with optional markup.

    This class **should not be instantiated directly,** but only through
    its class method constructors.  This is because the internal
    representation of the markup text may change at any time.
    """

    _content: lxml.etree._Element = field()

    def as_text(self) -> str:
        """Returns the plain text with any markup stripped.

        The only transformation that will be performed is replacing
        TeX-math expressions with their corresponding Unicode
        representation, if possible.
        """
        element = deepcopy(self._content)
        for sub in element.iterfind(".//tex-math"):
            sub.text = TexMath.to_unicode(sub)
            sub.tail = None  # tail is contained within the return value of to_unicode()
        text = lxml.etree.tostring(element, encoding="unicode", method="text")
        text = remove_extra_whitespace(text)
        return text

    def as_html(self, allow_url: bool = True) -> str:
        """Returns the text with markup transformed into HTML.

        Arguments:
            allow_url: Defaults to True. If False, URLs are **not** wrapped in
                `<a href="...">` tags, but in simply `<span>` tags.
        """
        element = deepcopy(self._content)
        # TODO: can we replace all .iterfind()s with a single .iter()?
        for sub in element.iterfind(".//url"):
            if allow_url:
                sub.tag = "a"
                sub.attrib["href"] = str(sub.text)
            else:
                sub.tag = "span"
            sub.attrib["class"] = "acl-markup-url"
        for sub in element.iterfind(".//fixed-case"):
            sub.tag = "span"
            sub.attrib["class"] = "acl-fixed-case"
        for sub in element.iterfind(".//tex-math"):
            parsed_elem = TexMath.to_html(sub)
            parsed_elem.tail = sub.tail
            sub.getparent().replace(sub, parsed_elem)  # type: ignore
        html = remove_extra_whitespace(stringify_children(element))
        return html

    def as_latex(self) -> str:
        """Returns the text with markup transformed into LaTeX commands."""
        text = markup_to_latex(self._content)
        text = remove_extra_whitespace(text)
        return text

    @classmethod
    def from_xml(cls, element: lxml.etree._Element) -> MarkupText:
        """Instantiate a MarkupText object from an XML element.

        Arguments:
            element: Can be any XML element that can contain MarkupText according
                to the schema.
        """
        return cls(deepcopy(element))