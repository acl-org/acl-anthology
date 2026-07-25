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

md = (MarkdownIt("commonmark", {'breaks': False, 'html': True, 'linkify': True, 'typographer': True})
        .disable("code").disable("fence").disable("heading").disable("hr").disable("lheading").disable("list")
        .disable("reference").disable("entity").disable("image"))
"""Markdown processor. (OpenReview follows the CommonMark specification but does not support images or inline HTML.)"""

anthology = Anthology.from_within_repo()

i = 0

for paper in anthology.papers():
    if paper.abstract is not None:
        text = paper.abstract.as_xml()
        #text = text.replace('<tex-math>', '<code type="tex-math">').replace('</tex-math>', '</code>')
        html = md.render(text).strip()
        if html.startswith('<p>'):
            html = html[3:]
        if html.endswith('</p>'):
            html = html[:-4]
        html = html.replace('&quot;', '"').replace('&amp;', '&')
        html = html.replace('<strong>', '<b>').replace('</strong>', '</b>')
        html = html.replace('<em>', '<i>').replace('</em>', '</i>')
        html = re.sub(r'</p>\s*<p>', '<par/>', html)
        if html!=text:
            try:
                paper.abstract = etree.fromstring("<abstract>" + html + "</abstract>")
                i += 1
            except etree.XMLSyntaxError as e:
                print(str(e))
                print(html)
    if i>=10:
        break

anthology.save_all()
