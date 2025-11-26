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

import pytest
from lxml import etree
from acl_anthology.text import MarkupText

test_cases_markup = (
    (  # Fixed-case
        "<fixed-case>A</fixed-case>dap<fixed-case>L</fixed-case>e<fixed-case>R</fixed-case>: Speeding up Inference by Adaptive Length Reduction",
        {
            "text": "AdapLeR: Speeding up Inference by Adaptive Length Reduction",
            "html": '<span class="acl-fixed-case">A</span>dap<span class="acl-fixed-case">L</span>e<span class="acl-fixed-case">R</span>: Speeding up Inference by Adaptive Length Reduction',
            "latex": "{A}dap{L}e{R}: Speeding up Inference by Adaptive Length Reduction",
        },
    ),
    (  # Fixed-case inside markup
        "<b><fixed-case>A</fixed-case>dap<fixed-case>L</fixed-case>e<fixed-case>R</fixed-case></b>: Speeding up Inference by Adaptive Length Reduction",
        {
            "text": "AdapLeR: Speeding up Inference by Adaptive Length Reduction",
            "html": '<b><span class="acl-fixed-case">A</span>dap<span class="acl-fixed-case">L</span>e<span class="acl-fixed-case">R</span></b>: Speeding up Inference by Adaptive Length Reduction',
            "latex": "\\textbf{{A}dap{L}e{R}}: Speeding up Inference by Adaptive Length Reduction",
        },
    ),
    (  # Markup <b>
        "<b>D</b>ynamic <b>S</b>chema <b>G</b>raph <b>F</b>usion <b>Net</b>work (<b>DSGFNet</b>)",
        {
            "text": "Dynamic Schema Graph Fusion Network (DSGFNet)",
            "html": "<b>D</b>ynamic <b>S</b>chema <b>G</b>raph <b>F</b>usion <b>Net</b>work (<b>DSGFNet</b>)",
            "latex": "\\textbf{D}ynamic \\textbf{S}chema \\textbf{G}raph \\textbf{F}usion \\textbf{Net}work (\\textbf{DSGFNet})",
        },
    ),
    (  # Markup <i>
        "selecting prompt templates <i>without labeled examples</i> and <i>without direct access to the model</i>.",
        {
            "text": "selecting prompt templates without labeled examples and without direct access to the model.",
            "html": "selecting prompt templates <i>without labeled examples</i> and <i>without direct access to the model</i>.",
            "latex": "selecting prompt templates \\textit{without labeled examples} and \\textit{without direct access to the model}.",
        },
    ),
    (  # Empty markup
        "We <b/>solve this<i/> problem",
        {
            "text": "We solve this problem",
            "html": "We <b></b>solve this<i></i> problem",
            "latex": "We \\textbf{}solve this\\textit{} problem",
        },
    ),
    (  # TeX-math expression
        "<tex-math>^{\\mathcal{E}}</tex-math>: a Vectorial Resource for Computing Conceptual Similarity",
        {
            "text": "ℰ: a Vectorial Resource for Computing Conceptual Similarity",
            "html": '<span class="tex-math"><sup>ℰ</sup></span>: a Vectorial Resource for Computing Conceptual Similarity',
            "latex": "$^{\\mathcal{E}}$: a Vectorial Resource for Computing Conceptual Similarity",
        },
    ),
    (  # URL
        "The source code will be available at <url>https://github.com/zhang-yu-wei/MTP-CLNN</url>.",
        {
            "text": "The source code will be available at https://github.com/zhang-yu-wei/MTP-CLNN.",
            "html": 'The source code will be available at <a href="https://github.com/zhang-yu-wei/MTP-CLNN" class="acl-markup-url">https://github.com/zhang-yu-wei/MTP-CLNN</a>.',
            "latex": "The source code will be available at \\url{https://github.com/zhang-yu-wei/MTP-CLNN}.",
        },
    ),
    (  # XML entity
        "Workshop on Topic A &amp; B",
        {
            "text": "Workshop on Topic A & B",
            "html": "Workshop on Topic A &amp; B",
            "latex": "Workshop on Topic A {\\&} B",
        },
    ),
    (  # Line breaks
        "Title with\n\n line breaks",
        {
            "text": "Title with line breaks",
            "html": "Title with line breaks",
            "latex": "Title with line breaks",
        },
    ),
    (
        "<span>Title with\n\n line breaks</span>",
        {
            "text": "Title with line breaks",
            "html": "<span>Title with line breaks</span>",
            "latex": "Title with line breaks",
        },
    ),
    (  # Nested tags
        "<fixed-case>U</fixed-case>pstream <fixed-case>M</fixed-case>itigation <fixed-case>I</fixed-case>s <i><fixed-case>N</fixed-case>ot</i> <fixed-case>A</fixed-case>ll <fixed-case>Y</fixed-case>ou <fixed-case>N</fixed-case>eed",
        {
            "text": "Upstream Mitigation Is Not All You Need",
            "html": '<span class="acl-fixed-case">U</span>pstream <span class="acl-fixed-case">M</span>itigation <span class="acl-fixed-case">I</span>s <i><span class="acl-fixed-case">N</span>ot</i> <span class="acl-fixed-case">A</span>ll <span class="acl-fixed-case">Y</span>ou <span class="acl-fixed-case">N</span>eed',
            "latex": "{U}pstream {M}itigation {I}s \\textit{{N}ot} {A}ll {Y}ou {N}eed",
        },
    ),
    (
        "<b>Con<i>trived</i></b> <fixed-case><b>Ex</b>AMP<i>L</i>e</fixed-case> of N<b>es<tex-math>_{te}</tex-math>d</b> markup",
        {
            "text": "Contrived ExAMPLe of Nested markup",
            "html": '<b>Con<i>trived</i></b> <span class="acl-fixed-case"><b>Ex</b>AMP<i>L</i>e</span> of N<b>es<span class="tex-math"><sub>te</sub></span>d</b> markup',
            "latex": "\\textbf{Con\\textit{trived}} {\\textbf{Ex}AMP\\textit{L}e} of N\\textbf{es$_{te}$d} markup",
        },
    ),
    (
        "<i>D<b>e<i>e<b>e<i>e<b>p</b></i></b></i></b></i>ly",
        {
            "text": "Deeeeply",
            "html": "<i>D<b>e<i>e<b>e<i>e<b>p</b></i></b></i></b></i>ly",
            "latex": "\\textit{D\\textbf{e\\textit{e\\textbf{e\\textit{e\\textbf{p}}}}}}ly",
        },
    ),
    (  # Apostrophe character gets turned into a regular, protected apostrophe
        "BERT’s and <fixed-case>BERT</fixed-case>’s Attention",
        {
            "text": "BERT’s and BERT’s Attention",
            "html": 'BERT’s and <span class="acl-fixed-case">BERT</span>’s Attention',
            "latex": "BERT{'}s and {BERT}{'}s Attention",
        },
    ),
    (  # Regular quotes get turned into LaTeX quotes (and left untouched otherwise)
        'This "very normal" assumption',
        {
            "text": 'This "very normal" assumption',
            "html": 'This "very normal" assumption',
            "latex": "This ``very normal'' assumption",
        },
    ),
    (
        'This "very <b>bold</b>" assumption',
        {
            "text": 'This "very bold" assumption',
            "html": 'This "very <b>bold</b>" assumption',
            "latex": "This ``very \\textbf{bold}'' assumption",
        },
    ),
    (  # Typographic quotes get turned into normal LaTeX quotes as well
        "This “very normal” assumption",
        {
            "text": "This “very normal” assumption",
            "html": "This “very normal” assumption",
            "latex": "This ``very normal'' assumption",
        },
    ),
    (
        "This “very <b>bold</b>” assumption",
        {
            "text": "This “very bold” assumption",
            "html": "This “very <b>bold</b>” assumption",
            "latex": "This ``very \\textbf{bold}'' assumption",
        },
    ),
    (  # Special characters should always be in braces for BibTeX export
        "Äöøéÿőßû–",
        {
            "text": "Äöøéÿőßû–",
            "html": "Äöøéÿőßû–",
            "latex": '{\\"A}{\\"o}{\\o}{\\\'e}{\\"y}{\\H{o}}{\\ss}{\\^u}{--}',
        },
    ),
    (
        "Hajič, Jan and Woźniak, Michał",
        {
            "text": "Hajič, Jan and Woźniak, Michał",
            "html": "Hajič, Jan and Woźniak, Michał",
            "latex": "Haji{\\v{c}}, Jan and Wo{\\'z}niak, Micha{\\l}",
        },
    ),
    (
        "Žabokrtský, Zdeněk and Ševčíková, Magda",
        {
            "text": "Žabokrtský, Zdeněk and Ševčíková, Magda",
            "html": "Žabokrtský, Zdeněk and Ševčíková, Magda",
            "latex": "{\\v{Z}}abokrtsk{\\'y}, Zden{\\v{e}}k and {\\v{S}}ev{\\v{c}}{\\'i}kov{\\'a}, Magda",
        },
    ),
    (
        "íìïîı ÍÌÏÎİ",
        {
            "text": "íìïîı ÍÌÏÎİ",
            "html": "íìïîı ÍÌÏÎİ",
            "latex": "{\\'i}{\\`i}{\\\"i}{\\^i}{\\i} {\\'I}{\\`I}{\\\"I}{\\^I}{\\.I}",
        },
    ),
    (
        "陳大文",
        {
            "text": "陳大文",
            "html": "陳大文",
            "latex": "陳大文",
        },
    ),
    (
        "",
        {
            "text": "",
            "html": "",
            "latex": "",
        },
    ),
)


@pytest.mark.parametrize("inp, out", test_cases_markup)
def test_markup_from_xml(inp, out):
    xml = f"<title>{inp}</title>"
    element = etree.fromstring(xml)
    markup = MarkupText.from_xml(element)
    assert markup.as_text() == out["text"]
    assert markup.as_html() == out["html"]
    assert markup.as_latex() == out["latex"]
    assert markup.as_xml() == inp
    if inp == "":
        assert etree.tostring(markup.to_xml("title"), encoding="unicode") == "<title/>"
    else:
        assert etree.tostring(markup.to_xml("title"), encoding="unicode") == xml
    assert markup.contains_markup == ("<" in out["html"])


def test_simple_string():
    text = "Some ASCII text without markup"
    markup = MarkupText.from_string(text)
    assert not markup.contains_markup
    assert markup.as_text() == text
    assert markup.as_html() == text
    assert markup.as_latex() == text
    assert markup.as_xml() == text
    assert (
        etree.tostring(markup.to_xml("span"), encoding="unicode")
        == f"<span>{text}</span>"
    )


test_cases_markup_from_latex = (
    ("", ""),
    (  # ~ becomes a non-breaking space  // TODO: do we want a regular space here?
        "~",
        "\xa0",
    ),
    (  # Convert \\ to newline
        "\\\\",
        "\n",
    ),
    (  # --note minor bug: \\ doesn't eat up the space following it
        "a\\\\ a",
        "a\n a",
    ),
    (  # Curly braces become <fixed-case>
        "{A}dap{L}e{R}: Speeding up Inference by Adaptive Length Reduction",
        "<fixed-case>A</fixed-case>dap<fixed-case>L</fixed-case>e<fixed-case>R</fixed-case>: Speeding up Inference by Adaptive Length Reduction",
    ),
    (  # \textbf becomes <b>
        "\\textbf{D}ynamic \\textbf{S}chema \\textbf{G}raph \\textbf{F}usion \\textbf{Net}work (\\textbf{DSGFNet})",
        "<b>D</b>ynamic <b>S</b>chema <b>G</b>raph <b>F</b>usion <b>Net</b>work (<b>DSGFNet</b>)",
    ),
    (  # \textit becomes <i>
        "selecting prompt templates \\textit{without labeled examples} and \\emph{without direct access to the model}.",
        "selecting prompt templates <i>without labeled examples</i> and <i>without direct access to the model</i>.",
    ),
    (  # Math expressions get turned into <tex-math>
        "$^{\\mathcal{E}}$: a Vectorial Resource for Computing Conceptual Similarity",
        "<tex-math>^{\\mathcal{E}}</tex-math>: a Vectorial Resource for Computing Conceptual Similarity",
    ),
    (  # \url becomes <url>
        "The source code will be available at \\url{https://github.com/zhang-yu-wei/MTP-CLNN}.",
        "The source code will be available at <url>https://github.com/zhang-yu-wei/MTP-CLNN</url>.",
    ),
    (  # \href currently only keeps the text, not the link
        "\\href{http://www.overleaf.com}{Overleaf}",
        "Overleaf",
    ),
    (  # Special characters do _not_ get <fixed-case> even when they’re in braces
        "Workshop on Topic A {\\&} B",
        "Workshop on Topic A &amp; B",
    ),
    (  # Nesting <fixed-case> and <i>
        "{U}pstream {M}itigation {I}s \\textit{{N}ot} {A}ll {Y}ou {N}eed",
        "<fixed-case>U</fixed-case>pstream <fixed-case>M</fixed-case>itigation <fixed-case>I</fixed-case>s <i><fixed-case>N</fixed-case>ot</i> <fixed-case>A</fixed-case>ll <fixed-case>Y</fixed-case>ou <fixed-case>N</fixed-case>eed",
    ),
    (  # Nesting tags in different ways
        "\\textbf{Con\\textit{trived}} {\\textbf{Ex}AMP\\textit{L}e} of N\\textbf{es$_{te}$d} markup",
        "<b>Con<i>trived</i></b> <b>Ex</b>AMP<i>L</i>e of N<b>es<tex-math>_{te}</tex-math>d</b> markup",
    ),
    (
        "\\textit{D\\textbf{e\\textit{e\\textbf{e\\textit{e\\textbf{p}}}}}}ly",
        "<i>D<b>e<i>e<b>e<i>e<b>p</b></i></b></i></b></i>ly",
    ),
    (  # Testing various special characters, again should _not_ get <fixed-case>
        '{\\"A}{\\"o}{\\o}{\\\'e}{\\"y}{\\H{o}}{\\ss}{\\^u}{--}',
        "Äöøéÿőßû–",
    ),
    (
        "Haji{\\v{c}}, Jan and Wo{\\'z}niak, Micha{\\l}",
        "Hajič, Jan and Woźniak, Michał",
    ),
    (
        "{\\v{Z}}abokrtsk{\\'y}, Zden{\\v{e}}k and {\\v{S}}ev{\\v{c}}{\\'i}kov{\\'a}, Magda",
        "Žabokrtský, Zdeněk and Ševčíková, Magda",
    ),
    (
        "{\\'i}{\\`i}{\\\"i}{\\^i}{\\i} {\\'I}{\\`I}{\\\"I}{\\^I}{\\.I}",
        "íìïîı ÍÌÏÎİ",
    ),
    (
        "\\'i\\`i\\\"i\\^i\\i~\\'I\\`I\\\"I\\^I\\.I",
        "íìïîı\xa0ÍÌÏÎİ",
    ),
    (
        '\\"\\i',
        "ï",
    ),
    (
        "\\textasciitilde{} \\sim",
        "~ ∼",
    ),
    (  # Testing various special characters that had explicitly defined regexes in the old latex_to_unicode.py
        "\\'e{\\'e}\\'{e}",
        "ééé",
    ),
    (
        "\\textcommabelow{S} \\textcommabelow t",
        "S\N{COMBINING COMMA BELOW} t\N{COMBINING COMMA BELOW}",
    ),
    (
        "\\dj\\DJ",
        "đĐ",
    ),
    (
        "\\hwithstroke\\Hwithstroke",
        "ħĦ",
    ),
    (
        "\\textquotesingle \\textquotedblleft \\textquotedblright \\textquoteleft \\textquoteright",
        "'“”‘’",
    ),
    (
        "\\$42",
        "$42",
    ),
    (  # LaTeX quotes should be turned into typographic quotes
        "``Double'' quotes ``within'' text and \\textbf{``markup''}",
        "“Double” quotes “within” text and <b>“markup”</b>",
    ),
    (
        "`Single' quotes `within' text and \\textbf{`markup'}",
        "‘Single’ quotes ‘within’ text and <b>‘markup’</b>",
    ),
    (  # Non-ASCII characters should remain unchanged
        "陳大文",
        "陳大文",
    ),
    (  # Simple math does not get wrapped in <tex-math>
        "A $4.9\\%$ increase",
        "A 4.9% increase",
    ),
    (  # Math with e.g. a command inside gets wrapped in <tex-math>
        "A $\\log 25$ increase",
        "A <tex-math>\\log 25</tex-math> increase",
    ),
    (  # ...but never in fixed-case
        "A {$\\log 25$} increase",
        "A <tex-math>\\log 25</tex-math> increase",
    ),
    (  # Unhandled TeX commands are converted by Latex2Text’s rules
        "An \\textsc{unhandled} command",
        "An unhandled command",
    ),
    (
        "\\newcommand{\\R}{\\mathbb{R}}",
        "",
    ),
    (  # A macro that pylatexenc doesn't know can't have its arguments parsed, so they end up as <fixed-case>
        "\\complicatedusermacro{bar}",
        "<fixed-case>bar</fixed-case>",
    ),
    (  # \cite gets turned into "(CITATION)"  // TODO: we could handle these differently
        "A citation \\cite[p.32]{doe-et-al-2024}",
        "A citation (CITATION)",
    ),
    (  # LaTeX comments get dropped
        "Some text    % a comment",
        "Some text    ",
    ),
    (  # LaTeX environments get dropped  // TODO: can Latex2Text’s defaults handle them?
        """\\begin{itemize}
             \\item I hope we don't have to handle this
           \\end{itemize}""",
        "",
    ),
)


@pytest.mark.parametrize("inp, out", test_cases_markup_from_latex)
def test_markup_from_latex(inp, out):
    markup = MarkupText.from_latex(inp)
    assert markup.as_xml() == out


test_cases_markup_from_latex_maybe = (
    ("", "", ""),
    (  # LaTeX comment or intended percentage sign?
        "This is a 20% increase",
        "This is a 20",
        "This is a 20% increase",
    ),
    (  # ... this should not be affected
        "A $4.9\\%$ increase",
        "A 4.9% increase",
        "A 4.9% increase",
    ),
    (  # Non-breaking space or actual tilde?
        "We have ~20 examples",
        "We have \xa020 examples",
        "We have ~20 examples",
    ),
    (
        "a few (~20)",
        "a few (\xa020)",
        "a few (~20)",
    ),
    (  # ... this should not be affected
        "We have 20~examples",
        "We have 20\xa0examples",
        "We have 20\xa0examples",
    ),
)


@pytest.mark.parametrize("inp, out1, out2", test_cases_markup_from_latex_maybe)
def test_markup_from_latex_maybe(inp, out1, out2):
    markup = MarkupText.from_latex(inp)
    assert markup.as_xml() == out1
    markup = MarkupText.from_latex_maybe(inp)
    assert markup.as_xml() == out2
