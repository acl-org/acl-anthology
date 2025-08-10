# Copyright 2023-2025 Marcel Bollmann <marcel@bollmann.me>
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

"""Functions implementing conversions to and from LaTeX/BibTeX formats."""

from __future__ import annotations

import re
from functools import lru_cache
from lxml import etree
from typing import cast, Optional, TypeAlias, TYPE_CHECKING

if TYPE_CHECKING:
    from ..people.name import NameSpecification
    from ..text import MarkupText

    SerializableAsBibTeX: TypeAlias = None | str | MarkupText | list[NameSpecification]
    """Any type that can be supplied to `make_bibtex_entry`."""

from .logging import get_logger
from .xml import append_text

from pylatexenc.latexencode import (
    UnicodeToLatexEncoder,
    UnicodeToLatexConversionRule,
    RULE_DICT,
)
from pylatexenc.latexwalker import (
    LatexWalker,
    LatexNode,
    LatexCharsNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexMathNode,
    LatexSpecialsNode,
    get_default_latex_context_db as get_default_latexwalker_context_db,
)
from pylatexenc.macrospec import MacroSpec, SpecialsSpec
from pylatexenc.latex2text import (
    LatexNodes2Text,
    MacroTextSpec,
    SpecialsTextSpec,
    get_default_latex_context_db as get_default_latex2text_context_db,
)

log = get_logger()

################################################################################
### UNICODE TO LATEX (BIBTEX)
################################################################################

LATEXENC = UnicodeToLatexEncoder(
    conversion_rules=[
        UnicodeToLatexConversionRule(
            RULE_DICT,
            {
                ord("‘"): "`",  # defaults to \textquoteleft
                ord("’"): "'",  # defaults to \textquoteright
                ord("“"): "``",  # defaults to \textquotedblleft
                ord("”"): "''",  # defaults to \textquotedblright
                ord("–"): "--",  # defaults to \textendash
                ord("—"): "---",  # defaults to \textemdash
                ord("í"): "\\'i",  # defaults to using dotless \i
                ord("ì"): "\\`i",
                ord("î"): "\\^i",
                ord("ï"): '\\"i',
            },
        ),
        "defaults",
    ],
    replacement_latex_protection="braces-all",
    unknown_char_policy="keep",
    unknown_char_warning=False,
)
"""A UnicodeToLatexEncoder instance intended for BibTeX generation."""

BIBTEX_FIELD_NEEDS_ENCODING = {"journal", "address", "publisher", "note"}
"""Any BibTeX field whose value should be LaTeX-encoded first."""

BIBTEX_MONTHS = {
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
"""A mapping of month names to BibTeX macros."""

RE_OPENING_QUOTE_DOUBLE = re.compile(
    r"""
     (\A|(?<=\s))    # must be start of the string or come after whitespace
     ({``}|{''}|'')  # match double apostrophe, optionally in braces
     (?!}|\s)        # must not come before whitespace or closing brace }
     """,
    re.X,
)
RE_OPENING_QUOTE_SINGLE = re.compile(
    r"""
     (\A|(?<=\s))  # must be start of the string or come after whitespace
     ({`}|{'}|')   # match single apostrophe, optionally in braces
     (?!'|}|\s)    # must not come before whitespace, closing brace, or another apostrophe
     """,
    re.X,
)
RE_CLOSING_QUOTE_DOUBLE = re.compile(
    r"""
     (?<!\\)       # must not come after backslash
     {''}          # match double apostrophe in braces
     (?=\W|\Z)     # must be end of the string or come before a non-word character
     """,
    re.X,
)
RE_CLOSING_QUOTE_SINGLE = re.compile(
    r"""
     (?<!\\)       # must not come after backslash
     {'}           # match single apostrophe in braces
     (?=\W|\Z)     # must be end of the string or come before a non-word character
     """,
    re.X,
)

RE_HYPHENS_BETWEEN_NUMBERS = re.compile(r"(?<=[0-9])(-|–|—)(?=[0-9])")


def bibtex_convert_month(spec: str) -> str:
    """Converts a month string to BibTeX macros.

    Arguments:
        spec: A month specification, as stored in the metadata.

    Returns:
        A BibTeX macro corresponding to the month specification, if possible. If the string contains digits or is otherwise not parseable, it is returned unchanged with quotes around it.
    """
    text = spec.lower()
    if text in BIBTEX_MONTHS:  # most common case; map e.g. march -> mar
        return BIBTEX_MONTHS[text]
    if text in BIBTEX_MONTHS.values():  # already a month spec
        return text
    # Find embedded month strings
    text = f'"{text}"'
    for month, macro in BIBTEX_MONTHS.items():
        if month in text:
            text = text.replace(month, f'" # {macro} # "')
            text = " # ".join(filter(lambda k: k != '""', text.split(" # ")))
    return text


def has_unbalanced_braces(string: str) -> bool:
    """Checks if a string has unbalanced curly braces."""
    c = 0
    for char in string:
        if char == "{":
            c += 1
        elif char == "}":
            c -= 1
        if c < 0:
            return True
    return c != 0


@lru_cache
def latex_encode(text: Optional[str]) -> str:
    """
    Arguments:
        text: A string that does *not* contain any LaTeX commands.

    Returns:
        The input string encoded for use in LaTeX/BibTeX.
    """
    if text is None:
        return ""
    text = cast(str, LATEXENC.unicode_to_latex(text))
    return text


def latex_convert_quotes(text: str) -> str:
    """
    Arguments:
        text: An arbitrary string.

    Returns:
        The input string with LaTeX quotes converted into proper opening and closing quotes, removing braces around them, if necessary.

    Note:
        This is called during the conversion from our XML markup to LaTeX. Straight quotation marks (`"`) will have been converted to double apostrophes, usually in braces (`{''}`), by pylatexenc; this function applies regexes to turn them into appropriate opening/closing quotes with the braces removed.

    Examples:
        >>> latex_convert_quotes("This {''}great{''} example")
        "This ``great'' example"
    """
    text = RE_OPENING_QUOTE_DOUBLE.sub("``", text)
    text = RE_OPENING_QUOTE_SINGLE.sub("`", text)
    text = RE_CLOSING_QUOTE_DOUBLE.sub("''", text)
    text = RE_CLOSING_QUOTE_SINGLE.sub("'", text)
    return text


def make_bibtex_entry(
    bibtype: str, bibkey: str, fields: list[tuple[str, SerializableAsBibTeX]]
) -> str:
    """Turn a list of field/value pairs into a BibTeX entry.

    Values will be LaTeX-formatted if necessary, and can also be empty, in which case they are automatically omitted.

    Arguments:
        bibtype: The BibTeX type for the entry.
        bibkey: The BibTeX key for the entry.
        fields: A list of tuples of the form (key, value) specifying the fields to include in the entry.

    Returns:
        A fully formatted BibTeX entry.
    """
    from ..people.name import NameSpecification
    from ..text import MarkupText

    lines = [f"@{bibtype}{{{bibkey},"]
    for key, value in fields:
        if not value:
            continue
        if isinstance(value, MarkupText):
            value = value.as_latex()
        elif isinstance(value, list) and isinstance(value[0], NameSpecification):
            value = namespecs_to_bibtex(value)
        elif isinstance(value, str):
            if key in BIBTEX_FIELD_NEEDS_ENCODING:
                value = latex_encode(value)
            elif key == "month":
                value = bibtex_convert_month(value)
            elif key == "pages":
                value = RE_HYPHENS_BETWEEN_NUMBERS.sub("--", value)
        else:
            raise TypeError(f"Unsupported type for BibTeX field: {type(value)}")
        if has_unbalanced_braces(value):
            raise ValueError(f"BibTeX field '{key}' has unbalanced braces: {value}")

        # Quote (if necessary) and append
        if key == "month":
            quoted = value
        else:
            # Make sure not to use "" to quote values when they contain "
            quoted = f'"{value}"' if '"' not in value else f"{{{value}}}"
        lines.append(f"    {key} = {quoted},")
    lines[-1] = lines[-1][:-1]  # cut off last comma
    lines.append("}")
    return "\n".join(lines)


def namespecs_to_bibtex(namespecs: list[NameSpecification]) -> str:
    """Convert a list of NameSpecifications to a BibTeX-formatted entry.

    Arguments:
        namespecs: A list of names to be included in the BibTeX entry.

    Returns:
        A BibTeX-formatted string representing the given names.
    """
    return "  and\n      ".join(spec.name.as_bibtex() for spec in namespecs)


################################################################################
### LATEX TO UNICODE/XML
################################################################################

# The logic implemented here is largely based on our old
# `bin/latex_to_unicode.py` which was mainly authored by David Chiang.

LATEX_MACRO_TO_XMLTAG = {
    "emph": "i",
    "em": "i",
    "textit": "i",
    "it": "i",
    "textsl": "i",
    "sl": "i",
    "textbf": "b",
    "bf": "b",
    "url": "url",
}
"""A mapping of LaTeX macros to Anthology XML tags."""

LATEX_CITE_MACROS = {"cite", "citep", "citet", "newcite", "citeauthor", "citeyear"}
"""A set of LaTeX macros that will be treated as citation macros."""

LW_CONTEXT = get_default_latexwalker_context_db()
LW_CONTEXT.add_context_category(
    "unhandled special characters",
    prepend=True,
    macros=[
        MacroSpec("textcommabelow", "{"),
    ],
    specials=[
        SpecialsSpec("`"),
        SpecialsSpec("'"),
    ],
)
LW_CONTEXT.add_context_category(
    "common macros",
    prepend=True,
    macros=[
        MacroSpec("href", "{{"),
    ],
)

L2T_CONTEXT = get_default_latex2text_context_db()
L2T_CONTEXT.add_context_category(
    "citations",
    prepend=True,
    macros=[
        MacroTextSpec(macro, simplify_repl=r"(CITATION)") for macro in LATEX_CITE_MACROS
    ],
)
L2T_CONTEXT.add_context_category(
    "unhandled special characters",
    prepend=True,
    macros=[
        MacroTextSpec("textcommabelow", simplify_repl="%s\N{COMBINING COMMA BELOW}"),
        MacroTextSpec("hwithstroke", simplify_repl="ħ"),
        MacroTextSpec("Hwithstroke", simplify_repl="Ħ"),
    ],
    specials=[
        SpecialsTextSpec("`", "‘"),
        SpecialsTextSpec("'", "’"),
    ],
)
L2T_CONTEXT.add_context_category(
    "common macros",
    prepend=True,
    macros=[
        # \href: drop the URL but keep the text – we could append the URL in a
        # <url> tag, but this cannot be done here, we would have to add this to
        # _parse_nodelist_to_element as another special case
        MacroTextSpec("href", simplify_repl=r"%(2)s")
    ],
)
LATEX_TO_TEXT = LatexNodes2Text(strict_latex_spaces=True, latex_context=L2T_CONTEXT)


def _is_trivial_math(node: LatexMathNode) -> bool:
    """Helper function to determine whether or not a LatexMathNode contains only 'trivial' content that doesn't require a <tex-math> node.

    Currently, a math node is considered 'trivial' if it only contains numbers, spaces, and a few allowed characters (e.g. commas, dots, percentage signs).
    """
    content = node.latex_verbatim().strip("$").replace(r"\%", "%")
    return all(c.isspace() or c.isdigit() or c in (".,@%~") for c in content)


def _should_wrap_in_fixed_case(node: LatexGroupNode) -> bool:
    """Helper function to determine whether or not a LatexGroupNode should produce a <fixed-case> tag."""
    if len(node.nodelist) == 0 or node.delimiters != ("{", "}"):
        return False
    if node.latex_verbatim().startswith("{\\"):
        # {\...} does *not* protect case
        return False
    if node.nodelist[0].isNodeType(LatexMathNode):
        # Don't mark {$...$}
        return False
    if node.nodelist[0].isNodeType(LatexSpecialsNode):
        # Don't mark {``}, {--}, etc.
        return False
    return True


def _parse_nodelist_to_element(
    nodelist: list[LatexNode],
    element: etree._Element,
    use_fixed_case: bool,
    in_macro: bool = False,
) -> None:
    """Parse a list of LaTeX nodes into an XML element using the Anthology markup format.

    Arguments:
        nodelist: The list of parsed LaTeX nodes.
        element: An XML element into which the parsed nodes will be added.
        use_fixed_case: Flag indicating whether <fixed-case> protection should be applied.
        in_macro: Flag indicating whether this function was called by recursing into a macro node. (Do not set this manually.)

    Returns:
        None; the XML element is modified in-place.
    """
    for node in nodelist:
        if node is None:
            continue  # pragma: no cover
        elif node.isNodeType(LatexCharsNode):
            # Plain text
            append_text(element, node.chars)
        elif node.isNodeType(LatexMacroNode):
            # LaTeX macro
            if (tag := LATEX_MACRO_TO_XMLTAG.get(node.macroname)) is not None:
                # This macro should get its own XML tag (e.g. \textbf -> <b>)
                subelem = etree.SubElement(element, tag)
                subnodes = node.nodeargd.argnlist
                _parse_nodelist_to_element(
                    subnodes, subelem, use_fixed_case, in_macro=True
                )
            elif node.macroname in LATEX_CITE_MACROS:
                # A citation command such as \cite{...}
                append_text(element, LATEX_TO_TEXT.macro_node_to_text(node))
            elif node.macroname == "\\":
                # Special case: explicit linebreak \\
                append_text(element, "\n")
            else:
                # This macro either represents a special characters, such as
                # \v{c} or \"I, or is some other macro we do not explicitly
                # handle; in both cases, we fall back on Latex2Text’s default
                # conversion, which can be influenced by L2T_CONTEXT
                append_text(element, LATEX_TO_TEXT.macro_node_to_text(node))
        elif node.isNodeType(LatexGroupNode):
            # Bracketed group, such as {...} or [...]
            if not in_macro and _should_wrap_in_fixed_case(node):
                # Protect this with <fixed-case>, then recurse
                subelem = etree.SubElement(element, "fixed-case")
                _parse_nodelist_to_element(node.nodelist, subelem, False)
            elif node.delimiters == ("{", "}"):
                # Just recurse
                _parse_nodelist_to_element(node.nodelist, element, use_fixed_case)
            else:
                # Skip [...] or <...> groups
                pass
        elif node.isNodeType(LatexMathNode):
            # Math node
            if _is_trivial_math(node):
                # Just append as text
                append_text(element, LATEX_TO_TEXT.math_node_to_text(node))
            else:
                # Keep verbatim, but wrap in <tex-math>
                subelem = etree.SubElement(element, "tex-math")
                subelem.text = node.latex_verbatim().strip("$")
        elif node.isNodeType(LatexSpecialsNode):
            # TODO: Is this always the correct way?
            append_text(element, LATEX_TO_TEXT.specials_node_to_text(node))
        else:
            # Comments or environments
            log.warning(f"Unhandled node type: {node.nodeType}")


def parse_latex_to_xml(
    latex_input: str, use_fixed_case: bool = True, use_heuristics: bool = False
) -> etree._Element:
    """Convert a string with LaTeX markup into the Anthology XML format.

    Arguments:
        latex_input: A string potentially including LaTeX markup.
        use_fixed_case: Flag indicating whether <fixed-case> protection should be applied.
        use_heuristics: If True, will apply some heuristics to determine if certain symbols should be interpreted as plain text rather than LaTeX; e.g., it will prevent percentage signs from being interpreted as LaTeX comments.  Set this to True when dealing with inputs that could either be plain text or LaTeX.

    Returns:
        An XML element representing the given LaTeX input in the Anthology XML format for markup strings.

    Note:
        This is a potentially lossy conversion, as the Anthology XML format only represents a small subset of LaTeX commands.  Unhandled commands will be dropped, but emit a warning in the logger.
    """
    if use_heuristics:
        # % is probably percent (not a comment delimiter)
        latex_input = re.sub(r"(?<!\\)%", r"\%", latex_input)

        # Use a heuristic to decide whether ~ means "approximately" or is a tie
        latex_input = re.sub(r"(?<=[ (])~(?=\d)", r"\\textasciitilde ", latex_input)
        latex_input = re.sub(r"^~(?=\d)", r"\\textasciitilde ", latex_input)

    element = etree.Element("root")
    walker = LatexWalker(latex_input, latex_context=LW_CONTEXT)
    nodelist, *_ = walker.get_latex_nodes()
    _parse_nodelist_to_element(nodelist, element, use_fixed_case)
    return element
