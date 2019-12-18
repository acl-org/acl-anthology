#!/usr/bin/env python3

# protect_allcaps.py <infile> <outfile>
# looks for file "truelist" in current dir

# Simpler version of protect.py for titles written in all caps.

import lxml.etree as ET
import os
import sys
import copy
import itertools
import inspect


if __name__ == "__main__":
    from common import *
else:
    from .common import *


def protect(node):
    if node.tag == "fixed-case":  # already protected
        newnode = copy.deepcopy(node)  # don't need to modify descendents
        newnode.tail = None  # tail will be protected by caller
        return newnode
    newnode = ET.Element(node.tag, node.attrib)

    def process(text):
        if text is None:
            return
        tokens = list(re.split(r'([\s:.,?-])', text))
        for token in tokens:
            if token == token.upper() and token in truelist:
                print(token, file=sys.stderr)
                for upper, chars in itertools.groupby(truelist[token], str.isupper):
                    if upper:
                        p = ET.Element("fixed-case")
                        p.text = "".join(chars).upper()
                        newnode.append(p)
                    else:
                        append_text(newnode, "".join(chars).upper())
            else:
                append_text(newnode, token)

    process(node.text)
    for child in node:
        newnode.append(protect(child))
        process(child.tail)
    return newnode


# Read in the truelist (list of words that should always be protected)
truelist = {}
module_file = inspect.getfile(inspect.currentframe())
module_dir = os.path.dirname(os.path.abspath(module_file))
truelist_file = os.path.join(module_dir, "truelist")
for line in open(truelist_file):
    line = line.split("#")[0].strip()
    if line == "":
        continue
    truelist[line.upper()] = line

# The truelist does not contain any acronyms, because normally they
# are marked as fixed-case by virtue of being written in all caps. But
# here we need an explicit list.

for word in "ACL ATIS ATN BBN CCG CMU COLING GPSG MT NIST NLP SRI TIPSTER TREC".split():
    truelist[word.upper()] = word

if __name__ == "__main__":
    infile, outfile = sys.argv[1:]

    tree = ET.parse(infile)
    if not tree.getroot().tail:
        tree.getroot().tail = "\n"

    for paper in tree.getroot().xpath(".//paper"):
        for title in paper.xpath("./title|./booktitle"):
            newtitle = protect(title)
            newtitle.tail = title.tail
            replace_node(title, newtitle)
    tree.write(outfile, encoding="UTF-8", xml_declaration=True)
