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
import csv
import logging as log
import os
import TexSoup


FUNCTION_NAMES = ("lim", "log")


def _append_text(text, trg):
    if not text:
        return
    if len(trg):
        if trg[-1].tail is not None:
            trg[-1].tail += text
        else:
            trg[-1].tail = text
    else:
        if trg.text is not None:
            trg.text += text
        else:
            trg.text = text


class TexMath:
    """Interpreter and converter for TeX inline math expressions.

    This class uses TexSoup (https://github.com/alvinwan/TexSoup) to parse a TeX
    expression and converts it to valid HTML.  The conversion combines a small
    number of handwritten rules with a mapping of LaTeX math mode commands to
    Unicode symbols (http://milde.users.sourceforge.net/LUCR/Math/).  Parts that
    cannot be interpreted using this simple method are preserved as raw LaTeX.
    """

    def __init__(self, symbolsfile=None):
        self.cmd_map = {}
        if symbolsfile is None:
            symbolsfile = "{}/{}".format(
                os.path.dirname(os.path.abspath(__file__)), "unimathsymbols.txt"
            )
        self.load_symbols(symbolsfile)

    def load_symbols(self, filename):
        with open(filename, "r", encoding="utf8") as f:
            reader = csv.reader(f, delimiter="^")
            for row in reader:
                if row[0].startswith("#"):  # comment
                    continue
                assert len(row) == 8, "Expect eight-column format"
                char, cmd = row[1], row[2]
                if cmd.startswith("\\"):
                    self.cmd_map[cmd[1:]] = char
                if row[-1].startswith("= ") and ", " in row[-1]:
                    # last column sometimes contains alternative command
                    cmd = row[-1][2:].split(", ")[0]
                    if cmd.startswith("\\"):
                        self.cmd_map[cmd[1:]] = char

    def _parse(self, everything, trg):
        """Parses a list of TeX constituents into an lxml.etree._Element.

        Arguments:
            everything: An iterator over TeX constituents as provided by TexSoup
            trg: The lxml.etree._Element to parse the expression into

        The approach of iterating over the TeX constituents roughly follows
        <https://github.com/alvinwan/TexSoup/blob/master/examples/list_everything.py>.
        """
        sxscript = False  # Tracks whether we're in a subscript/superscript
        for code in everything:
            if isinstance(code, TexSoup.TexCmd):
                # code is a TeX command
                self._parse_command(code, trg)
            elif isinstance(code, TexSoup.TokenWithPosition):
                # code is text
                sxscript = self._parse_text(code, trg)
            elif isinstance(code, TexSoup.Arg):
                # If in subscript/superscript, wrap the entire element in respective tag
                if sxscript:
                    my_trg = etree.Element(sxscript)
                    self._parse(TexSoup.TexSoup(code.value).expr.everything, my_trg)
                    trg.append(my_trg)
                    sxscript = False
                # Otherwise, just parse it normally
                else:
                    self._parse(TexSoup.TexSoup(code.value).expr.everything, trg)
            else:
                log.error(
                    "TeX-math parser got unhandled element: {}".format(type(code))
                )

    def _parse_command(self, code, trg):
        args = list(code.arguments)
        name = str(code.name)
        # TexSoup doesn't parse curly brackets correctly
        if name[0] in ("{", "}"):
            args = list(TexSoup.TexSoup(name[1:]).expr.everything) + args
            name = name[0]
        # Check if the command is in the list of known Unicode mappings
        if name in self.cmd_map:
            _append_text(self.cmd_map[name], trg)
            self._parse(args, trg)
        # Check if command + arguments is in the list of known Unicode mappings
        # (this covers commands like "\mathcal{A}", which have their own entries)
        elif str(code)[1:] in self.cmd_map:
            _append_text(self.cmd_map[str(code)[1:]], trg)
        # Check if command is a known function name (e.g. "log")
        elif name in FUNCTION_NAMES:
            sx = etree.Element("span")
            sx.attrib["class"] = "tex-math-function"
            sx.text = str(name)
            trg.append(sx)
            self._parse(args, trg)
        # Handle fractions
        elif name == "frac":
            self._parse_fraction(args, trg)
        # Give up, but preserve element
        else:
            log.warn("Unknown TeX-math command: {}".format(str(code)))
            self._append_unparsed(code, trg)

    def _parse_fraction(self, args, trg):
        if len(args) != 2:
            log.warn(
                "Couldn't parse \\frac: got {} arguments, expected {}".format(
                    len(args), 2
                )
            )
            self._append_unparsed(code, trg)
        else:
            # Represent numerator of fraction as superscript
            sx = etree.Element("sup")
            self._parse([args[0]], sx)
            trg.append(sx)
            # Unicode symbol for fraction slash
            _append_text("\u2044", trg)
            # Represent denominator of fraction as subscript
            sx = etree.Element("sub")
            self._parse([args[1]], sx)
            trg.append(sx)

    def _parse_text(self, code, trg):
        text = code.text
        # TexSoup doesn't parse curly brackets correctly, so we replace them
        # with a valid alternative command and repeat the parse
        if "\\{" in text or "\\}" in text:
            text = text.replace("\\{", "\\lbrace{}").replace("\\}", "\\rbrace{}")
            self._parse(TexSoup.TexSoup(text).expr.everything, trg)
            return
        # parse ^ and _ (won't get recognized as separate nodes by TexSoup)
        sxscript = False
        if "^" in text or "_" in text:
            buf = ""
            for char in text:
                if char == "^" or char == "_":
                    _append_text(buf, trg)
                    buf = ""
                    sxscript = "sup" if char == "^" else "sub"
                elif sxscript:
                    sx = etree.Element(sxscript)
                    sx.text = char
                    trg.append(sx)
                    sxscript = False
                else:
                    buf += char
            text = buf
        # Append as text
        _append_text(text, trg)
        return sxscript

    def _append_unparsed(self, code, trg):
        pre = etree.Element("span")
        pre.attrib["class"] = "tex-math-unparsed"
        pre.text = "\\{}{}".format(code.name, str(code.arguments))
        trg.append(pre)

    def etree_to_html(self, element):
        result = etree.Element("span")
        result.attrib["class"] = "tex-math"
        result.tail = element.tail  # Preserve tail
        self._parse(TexSoup.TexSoup(element.text).expr.everything, result)
        return result

    def to_html(self, element):
        """Converts a TeX math expression to HTML markup."""
        if isinstance(element, etree._Element):
            return self.etree_to_html(element)
        elif isinstance(element, str):
            value = self.etree_to_html(
                etree.fromstring("<span>{}</span>".format(element))
            )
            return etree.tostring(value)
        raise NotImplementedError(
            "Cannot convert elements of type {}".format(type(element))
        )

    def to_unicode(self, element):
        """Converts a TeX math expression to a Unicode string.

        This will perform the same conversions as `to_html()`, but strip out the
        HTML tags afterwards.
        """
        element = self.to_html(element)
        return etree.tostring(element, encoding="unicode", method="text")
