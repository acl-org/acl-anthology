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
from acl_anthology.text import TexMath

test_cases_unicode = (
    (
        "<tex-math>K</tex-math>-Embeddings: Learning Conceptual Embeddings for Words using Context",
        "K-Embeddings: Learning Conceptual Embeddings for Words using Context",
    ),
    (
        "<tex-math>^{\\mathcal{E}}</tex-math>: a Vectorial Resource for Computing Conceptual Similarity",
        "ℰ: a Vectorial Resource for Computing Conceptual Similarity",
    ),
    (
        "<tex-math>\\sharp</tex-math>: An Enhancement Approach to Reference-based Evaluation Metrics for Open-domain Dialog Generation",
        "♯: An Enhancement Approach to Reference-based Evaluation Metrics for Open-domain Dialog Generation",
    ),
    ("<tex-math>k</tex-math>-arization of Synchronous ", "k-arization of Synchronous "),
    ("<tex-math>N</tex-math>-Gram Translation", "N-Gram Translation"),
    ("<tex-math>k</tex-math>-best ", "k-best "),
    (
        "<tex-math>n</tex-math>-grams – Investigating Abstraction and Domain Dependence",
        "n-grams – Investigating Abstraction and Domain Dependence",
    ),
    (
        "<tex-math>N</tex-math>-gram Fragment Sequence Based Unsupervised Domain-Specific Document Readability",
        "N-gram Fragment Sequence Based Unsupervised Domain-Specific Document Readability",
    ),
    ("<tex-math>n</tex-math>-grams", "n-grams"),
    ("<tex-math>O(M(n^2))</tex-math> Time", "O(M(n2)) Time"),
    ("<tex-math>L_0</tex-math>-norm", "L0-norm"),
    ("<tex-math>n</tex-math>-gram embedding", "n-gram embedding"),
    ("<tex-math>N</tex-math>-best List Re-ranking", "N-best List Re-ranking"),
    ("<tex-math>O(n^6)</tex-math> ", "O(n6) "),
    (
        "<tex-math>^{\\circ}</tex-math>: A Referring Expression Recognition Dataset in 360",
        "∘: A Referring Expression Recognition Dataset in 360",
    ),
    ("<tex-math>^{\\circ}</tex-math> Images", "∘ Images"),
    ("<tex-math>k</tex-math>", "k"),
    (
        "<tex-math>k</tex-math>-Fold Ensemble for Out-Of-Distribution Detection",
        "k-Fold Ensemble for Out-Of-Distribution Detection",
    ),
    ("<tex-math>Q^{2}</tex-math>: ", "Q2: "),
    ("<tex-math>l_{0}</tex-math>-norm-based Alignment", "l0-norm-based Alignment"),
    ("<tex-math>\\tau</tex-math> Maximization", "𝜏 Maximization"),
    (
        "<tex-math>\\ell_1</tex-math>-Norm Symmetric Nonnegative Matrix Factorization",
        "ℓ1-Norm Symmetric Nonnegative Matrix Factorization",
    ),
    (
        "<tex-math>{\\mathcal{P}^2}</tex-math>: A Plan-and-Pretrain Approach for Knowledge Graph-to-Text Generation",
        "𝒫2: A Plan-and-Pretrain Approach for Knowledge Graph-to-Text Generation",
    ),
    (
        "<tex-math>^2</tex-math> Learning: Actively reducing redundancies in Active Learning methods for Sequence Tagging and Machine Translation",
        "2 Learning: Actively reducing redundancies in Active Learning methods for Sequence Tagging and Machine Translation",
    ),
    ("<tex-math>\\ell_{1}</tex-math> Norm Optimisation", "ℓ1 Norm Optimisation"),
    (
        "<tex-math>S^3</tex-math> - Statistical Sandhi Splitting",
        "S3 - Statistical Sandhi Splitting",
    ),
    ("<tex-math>\\epsilon</tex-math>-extension Hidden ", "𝜖-extension Hidden "),
    (
        "<tex-math>\\varepsilon</tex-math>-Skip Discriminating-Reverse Parsing on Graph-Structured Stack",
        "𝜀-Skip Discriminating-Reverse Parsing on Graph-Structured Stack",
    ),
    (
        "<tex-math>F^2</tex-math> - New Technique for Recognition of User Emotional States in Spoken Dialogue Systems",
        "F2 - New Technique for Recognition of User Emotional States in Spoken Dialogue Systems",
    ),
    (
        "<tex-math>0(n^6)</tex-math> Recognition Algorithm for Mildly Context-Sensitive Languages",
        "0(n6) Recognition Algorithm for Mildly Context-Sensitive Languages",
    ),
    ("<tex-math>\\lambda</tex-math>-", "𝜆-"),
    ("<tex-math>\\leftrightarrow</tex-math> ", "↔ "),
    ("<tex-math>\\Phi</tex-math>", "𝛷"),
)

test_cases_html = (
    (
        "<tex-math>K</tex-math>-Embeddings: Learning Conceptual Embeddings for Words using Context",
        '<span class="tex-math">K</span>-Embeddings: Learning Conceptual Embeddings for Words using Context',
    ),
    (
        "<tex-math>^{\\mathcal{E}}</tex-math>: a Vectorial Resource for Computing Conceptual Similarity",
        '<span class="tex-math"><sup>ℰ</sup></span>: a Vectorial Resource for Computing Conceptual Similarity',
    ),
    (
        "<tex-math>\\sharp</tex-math>: An Enhancement Approach to Reference-based Evaluation Metrics for Open-domain Dialog Generation",
        '<span class="tex-math">♯</span>: An Enhancement Approach to Reference-based Evaluation Metrics for Open-domain Dialog Generation',
    ),
    (
        "<tex-math>k</tex-math>-arization of Synchronous ",
        '<span class="tex-math">k</span>-arization of Synchronous ',
    ),
    (
        "<tex-math>N</tex-math>-Gram Translation",
        '<span class="tex-math">N</span>-Gram Translation',
    ),
    ("<tex-math>k</tex-math>-best ", '<span class="tex-math">k</span>-best '),
    (
        "<tex-math>n</tex-math>-grams – Investigating Abstraction and Domain Dependence",
        '<span class="tex-math">n</span>-grams – Investigating Abstraction and Domain Dependence',
    ),
    (
        "<tex-math>N</tex-math>-gram Fragment Sequence Based Unsupervised Domain-Specific Document Readability",
        '<span class="tex-math">N</span>-gram Fragment Sequence Based Unsupervised Domain-Specific Document Readability',
    ),
    ("<tex-math>n</tex-math>-grams", '<span class="tex-math">n</span>-grams'),
    (
        "<tex-math>O(M(n^2))</tex-math> Time",
        '<span class="tex-math">O(M(n<sup>2</sup>))</span> Time',
    ),
    ("<tex-math>L_0</tex-math>-norm", '<span class="tex-math">L<sub>0</sub></span>-norm'),
    (
        "<tex-math>n</tex-math>-gram embedding",
        '<span class="tex-math">n</span>-gram embedding',
    ),
    (
        "<tex-math>N</tex-math>-best List Re-ranking",
        '<span class="tex-math">N</span>-best List Re-ranking',
    ),
    ("<tex-math>O(n^6)</tex-math> ", '<span class="tex-math">O(n<sup>6</sup>)</span> '),
    (
        "<tex-math>^{\\circ}</tex-math>: A Referring Expression Recognition Dataset in 360",
        '<span class="tex-math"><sup>∘</sup></span>: A Referring Expression Recognition Dataset in 360',
    ),
    (
        "<tex-math>^{\\circ}</tex-math> Images",
        '<span class="tex-math"><sup>∘</sup></span> Images',
    ),
    ("<tex-math>k</tex-math>", '<span class="tex-math">k</span>'),
    (
        "<tex-math>k</tex-math>-Fold Ensemble for Out-Of-Distribution Detection",
        '<span class="tex-math">k</span>-Fold Ensemble for Out-Of-Distribution Detection',
    ),
    ("<tex-math>Q^{2}</tex-math>: ", '<span class="tex-math">Q<sup>2</sup></span>: '),
    (
        "<tex-math>l_{0}</tex-math>-norm-based Alignment",
        '<span class="tex-math">l<sub>0</sub></span>-norm-based Alignment',
    ),
    (
        "<tex-math>\\tau</tex-math> Maximization",
        '<span class="tex-math">𝜏</span> Maximization',
    ),
    (
        "<tex-math>\\ell_1</tex-math>-Norm Symmetric Nonnegative Matrix Factorization",
        '<span class="tex-math">ℓ<sub>1</sub></span>-Norm Symmetric Nonnegative Matrix Factorization',
    ),
    (
        "<tex-math>{\\mathcal{P}^2}</tex-math>: A Plan-and-Pretrain Approach for Knowledge Graph-to-Text Generation",
        '<span class="tex-math">𝒫<sup>2</sup></span>: A Plan-and-Pretrain Approach for Knowledge Graph-to-Text Generation',
    ),
    (
        "<tex-math>^2</tex-math> Learning: Actively reducing redundancies in Active Learning methods for Sequence Tagging and Machine Translation",
        '<span class="tex-math"><sup>2</sup></span> Learning: Actively reducing redundancies in Active Learning methods for Sequence Tagging and Machine Translation',
    ),
    (
        "<tex-math>\\ell_{1}</tex-math> Norm Optimisation",
        '<span class="tex-math">ℓ<sub>1</sub></span> Norm Optimisation',
    ),
    (
        "<tex-math>S^3</tex-math> - Statistical Sandhi Splitting",
        '<span class="tex-math">S<sup>3</sup></span> - Statistical Sandhi Splitting',
    ),
    (
        "<tex-math>\\epsilon</tex-math>-extension Hidden ",
        '<span class="tex-math">𝜖</span>-extension Hidden ',
    ),
    (
        "<tex-math>\\varepsilon</tex-math>-Skip Discriminating-Reverse Parsing on Graph-Structured Stack",
        '<span class="tex-math">𝜀</span>-Skip Discriminating-Reverse Parsing on Graph-Structured Stack',
    ),
    (
        "<tex-math>F^2</tex-math> - New Technique for Recognition of User Emotional States in Spoken Dialogue Systems",
        '<span class="tex-math">F<sup>2</sup></span> - New Technique for Recognition of User Emotional States in Spoken Dialogue Systems',
    ),
    (
        "<tex-math>0(n^6)</tex-math> Recognition Algorithm for Mildly Context-Sensitive Languages",
        '<span class="tex-math">0(n<sup>6</sup>)</span> Recognition Algorithm for Mildly Context-Sensitive Languages',
    ),
    ("<tex-math>\\lambda</tex-math>-", '<span class="tex-math">𝜆</span>-'),
    ("<tex-math>\\leftrightarrow</tex-math> ", '<span class="tex-math">↔</span> '),
    ("<tex-math>\\Phi</tex-math>", '<span class="tex-math">𝛷</span>'),
    # Manually collected tests
    (
        "<tex-math>0(n^{\\tilde{\\rho}+1})</tex-math>",
        '<span class="tex-math">0(n<sup> ̃𝜌+1</sup>)</span>',
    ),
    (
        "<tex-math>\\{mt, src\\} \\rightarrow pe</tex-math>",
        '<span class="tex-math">{mt, src} → pe</span>',
    ),
    (
        "<tex-math>p(\\boldsymbol{y}|\\textrm{do}(\\boldsymbol{x}))</tex-math>",
        '<span class="tex-math">p(<strong>y</strong>|<span class="font-weight-normal">do</span>(<strong>x</strong>))</span>',
    ),
    ("<tex-math>{\\sim}3\\%</tex-math>", '<span class="tex-math">∼3%</span>'),
    (
        "<tex-math>O(\\log_2 n)</tex-math>",
        '<span class="tex-math">O(<span class="tex-math-function">log</span><sub>2</sub> n)</span>',
    ),
    (
        "<tex-math>\\mathbf{^2}</tex-math>",
        '<span class="tex-math"><strong><sup>2</sup></strong></span>',
    ),
    (
        "<tex-math>RoBERTa_{large}</tex-math>",
        '<span class="tex-math">RoBERTa<sub>large</sub></span>',
    ),
    (
        "<tex-math>RoBERTa_{\\rm large}</tex-math>",
        '<span class="tex-math">RoBERTa<sub> large</sub></span>',
    ),
    (
        "<tex-math>RoBERTa_{\\bf large}</tex-math>",
        '<span class="tex-math">RoBERTa<sub> large</sub></span>',
    ),
    ("<tex-math>\\ell_1</tex-math>", '<span class="tex-math">ℓ<sub>1</sub></span>'),
    (
        "<tex-math>n \\log_2 \\frac{m}{n} + o(m)</tex-math>",
        '<span class="tex-math">n <span class="tex-math-function">log</span><sub>2</sub> <sup>m</sup>⁄<sub>n</sub> + o(m)</span>',
    ),
    (
        "<tex-math>\textrm{Pr}(f_1^J/e^I_1)</tex-math>",
        '<span class="tex-math">\textrmPr(f<sub>1</sub><sup>J</sup>/e<sup>I</sup><sub>1</sub>)</span>',
    ),
    (
        "<tex-math>\\# \\$ \\% \\&amp; \\_ \\{ \\} \\| \\:</tex-math>",
        '<span class="tex-math"># $ % &amp; _ { } ‖  </span>',
    ),
    (
        "<tex-math>asd\\$asd</tex-math>",
        '<span class="tex-math">asd$asd</span>',
    ),
    (
        "<tex-math>2\\_3</tex-math>",
        '<span class="tex-math">2_3</span>',
    ),
    (
        "<tex-math>2_3</tex-math>",
        '<span class="tex-math">2<sub>3</sub></span>',
    ),
    (
        "<tex-math>foo_{\\textsc{bar}}</tex-math>",
        '<span class="tex-math">foo<sub><span style="font-variant: small-caps;">bar</span></sub></span>',
    ),
    (
        "<tex-math>foo^{\\texttt{bar}}</tex-math>",
        '<span class="tex-math">foo<sup><span class="text-monospace">bar</span></sup></span>',
    ),
)


@pytest.mark.parametrize("inp, out", test_cases_unicode)
def test_unicode(inp, out):
    element = etree.fromstring(f"<span>{inp}</span>")
    math_element = element.find(".//tex-math")
    actual_out = TexMath.to_unicode(math_element)
    assert actual_out == out


@pytest.mark.parametrize("inp, out", test_cases_html)
def test_html(inp, out):
    element = etree.fromstring(f"<span>{inp}</span>")
    math_element = element.find(".//tex-math")
    result = TexMath.to_html(math_element)
    actual_out = etree.tostring(result, encoding="unicode")
    assert actual_out == out
