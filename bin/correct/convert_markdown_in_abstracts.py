import warnings
import logging as log
from docopt import docopt
import re
from typing import Optional, Tuple
from lxml import etree

from acl_anthology import Anthology
from acl_anthology.collections import Paper
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.people import NameSpecification, Name
from acl_anthology.text import MarkupText, to_markuptext
from acl_anthology.utils.logging import setup_rich_logging

from markdown_it import MarkdownIt

setup_rich_logging()

md = (MarkdownIt("commonmark", {'breaks': False, 'html': True, 'linkify': True, 'typographer': True})
        .enable(["linkify", "smartquotes"]) # don't enable "replacements" as this overcorrects "(c)" to "©" etc.
        .disable("code").disable("fence").disable("heading").disable("hr").disable("lheading").disable("list")
        .disable("reference").disable("entity").disable("image"))
"""Markdown processor. (OpenReview follows the CommonMark specification but does not support images or inline HTML.)"""

assert md.linkify
md.linkify.set({"fuzzy_link": False, "fuzzy_email": False, "fuzzy_ip": False})


def process_md_in_xml(text: str) -> str:
    # strip out latex so Markdown parser doesn't treat _ as italics etc.
    maths = re.findall(r'<tex-math>.+?</tex-math>', text)
    protected_text = re.sub(r'<tex-math>.+?</tex-math>', '<tex-math></tex-math>', text)
    # linkification doesn't recognize <url> so convert temporarily to <a>
    protected_text = re.sub(r'<url>([^<]+)</url>', r'<a href="\1">\1</a>', protected_text)

    # (not really Markdown but) process LaTeX-style quotes
    protected_text = protected_text.replace('``', '“').replace("''", '”')
    protected_text = re.sub(r"(?<!\w)`(.+?)'(?!\w)", r'‘\1’', protected_text)

    # Markdown -> HTML
    html = md.render(protected_text).strip()
    

    if html.startswith('<p>'):
        html = html[3:]
    if html.endswith('</p>'):
        html = html[:-4]
    html = html.replace('&quot;', '"').replace('&amp;', '&')
    html = html.replace('<strong>', '<b>').replace('</strong>', '</b>')
    html = html.replace('<em>', '<i>').replace('</em>', '</i>')
    html = re.sub(r'</p>\s*<p>', '<par/>', html)
    html = re.sub(r'<a href="([^"]+)">\1</a>', lambda m: "<url>" + m.group(1) + "</url>", html)

    # restore LaTeX
    html = re.sub(r'<tex-math></tex-math>', lambda m: maths.pop(0), html)

    return html


test_in1 = "The ``**code** and __data__'' are 'available' at the authors' github.com repo, https://github.com/Junjie-Ye/RoTBench."
test_out1 = process_md_in_xml(test_in1)
assert test_out1=="The “<b>code</b> and <b>data</b>” are ‘available’ at the authors’ github.com repo, <url>https://github.com/Junjie-Ye/RoTBench</url>.", test_out1

test_in2 = "Given a context-free grammar <tex-math>G</tex-math> and a sentence <tex-math>S</tex-math>, find and parse <tex-math>S'</tex-math> – the largest subset of words of <tex-math>S</tex-math>, such that <tex-math>S' \\in L(G)</tex-math>."
test_out2 = process_md_in_xml(test_in2)
assert test_out2=="Given a context-free grammar <tex-math>G</tex-math> and a sentence <tex-math>S</tex-math>, find and parse <tex-math>S'</tex-math> – the largest subset of words of <tex-math>S</tex-math>, such that <tex-math>S' \\in L(G)</tex-math>.", test_out2

anthology = Anthology.from_within_repo()


i = 0

for paper in anthology.papers():
    if paper.abstract is not None:
        text = paper.abstract.as_xml()

        html = process_md_in_xml(text)

        if html!=text and 'A*esque' not in text:
            try:
                paper.abstract = etree.fromstring("<abstract>" + html + "</abstract>")
                i += 1
            except etree.XMLSyntaxError as e:
                log.error(str(e))
                log.info(html)
    if i>=50:
        break

anthology.save_all()
