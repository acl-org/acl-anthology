# Marcel Bollmann <marcel@bollmann.me>, 2019

from lxml import etree
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape
import itertools as it
import logging
import re

from . import data


xml_escape_or_none = lambda t: None if t is None else xml_escape(t)


def stringify_children(node):
    """Returns the full content of a node, including tags.

    Used for nodes that can have mixed text and HTML elements (like <b> and <i>)."""
    return "".join(
        chunk
        for chunk in it.chain(
            (xml_escape_or_none(node.text),),
            it.chain(
                *(
                    (
                        etree.tostring(child, with_tail=False, encoding=str),
                        xml_escape_or_none(child.tail),
                    )
                    for child in node.getchildren()
                )
            ),
            (xml_escape_or_none(node.tail),),
        )
        if chunk
    ).strip()


def remove_extra_whitespace(text):
    return re.sub(" +", " ", text.replace("\n", "").strip())


def infer_attachment_url(filename):
    # If filename has a network location, it's interpreted as a complete URL
    if urlparse(filename).netloc:
        return filename
    # Otherwise, treat it as an internal filename
    return data.ATTACHMENT_URL.format(filename[0], filename[:3], filename)


class SeverityTracker(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level=level)
        self.highest = logging.NOTSET

    def emit(self, record):
        if record.levelno > self.highest:
            self.highest = record.levelno
