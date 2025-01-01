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

from __future__ import annotations

import re
from functools import lru_cache
from typing import cast, Optional, TypeAlias, TYPE_CHECKING

if TYPE_CHECKING:
    from ..people.name import NameSpecification
    from ..text import MarkupText

    SerializableAsBibTeX: TypeAlias = None | str | MarkupText | list[NameSpecification]
    """Any type that can be supplied to `make_bibtex_entry`."""


from pylatexenc.latexencode import (
    UnicodeToLatexEncoder,
    UnicodeToLatexConversionRule,
    RULE_DICT,
)

LATEXENC = UnicodeToLatexEncoder(
    conversion_rules=[
        UnicodeToLatexConversionRule(
            RULE_DICT,
            {
                ord("’"): "'",  # defaults to \textquoteright
                ord("–"): "--",  # defaults to \textendash
                ord("—"): "---",  # defaults to \textemdash
            },
        ),
        "defaults",
    ],
    replacement_latex_protection="braces-all",
    unknown_char_policy="keep",
)

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

RE_OPENING_QUOTE_DOUBLE = re.compile(r"(?<!\\)({''}|'')\b")
RE_OPENING_QUOTE_SINGLE = re.compile(r"(?<!\\)({'}|')\b")
RE_CLOSING_QUOTE_DOUBLE = re.compile(r"(?<!\\){''}")
RE_CLOSING_QUOTE_SINGLE = re.compile(r"(?<!\\){'}")
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
