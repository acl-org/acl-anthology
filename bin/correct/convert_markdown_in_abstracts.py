#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Nathan Schneider (@nschneid)
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

"""
Iterates over papers in the database and performs cleanup on abstracts,
most notably converting from Markdown to XML markup, applying smart quotes,
and linkifying URLs.

Exits after 200 abstracts have been modified so the diff can be manually
reviewed in batches.
"""

import logging as log
import re
from lxml import etree

from acl_anthology import Anthology
from acl_anthology.utils.logging import setup_rich_logging

from markdown_it import MarkdownIt

setup_rich_logging()

md = (
    MarkdownIt(
        "commonmark",
        {"breaks": False, "html": True, "linkify": True, "typographer": True},
    )
    .enable(
        ["linkify", "smartquotes"]
    )  # don't enable "replacements" as this overcorrects "(c)" to "©" etc.
    .disable(
        [
            "code",
            "fence",
            "heading",
            "hr",
            "lheading",
            "list",
            "reference",
            "entity",
            "image",
        ]
    )
)
"""Markdown processor. (OpenReview follows the CommonMark specification but does not support images or inline HTML.)"""

assert md.linkify
md.linkify.set({"fuzzy_link": False, "fuzzy_email": False, "fuzzy_ip": False})


def process_md_in_xml(text: str) -> str:
    # strip out latex so Markdown parser doesn't treat _ as italics etc.
    maths = re.findall(r"<tex-math>.+?</tex-math>", text)
    protected_text = re.sub(r"<tex-math>.+?</tex-math>", "<tex-math></tex-math>", text)
    # linkification doesn't recognize <url> so convert temporarily to <a>
    protected_text = re.sub(r"<url>([^<]+)</url>", r'<a href="\1">\1</a>', protected_text)
    # CJK punctuation, regular punctuation + curly quotes: wrap in <span> so it doesn't end up in a linkified URL
    protected_text = re.sub(
        r"([。，！？；：）】》]|[.,!?;:\]\}]*[’”‘“]+|[\]\}][.,!?;:])", r"<span>\1</span>", protected_text
    )
    protected_text = protected_text.replace("O*NET", "O\\*NET").replace(
        "A*esque", "A\\*esque"
    )

    # (not really Markdown but) process LaTeX-style quotes
    protected_text = protected_text.replace("``", "“").replace("''", "”")
    # characters that occur in some old volumes
    protected_text = protected_text.replace("\u0091", "‘").replace("\u0092", "’")
    protected_text = protected_text.replace("\u0093", "“").replace("\u0094", "”")
    protected_text = re.sub(r"(?<!\w)`(.+?)'(?!\w)", r"‘\1’", protected_text)
    # unescape &lt; and &gt; if acting as Markdown delimiters of a URL
    protected_text = re.sub(r"&lt;(\S+\.\S+)&gt;", r"<\1>", protected_text)

    # Markdown -> HTML
    html = md.render(protected_text).strip()

    if html.startswith("<p>"):
        html = html[3:]
    if html.endswith("</p>"):
        html = html[:-4]
    html = html.replace("&quot;", '"').replace("&amp;", "&")
    html = html.replace("<strong>", "<b>").replace("</strong>", "</b>")
    html = html.replace("<em>", "<i>").replace("</em>", "</i>")
    html = re.sub(r"</p>\s*<p>", "<par/>", html)
    html = re.sub(  # linked text is URL + period. move period after
        r'(<a href="([^"]+)">\2)\.</a>', r"\1</a>.", html
    )
    for url in re.findall(r'<a href="([^"]+)"', html):
        if "%" in url:
            log.warning(f"URL with %-encoding: {url}")  # sometimes extra punctuation characters are gobbled up into the URL
    html = re.sub(
        r'<a href="([^"]+)">\1</a>', lambda m: "<url>" + m.group(1) + "</url>", html
    )
    html = re.sub(r"<span>(.+?)</span>", r"\1", html)

    # restore LaTeX
    html = re.sub(r"<tex-math></tex-math>", lambda m: maths.pop(0), html)

    return html


test_in1 = "The ``**code** and __data__'' are 'available' at the authors' github.com repo, https://github.com/Junjie-Ye/RoTBench."
test_out1 = process_md_in_xml(test_in1)
assert (
    test_out1
    == "The “<b>code</b> and <b>data</b>” are ‘available’ at the authors’ github.com repo, <url>https://github.com/Junjie-Ye/RoTBench</url>."
), test_out1

test_in2 = "Given a context-free grammar <tex-math>G</tex-math> and a sentence <tex-math>S</tex-math>, find and parse <tex-math>S'</tex-math> – the largest subset of words of <tex-math>S</tex-math>, such that <tex-math>S' \\in L(G)</tex-math>."
test_out2 = process_md_in_xml(test_in2)
assert (
    test_out2
    == "Given a context-free grammar <tex-math>G</tex-math> and a sentence <tex-math>S</tex-math>, find and parse <tex-math>S'</tex-math> – the largest subset of words of <tex-math>S</tex-math>, such that <tex-math>S' \\in L(G)</tex-math>."
), test_out2

test_in3 = "“本文将TicomR开放供研究使用,http://github.com/Tshor/TicomR。”"
test_out3 = process_md_in_xml(test_in3)
assert (
    test_out3
    == "“本文将TicomR开放供研究使用,<url>http://github.com/Tshor/TicomR</url>。”"
), test_out3

test_in4 = "Our data and code for O*NET and A*esque are available at https://github.com/sjtu-compling/llm-pragmatics.”"
test_out4 = process_md_in_xml(test_in4)
assert (
    test_out4
    == "Our data and code for O*NET and A*esque are available at <url>https://github.com/sjtu-compling/llm-pragmatics</url>.”"
), test_out4

test_in5 = "See code at &lt;https://github.com/sjtu-compling/llm-pragmatics&gt;."
test_out5 = process_md_in_xml(test_in5)
assert (
    test_out5 == "See code at <url>https://github.com/sjtu-compling/llm-pragmatics</url>."
), test_out5

test_in6 = "Our <b>code</b> and <sc>dataset</sc> are available at: https://github.com/David-Li0406/ToolPRMBench[More resources on LLM-as-a-judge are on the website: &lt;https://llm-as-a-judge.github.io&gt;]."
test_out6 = process_md_in_xml(test_in6)
assert (
    test_out6 == "Our <b>code</b> and <sc>dataset</sc> are available at: <url>https://github.com/David-Li0406/ToolPRMBench</url>[More resources on LLM-as-a-judge are on the website: <url>https://llm-as-a-judge.github.io</url>]."
), test_out6

test_in7 = "The collected papers are available in [link here](https://github.com/FairyFali/Graph4LLM-Survey)."
test_out7 = process_md_in_xml(test_in7)
assert (
    test_out7 == 'The collected papers are available in <a href="https://github.com/FairyFali/Graph4LLM-Survey">link here</a>.'
), test_out7


anthology = Anthology.from_within_repo()


i = 0

for paper in anthology.papers():
    if paper.abstract is not None:
        text = paper.abstract.as_xml()

        html = process_md_in_xml(text)

        if html != text:
            try:
                paper.abstract = etree.fromstring("<abstract>" + html + "</abstract>")
                i += 1
            except etree.XMLSyntaxError as e:
                log.error(str(e))
                log.info(html)
    if i >= 200:
        break

anthology.save_all()
