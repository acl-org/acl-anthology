# Copyright 2019-2025 Marcel Bollmann <marcel@bollmann.me>
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

from attrs import define, field, validators as v
from collections import defaultdict
from copy import deepcopy
from functools import total_ordering
from lxml import etree
from typing import Iterator, Optional, SupportsIndex
from xml.sax.saxutils import escape as xml_escape

from ..utils import (
    clean_unicode,
    latex_encode,
    latex_convert_quotes,
    parse_latex_to_xml,
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
    return text


@define(repr=False)
@total_ordering
class MarkupText:
    """Text with optional markup.

    Warning:
        This class **should not be instantiated directly.**  Use its class method constructors instead.

    Example:
        ```python
        title = MarkupText.from_("A Structured Review of the Validity of BLEU")
        title = MarkupText.from_("TTCS$^{\\mathcal{E}}$: a Vectorial Resource for Computing Conceptual Similarity")
        ```

    Note:
        This class implements a limited subset of string methods to make common operations more convenient, for example:

        ```python
        title = MarkupText.from_string("A Structured Review of the Validity of BLEU")
        title == "A Structured Review of the Validity of BLEU"  # True
        "BLEU" in title  # True
        title.startswith("A ")  # True
        ```

        These operate on the [stringified XML representation][acl_anthology.text.markuptext.MarkupText.as_xml] of the class.
    """

    # IMPLEMENTATION NOTE: Deepcopy-ing (or newly instantiating) etree._Element
    # is very expensive, as shown by profiling. Therefore, markup elements
    # which don't actually contain any markup are simply stored as
    # strings. This makes the implementation slightly more verbose (we need to
    # check everywhere whether we're dealing with etree._Element or str), but
    # much faster. ---For further optimization, we could explore if there's an
    # alternative that doesn't require deepcopy-ing XML elements at all.
    _content: etree._Element | str = field(validator=v.instance_of((etree._Element, str)))

    # For caching
    _html: Optional[str] = field(init=False, default=None)
    _latex: Optional[str] = field(init=False, default=None)
    _text: Optional[str] = field(init=False, default=None)
    _xml: Optional[str] = field(init=False, default=None)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return (key in self.as_text()) or (key in self.as_xml())
        return False  # pragma: no cover

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.as_xml() == other
        elif isinstance(other, MarkupText):
            return self.as_xml() == other.as_xml()
        return False  # pragma: no cover

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.as_xml() < other
        elif isinstance(other, MarkupText):
            return self.as_xml() < other.as_xml()
        return False  # pragma: no cover

    def __len__(self) -> int:
        return len(self.as_text())

    def __str__(self) -> str:
        return self.as_text()

    def __repr__(self) -> str:
        return f"<MarkupText {self.as_html()!r}>"

    def __rich_repr__(self) -> Iterator[str]:
        yield self.as_xml()

    @property
    def contains_markup(self) -> bool:
        """True if this text contains markup; False if it is a plain string."""
        return isinstance(self._content, etree._Element)

    def as_text(self) -> str:
        """
        Returns:
            The plain text with any markup stripped. The only transformation that will be performed is replacing TeX-math expressions with their corresponding Unicode representation, if possible.
        """
        if isinstance(self._content, str):
            return remove_extra_whitespace(self._content)
        if self._text is not None:
            return self._text
        element = deepcopy(self._content)
        for sub in element.iterfind(".//tex-math"):
            sub.text = TexMath.to_unicode(sub)
        text = etree.tostring(element, encoding="unicode", method="text")
        self._text = remove_extra_whitespace(text)
        return self._text

    def as_html(self, allow_url: bool = True) -> str:
        """
        Returns:
            Text with markup transformed into HTML.

        Arguments:
            allow_url: Defaults to True. If False, URLs are **not** wrapped in
                `<a href="...">` tags, but in simply `<span>` tags.
        """
        if isinstance(self._content, str):
            return xml_escape(remove_extra_whitespace(self._content))
        if self._html is not None:
            return self._html
        element = deepcopy(self._content)
        for sub in element.iter():
            if sub.tag == "url":
                if allow_url:
                    sub.tag = "a"
                    sub.set("href", str(sub.text))
                else:
                    sub.tag = "span"
                sub.set("class", "acl-markup-url")
            elif sub.tag == "fixed-case":
                sub.tag = "span"
                sub.set("class", "acl-fixed-case")
            elif sub.tag == "tex-math":
                parsed_elem = TexMath.to_html(sub)
                parsed_elem.tail = sub.tail
                sub.getparent().replace(sub, parsed_elem)  # type: ignore
            elif len(sub) == 0 and sub.text is None:
                sub.text = ""
        self._html = remove_extra_whitespace(stringify_children(element))
        return self._html

    def as_latex(self) -> str:
        """
        Returns:
            Text with markup transformed into LaTeX commands.
        """
        if self._latex is not None:
            return self._latex
        if isinstance(self._content, str):
            latex = latex_encode(self._content)
        else:
            latex = markup_to_latex(self._content)
        self._latex = remove_extra_whitespace(latex_convert_quotes(latex))
        return self._latex

    def as_xml(self) -> str:
        """
        Returns:
            Text with markup in the original XML format.
        """
        if isinstance(self._content, str):
            return xml_escape(self._content)
        if self._xml is None:
            self._xml = stringify_children(self._content)
        return self._xml

    @classmethod
    def from_string(cls, text: str, clean: bool = True) -> MarkupText:
        """
        Arguments:
            text: A simple text string without any markup.
            clean: If True, applies the Anthology's [Unicode normalization][acl_anthology.utils.text.clean_unicode].

        Returns:
            Instantiated MarkupText object corresponding to the string.
        """
        if clean:
            return cls(clean_unicode(text))
        return cls(text)

    @classmethod
    def from_latex(cls, text: str, clean: bool = True) -> MarkupText:
        """
        Arguments:
            text: A text string potentially containing LaTeX markup.
            clean: If True, applies the Anthology's [Unicode normalization][acl_anthology.utils.text.clean_unicode].

        Returns:
            Instantiated MarkupText object corresponding to the string.
        """
        if clean:
            text = clean_unicode(text)
        element = parse_latex_to_xml(text, use_heuristics=False)
        return cls.from_xml(element)

    @classmethod
    def from_latex_maybe(cls, text: str, clean: bool = True) -> MarkupText:
        """
        Like `from_latex()`, but can be used if it is unclear if the string is plain text or LaTeX.  Will prevent percentage signs being interpreted as LaTeX comments, and apply a heuristic to decide if a tilde is literal or a non-breaking space.

        Arguments:
            text: A text string potentially in plain text or LaTeX format.
            clean: If True, applies the Anthology's [Unicode normalization][acl_anthology.utils.text.clean_unicode].

        Returns:
            Instantiated MarkupText object corresponding to the string.
        """
        if clean:
            text = clean_unicode(text)
        element = parse_latex_to_xml(text, use_heuristics=True)
        return cls.from_xml(element)

    @classmethod
    def from_xml(cls, element: etree._Element) -> MarkupText:
        """
        Arguments:
            element: An XML element containing valid MarkupText according to the schema.

        Returns:
            Instantiated MarkupText object corresponding to the element.
        """
        if len(element):
            return cls(deepcopy(element))
        return cls(str(element.text) if element.text is not None else "")

    @classmethod
    def from_(cls, content: etree._Element | str) -> MarkupText:
        """Instantiate MarkupText from an XML element or a string, heuristically parsing any supported markup.

        - If called with an XML element, assumes it uses the Anthology's markup format and calls [`from_xml()`][acl_anthology.text.markuptext.MarkupText.from_xml].
        - If called with a string, assumes the string might contain markup and will try to intelligently parse it.  At the moment, only LaTeX markup is supported, which means that the effect of this is identical to calling [`from_latex_maybe()`][acl_anthology.text.markuptext.MarkupText.from_latex_maybe], but this may change if we support different types of markup in the future.

        Note:
            If you want more fine-grained control over markup detection, call one of the more specific builder functions instead.

        Arguments:
            content: A string potentially containing markup, or an XML element containing valid MarkupText according to the schema.

        Returns:
            Instantiated MarkupText object corresponding to the content.
        """
        if isinstance(content, etree._Element):
            return cls.from_xml(content)
        elif isinstance(content, str):
            return cls.from_latex_maybe(content)
        else:  # pragma: no cover
            raise TypeError(f"Cannot instantiate MarkupText from {type(content)}")

    def to_xml(self, tag: str = "span") -> etree._Element:
        """
        Arguments:
            tag: Name of outer tag in which the text should be wrapped.

        Returns:
            A serialization of this MarkupText in Anthology XML format.
        """
        if isinstance(self._content, str):
            element = etree.Element(tag)
            if self._content:
                element.text = self._content
        else:
            element = deepcopy(self._content)
            element.tag = tag
        return element

    ### STRING METHODS

    def endswith(
        self,
        suffix: str | tuple[str, ...],
        start: Optional[SupportsIndex] = None,
        end: Optional[SupportsIndex] = None,
    ) -> bool:
        """Return True if the string ends with the specified suffix, False otherwise.

        Equivalent to `self.as_xml().endswith(...)`.
        """
        return self.as_xml().endswith(suffix, start, end)

    def startswith(
        self,
        prefix: str | tuple[str, ...],
        start: Optional[SupportsIndex] = None,
        end: Optional[SupportsIndex] = None,
    ) -> bool:
        """Return True if the string starts with the specified prefix, False otherwise.

        Equivalent to `self.as_xml().startswith(...)`.
        """
        return self.as_xml().startswith(prefix, start, end)


def to_markuptext(value: object) -> MarkupText:
    if isinstance(value, MarkupText):
        return value
    # MarkupText.from_ already raises TypeError, so let's not duplicate that here
    return MarkupText.from_(value)  # type: ignore[arg-type]
