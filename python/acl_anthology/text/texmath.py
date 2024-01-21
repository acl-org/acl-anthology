# Copyright 2019-2024 Marcel Bollmann <marcel@bollmann.me>
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

import csv
import pkgutil
from attrs import define, field
from lxml import etree
from TexSoup import TexSoup
from TexSoup.data import TexCmd, TexText, TexGroup
from typing import Literal, Tuple, Union, overload

from ..utils.logging import get_logger

log = get_logger()


FUNCTION_NAMES = ("lim", "log")
TEX_TO_HTML: dict[str, Tuple[str, dict[str, str]]] = {
    "mathrm": ("span", {"class": "font-weight-normal"}),
    "textrm": ("span", {"class": "font-weight-normal"}),
    "text": ("span", {"class": "font-weight-normal"}),
    "mathbf": ("strong", {}),
    "textbf": ("strong", {}),
    "boldsymbol": ("strong", {}),
    "mathit": ("em", {}),
    "textit": ("em", {}),
    "emph": ("em", {}),
    "textsc": ("span", {"style": "font-variant: small-caps;"}),
    "texttt": ("span", {"class": "text-monospace"}),
    "textsubscript": ("sub", {}),
    "textsuperscript": ("sup", {}),
}
REMOVED_COMMANDS = ("bf", "rm", "it", "sc")


def _append_text(text: str, trg: etree._Element) -> None:
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


SxscriptStatus = Literal[False, "sub", "sup"]
TexEverything = list[Union[str, TexCmd, TexText, TexGroup]]


@define
class _TexMath:
    """Interpreter and converter for TeX inline math expressions.

    This class uses [TexSoup](https://github.com/alvinwan/TexSoup) to
    parse a TeX expression and converts it to valid HTML.  The
    conversion combines a small number of handwritten rules with a
    [mapping of LaTeX math mode commands to Unicode
    symbols](http://milde.users.sourceforge.net/LUCR/Math/).  Parts that
    cannot be interpreted using this simple method are preserved as raw
    LaTeX.
    """

    cmd_map: dict[str, str] = field(init=False, factory=dict)
    loaded: bool = field(init=False, default=False)

    def load_symbols(self) -> None:
        data = pkgutil.get_data("acl_anthology", "data/unimathsymbols.txt")
        if data is None:
            raise FileNotFoundError(
                "Resource data/unimathsymbols.txt not found in acl_anthology"
            )
        lines = data.decode("utf-8").split("\n")
        reader = csv.reader(lines, delimiter="^")
        for row in reader:
            if (not row) or row[0].startswith("#"):  # comment
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
        self.loaded = True

    def _parse(self, everything: TexEverything, trg: etree._Element) -> None:
        """Parses a list of TeX constituents into an lxml.etree._Element.

        Arguments:
            everything: An iterator over TeX constituents as provided by TexSoup
            trg: The lxml.etree._Element to parse the expression into

        The approach of iterating over the TeX constituents roughly follows
        <https://github.com/alvinwan/TexSoup/blob/master/examples/list_everything.py>.
        """
        sxscript: SxscriptStatus = (
            False  # Tracks whether we're in a subscript/superscript
        )
        for code in everything:
            if isinstance(code, TexCmd):
                # code is a TeX command
                self._parse_command(code, trg)
            elif isinstance(code, (str, TexText)):
                # code is text
                sxscript = self._parse_text(code, trg)
            elif isinstance(code, TexGroup):
                # If in subscript/superscript, wrap the entire element in respective tag
                if sxscript:
                    my_trg = etree.Element(sxscript)
                    self._parse(code.contents, my_trg)
                    trg.append(my_trg)
                    sxscript = False
                # Otherwise, just parse it normally
                else:
                    self._parse(code.contents, trg)
            else:
                log.error(f"TeX-math parser got unhandled element: {type(code)}")

    def _parse_command(self, code: TexCmd, trg: etree._Element) -> None:
        args = list(code.args)
        name = str(code.name)
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
            sx = etree.Element("span", {"class": "tex-math-function"})
            sx.text = str(name)
            trg.append(sx)
            self._parse(args, trg)
        # Handle fractions
        elif name == "frac":
            self._parse_fraction(args, trg)
        # Handle commands with simple HTML tag substitutions
        elif name in TEX_TO_HTML:
            elem_name, elem_attrib = TEX_TO_HTML[name]
            sx = etree.Element(elem_name, attrib=elem_attrib)
            self._parse(args, sx)
            trg.append(sx)
        # Known, but unsupported formatting tags that will just be removed
        elif name in REMOVED_COMMANDS and not args:
            pass
        # Give up, but preserve element
        else:
            log.warn(f"Unknown TeX-math command: {code}")
            self._append_unparsed(code, trg)

    def _parse_fraction(self, args: list[TexEverything], trg: etree._Element) -> None:
        if len(args) != 2:
            log.warn(f"Couldn't parse \\frac: got {len(args)} arguments, expected 2")
            self._append_unparsed(TexCmd("frac", args=args), trg)
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

    def _parse_text(self, code: str | TexText, trg: etree._Element) -> SxscriptStatus:
        text = str(code)
        # TexSoup doesn't parse any non-alpha command as a command. Ex: \$
        # However it does seperate them into their own text part. Ex: 'r\\&dd' -> ['r', '\\&', 'dd']
        # Therefore try to do command mapping replacement of all text beginning with \ and of length 2
        if len(text) == 2 and text[0] == "\\":
            text = self.cmd_map.get(text[1], text)
            _append_text(text, trg)
            return False
        # parse ^ and _ (won't get recognized as separate nodes by TexSoup)
        sxscript: SxscriptStatus = False
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

    def _append_unparsed(self, code: TexCmd, trg: etree._Element) -> None:
        pre = etree.Element("span", {"class": "tex-math-unparsed"})
        pre.text = f"\\{code.name}{code.args}"
        trg.append(pre)

    def etree_to_html(self, element: etree._Element) -> etree._Element:
        result = etree.Element("span", {"class": "tex-math"})
        result.tail = element.tail  # Preserve tail
        self._parse(TexSoup(element.text).expr.all, result)
        return result

    @overload
    def to_html(self, element: str) -> str:  # pragma: no cover
        ...

    @overload
    def to_html(self, element: etree._Element) -> etree._Element:  # pragma: no cover
        ...

    def to_html(self, element: str | etree._Element) -> str | etree._Element:
        """Converts a TeX math expression to HTML markup.

        Arguments:
            element: The element to convert to HTML markup.

        Returns:
            The HTML-converted markup; the return type of this function is identical to the type that is passed in (i.e., [str][] or [etree._Element][lxml.etree._Element]).
        """
        if not self.loaded:
            self.load_symbols()
        if isinstance(element, etree._Element):
            return self.etree_to_html(element)
        elif isinstance(element, str):
            value = self.etree_to_html(etree.fromstring(f"<span>{element}</span>"))
            return etree.tostring(value, encoding="unicode")
        raise NotImplementedError(f"Cannot convert elements of type {type(element)}")

    def to_unicode(self, element: etree._Element) -> str:
        """Converts a TeX math expression to a Unicode string.

        This will perform the same conversions as
        [to_html()][acl_anthology.text.texmath.TexMath.to_html], but
        strip out the HTML tags afterwards.

        Arguments:
            element: The element to convert.

        Returns:
            The converted string.
        """
        if not self.loaded:
            self.load_symbols()
        element = self.to_html(element)
        return etree.tostring(element, encoding="unicode", method="text")


TexMath = _TexMath()
