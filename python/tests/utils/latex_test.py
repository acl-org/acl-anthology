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

import unicodedata
import pytest
from acl_anthology.people.name import Name, NameSpecification
from acl_anthology.text import MarkupText
from acl_anthology.utils import latex


def test_latexenc_configuration_assumptions():
    """`latex_encode()` replaces calling `LATEXENC.unicode_to_latex()` with a
    single `str.translate()` pass, which is only equivalent because
    `LATEXENC` uses dict-only conversion rules together with the specific
    settings checked here (see the note on `LATEXENC` in `utils/latex.py`).
    If this test fails, `_build_fast_latex_table()`/`latex_encode()` need to
    be revisited -- they may silently produce incorrect BibTeX otherwise.
    """
    assert latex.LATEXENC.non_ascii_only is False
    assert latex.LATEXENC.unknown_char_policy == "keep"
    assert latex.LATEXENC.replacement_latex_protection == "braces-all"
    assert latex.LATEXENC.latex_string_class is str


def test_latex_encode_matches_reference_for_every_mapped_codepoint():
    """Exhaustively checks latex_encode()'s fast path against the reference
    `LATEXENC.unicode_to_latex()` for every codepoint it claims to handle."""
    for codepoint in latex.FAST_LATEX_TABLE:
        char = chr(codepoint)
        assert latex.latex_encode(char) == latex.LATEXENC.unicode_to_latex(char)


@pytest.mark.parametrize(
    "text",
    (
        "",
        "Plain ASCII text, with punctuation: (a, b) & c! 100%.",
        "Mixed café naïve façade 中文 русский",  # mapped + unmapped non-ASCII
        "\N{GRINNING FACE}",  # unmapped and outside the BMP-adjacent ranges
        "\t\n\r control whitespace",
        "e\N{COMBINING ACUTE ACCENT}",  # decomposed; NFC-normalizes to "é"
    ),
)
def test_latex_encode_matches_reference_for_arbitrary_text(text):
    assert latex.latex_encode(text) == latex.LATEXENC.unicode_to_latex(text)


def test_latex_encode_none_and_empty():
    assert latex.latex_encode(None) == ""
    assert latex.latex_encode("") == ""


def test_latex_encode_normalizes_nfc():
    decomposed = "e\N{COMBINING ACUTE ACCENT}"
    assert unicodedata.normalize("NFC", decomposed) != decomposed  # sanity check
    assert latex.latex_encode(decomposed) == latex.latex_encode("é")


# Tests helper function used during conversion of our XML markup to LaTeX.
# Straight quotation marks (") will have been converted to double apostrophes,
# usually in braces ({''}), by pylatexenc; the function tested here applies
# heuristics to turn them into appropriate opening/closing quotes with the
# braces removed.
test_cases_latex_convert_quotes = (
    ("{''}This is a quotation.{''}", "``This is a quotation.''"),
    ("''This is a quotation.''", "``This is a quotation.''"),
    ("This is a {''}quotation{''}.", "This is a ``quotation''."),
    ("Can you 'please' {'}convert{'} this?", "Can you `please' `convert' this?"),
    ("My name is ''陳大文''.", "My name is ``陳大文''."),
    ("This isn't a quotation.", "This isn't a quotation."),
    ("But ''\\textbf{this}'' is", "But ``\\textbf{this}'' is"),
    ("But {''}\\textbf{this}{''} is", "But ``\\textbf{this}'' is"),
)


@pytest.mark.parametrize("inp, out", test_cases_latex_convert_quotes)
def test_latex_convert_quotes(inp, out):
    assert latex.latex_convert_quotes(inp) == out


def test_namespecs_to_bibtex():
    ns1 = NameSpecification(Name("Tai Man", "Chan"))
    ns2 = NameSpecification(Name("John", "Doé"))
    assert latex.namespecs_to_bibtex([]) == ""
    assert latex.namespecs_to_bibtex([ns1]) == "Chan, Tai Man"
    assert (
        latex.namespecs_to_bibtex([ns1, ns2])
        == "Chan, Tai Man  and\n      Do{\\'e}, John"
    )


def test_has_unbalanced_braces():
    assert not latex.has_unbalanced_braces("asdf")
    assert not latex.has_unbalanced_braces("{}")
    assert not latex.has_unbalanced_braces("{foo} {bar {baz}}")
    assert latex.has_unbalanced_braces("}{")
    assert latex.has_unbalanced_braces("{}}")
    assert latex.has_unbalanced_braces("foo {bar {baz}")


def test_bibtex_convert_month():
    assert latex.bibtex_convert_month("January") == "jan"
    assert latex.bibtex_convert_month("SEPTEMBER") == "sep"
    assert latex.bibtex_convert_month("mar") == "mar"
    assert latex.bibtex_convert_month("aug") == "aug"
    assert latex.bibtex_convert_month("September--November") == 'sep # "--" # nov'
    assert latex.bibtex_convert_month("December 3") == 'dec # " 3"'
    assert latex.bibtex_convert_month("UNK") == '"unk"'


def test_make_bibtex_entry():
    bibtype, bibkey = "inproceedings", "my-entry"
    fields = [
        ("author", [NameSpecification(Name("John", "Doé"))]),
        ("editor", []),
        ("title", MarkupText.from_string("Thé Papér")),
        ("booktitle", MarkupText.from_string('My "Conference"')),
        ("address", "Montréal"),
        ("doi", "10.000.a_b_c"),
        ("publisher", ""),
        ("month", "February"),
        ("note", None),
        ("pages", "1–7"),
    ]
    expected = """@inproceedings{my-entry,
    author = "Do{\\'e}, John",
    title = "Th{\\'e} Pap{\\'e}r",
    booktitle = "My ``Conference''",
    address = "Montr{\\'e}al",
    doi = "10.000.a_b_c",
    month = feb,
    pages = "1--7"
}"""
    assert latex.make_bibtex_entry(bibtype, bibkey, fields) == expected


def test_make_bibtex_entry_malformed():
    with pytest.raises(TypeError):
        latex.make_bibtex_entry("", "", [("author", Name("John", "Doé"))])
    with pytest.raises(TypeError):
        latex.make_bibtex_entry("", "", [("author", [Name("John", "Doé")])])
    with pytest.raises(ValueError):
        latex.make_bibtex_entry("", "", [("title", "}{")])


@pytest.mark.integration
def test_latex_encode_matches_reference_on_full_corpus():
    """Cross-checks latex_encode()'s fast path against the reference
    `LATEXENC.unicode_to_latex()` for every string in data/xml/*.xml, not
    just the hand-picked cases above."""
    import os
    from lxml import etree
    from pathlib import Path

    datadir = (
        Path(os.path.dirname(os.path.realpath(__file__))) / ".." / ".." / ".." / "data"
    )
    texts = set()
    for xmlpath in sorted(datadir.glob("xml/*.xml")):
        tree = etree.parse(xmlpath)
        for element in tree.iter(
            "title",
            "abstract",
            "first",
            "last",
            "booktitle",
            "publisher",
            "address",
            "note",
        ):
            text = "".join(element.itertext())
            if text:
                texts.add(text)

    assert texts, "expected to find at least some text in data/xml/*.xml"
    mismatches = [
        text
        for text in texts
        if latex.latex_encode(text) != latex.LATEXENC.unicode_to_latex(text)
    ]
    assert not mismatches, (
        f"{len(mismatches)} strings mismatched, e.g. {mismatches[:3]!r}"
    )
