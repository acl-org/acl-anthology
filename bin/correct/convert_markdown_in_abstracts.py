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
        .disable("code").disable("fence").disable("heading").disable("hr").disable("lheading").disable("list")
        .disable("reference").disable("entity").disable("image"))
"""Markdown processor. (OpenReview follows the CommonMark specification but does not support images or inline HTML.)"""

def process_md_in_xml(text: str) -> str:
    # strip out latex so Markdown parser doesn't treat _ as italics etc.
    maths = re.findall(r'<tex-math>.+?</tex-math>', text)
    protected_text = re.sub(r'<tex-math>.+?</tex-math>', '<tex-math></tex-math>', text)

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




def test_abstract():
    text = "Since the rise of neural natural-language-to-code models (NL<tex-math>\\rightarrow</tex-math>Code) that can generate long expressions and statements rather than a single next-token, one of the major problems has been reliably evaluating their generated output. In this paper, we propose CodeBERTScore: an evaluation metric for code generation, which builds on BERTScore (Zhang et al., 2020). Instead of encoding only the generated tokens as in BERTScore, CodeBERTScore also encodes the natural language input preceding the generated code, thus modeling the consistency between the generated code and its given natural language context as well. We perform an extensive evaluation of CodeBERTScore across four programming languages. We find that CodeBERTScore achieves a higher correlation with human preference and with functional correctness than all existing metrics. That is, generated code that receives a higher score by CodeBERTScore is more likely to be preferred by humans, as well as to function correctly when executed. We release five language-specific pretrained models to use with our publicly available code. Our language-specific models have been downloaded more than **1,000,000** times from the Huggingface Hub. Our code and data are available at https://github.com/neulab/code-bert-score"
    out = process_md_in_xml(text)
    text2 = "Since the rise of neural natural-language-to-code models (NL<tex-math>\\rightarrow</tex-math>Code) that can generate long expressions and statements rather than a single next-token, one of the major problems has been reliably evaluating their generated output. In this paper, we propose CodeBERTScore: an evaluation metric for code generation, which builds on BERTScore (Zhang et al., 2020). Instead of encoding only the generated tokens as in BERTScore, CodeBERTScore also encodes the natural language input preceding the generated code, thus modeling the consistency between the generated code and its given natural language context as well. We perform an extensive evaluation of CodeBERTScore across four programming languages. We find that CodeBERTScore achieves a higher correlation with human preference and with functional correctness than all existing metrics. That is, generated code that receives a higher score by CodeBERTScore is more likely to be preferred by humans, as well as to function correctly when executed. We release five language-specific pretrained models to use with our publicly available code. Our language-specific models have been downloaded more than <b>1,000,000</b> times from the Huggingface Hub. Our code and data are available at https://github.com/neulab/code-bert-score"
    assert text2==out
    tree = etree.fromstring("<abstract>" + text2 + "</abstract>")
    print(etree.tostring(tree))
    mutext = to_markuptext(tree)
    print(mutext.as_xml())
    anthology = Anthology.from_within_repo()
    paper = anthology.get('2023.emnlp-main.859')
    print(paper.abstract.as_xml())
    xml = paper.abstract.to_xml("abstract")
    print(etree.tostring(xml))
    paper.abstract = mutext
    print(paper.abstract.as_xml())
    xml = paper.abstract.to_xml("abstract")
    print(etree.tostring(xml))
    anthology.save_all()
    anthology = Anthology.from_within_repo()
    paper = anthology.get('2023.emnlp-main.859')
    print(paper.abstract.as_xml())
    xml = paper.abstract.to_xml("abstract")
    print(etree.tostring(xml))
    assert False


test_abstract()

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
