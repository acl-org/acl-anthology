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
from acl_anthology.text import MarkupText
from acl_anthology.utils.logging import setup_rich_logging

from markdown_it import MarkdownIt

setup_rich_logging()

md = (MarkdownIt("commonmark", {'breaks': False, 'html': True, 'linkify': True, 'typographer': True})
        .disable("code").disable("fence").disable("heading").disable("hr").disable("lheading").disable("list")
        .disable("reference").disable("entity").disable("image"))
"""Markdown processor. (OpenReview follows the CommonMark specification but does not support images or inline HTML.)"""

anthology = Anthology.from_within_repo()

i = 0

for paper in anthology.papers():
    if paper.abstract is not None:
        text = paper.abstract.as_xml()

        # strip out latex so Markdown parser doesn't treat _ as italics etc.
        maths = re.findall(r'<tex-math>.+?</tex-math>', text)
        protected_text = re.sub(r'<tex-math>.+?</tex-math>', '<tex-math></tex-math>', text)

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
