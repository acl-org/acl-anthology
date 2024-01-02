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

import pytest
from lxml import etree
from acl_anthology.text import MarkupText

test_cases_markup = (
    (
        "<fixed-case>A</fixed-case>dap<fixed-case>L</fixed-case>e<fixed-case>R</fixed-case>: Speeding up Inference by Adaptive Length Reduction",
        {
            "text": "AdapLeR: Speeding up Inference by Adaptive Length Reduction",
            "html": '<span class="acl-fixed-case">A</span>dap<span class="acl-fixed-case">L</span>e<span class="acl-fixed-case">R</span>: Speeding up Inference by Adaptive Length Reduction',
            "latex": "{A}dap{L}e{R}: Speeding up Inference by Adaptive Length Reduction",
        },
    ),
    (
        "<b>D</b>ynamic <b>S</b>chema <b>G</b>raph <b>F</b>usion <b>Net</b>work (<b>DSGFNet</b>)",
        {
            "text": "Dynamic Schema Graph Fusion Network (DSGFNet)",
            "html": "<b>D</b>ynamic <b>S</b>chema <b>G</b>raph <b>F</b>usion <b>Net</b>work (<b>DSGFNet</b>)",
            "latex": "\\textbf{D}ynamic \\textbf{S}chema \\textbf{G}raph \\textbf{F}usion \\textbf{Net}work (\\textbf{DSGFNet})",
        },
    ),
    (
        "selecting prompt templates <i>without labeled examples</i> and <i>without direct access to the model</i>.",
        {
            "text": "selecting prompt templates without labeled examples and without direct access to the model.",
            "html": "selecting prompt templates <i>without labeled examples</i> and <i>without direct access to the model</i>.",
            "latex": "selecting prompt templates \\textit{without labeled examples} and \\textit{without direct access to the model}.",
        },
    ),
    (
        "<tex-math>^{\\mathcal{E}}</tex-math>: a Vectorial Resource for Computing Conceptual Similarity",
        {
            "text": "ℰ: a Vectorial Resource for Computing Conceptual Similarity",
            "html": '<span class="tex-math"><sup>ℰ</sup></span>: a Vectorial Resource for Computing Conceptual Similarity',
            "latex": "$^{\\mathcal{E}}$: a Vectorial Resource for Computing Conceptual Similarity",
        },
    ),
    (
        "The source code will be available at <url>https://github.com/zhang-yu-wei/MTP-CLNN</url>.",
        {
            "text": "The source code will be available at https://github.com/zhang-yu-wei/MTP-CLNN.",
            "html": 'The source code will be available at <a href="https://github.com/zhang-yu-wei/MTP-CLNN" class="acl-markup-url">https://github.com/zhang-yu-wei/MTP-CLNN</a>.',
            "latex": "The source code will be available at \\url{https://github.com/zhang-yu-wei/MTP-CLNN}.",
        },
    ),
    (
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
    (
        "Äöøéÿőßû–",
        {
            "text": "Äöøéÿőßû–",
            "html": "Äöøéÿőßû–",
            # this is what the modified latexcodec from the acl-anthology repo produces:
            # "latex": '{\\"A}{\\"o}{\\o}{\\\'e}{\\"y}{\\H{o}}{\\ss}{\\^u}{--}',
            "latex": '\\"A\\"o\\o \\\'e\\"y\\H o\\ss \\^u--',
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
)


@pytest.mark.parametrize("inp, out", test_cases_markup)
def test_markup(inp, out):
    xml = f"<title>{inp}</title>"
    element = etree.fromstring(xml)
    markup = MarkupText.from_xml(element)
    assert markup.as_text() == out["text"]
    assert markup.as_html() == out["html"]
    assert markup.as_latex() == out["latex"]
    assert etree.tostring(markup.to_xml("title"), encoding="unicode") == xml
    assert markup.contains_markup == (out["text"] != out["html"])


def test_simple_string():
    text = "Some ASCII text without markup"
    markup = MarkupText.from_string(text)
    assert not markup.contains_markup
    assert markup.as_text() == text
    assert markup.as_html() == text
    assert markup.as_latex() == text
    assert (
        etree.tostring(markup.to_xml("span"), encoding="unicode")
        == f"<span>{text}</span>"
    )
