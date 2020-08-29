"""author_case.py

usage: author_case.py -o <outdir>

Try to correct titles that are written in mostly uppercase.
"""

import sys
import os.path
import glob
import lxml.etree as etree
import argparse
import logging
import re
from fixedcase.common import get_text


def titlecase(s):
    if s is None:
        return None
    ret = []
    first = True
    for word in re.split(r"([^A-Za-z'’])", s):
        if (
            first
            or word.lower()
            not in "and or nor but a an the as at by for in of on per to vs".split()
        ):
            if len(word) > 0:
                word = word[0].upper() + word[1:].lower()
        else:
            word = word.lower()
        ret.append(word)
        if any(c.isalpha() for c in word):
            first = False
        if word in [':', '(']:
            first = True

    ret = ''.join(ret)
    return ret


def replace_text(node, text):
    def visit(node, skip):
        nonlocal text
        if node.tag == 'fixed-case':
            skip = True
        if node.text:
            n = len(node.text)
            if not skip:
                node.text = text[:n]
            text = text[n:]
        for child in node:
            visit(child, skip)
            if child.tail:
                n = len(child.tail)
                if not skip:
                    child.tail = text[:n]
                text = text[n:]

    visit(node, False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    scriptdir = os.path.dirname(os.path.abspath(__file__))
    datadir = os.path.join(scriptdir, '..', 'data')

    ap = argparse.ArgumentParser(description="Correct titles.")
    ap.add_argument(
        "-o", "--outdir", metavar="dir", help="output directory", required=True
    )
    args = ap.parse_args()

    infiles = sorted(glob.glob(os.path.join(datadir, "xml", "*.xml")))

    os.makedirs(os.path.join(args.outdir, "data", "xml"), exist_ok=True)

    for infile in infiles:
        tree = etree.parse(infile)
        root = tree.getroot()
        if not root.tail:
            root.tail = "\n"
        for title in root.xpath(".//title|.//booktitle"):
            title_text = get_text(title)
            ratio = len([c for c in title_text if c == c.lower()]) / len(title_text)
            if ratio < 0.5:
                replace_text(title, titlecase(title_text))
        outfile = os.path.join(args.outdir, "data", "xml", os.path.basename(infile))
        tree.write(outfile, xml_declaration=True, encoding="UTF-8")
