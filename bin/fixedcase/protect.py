#!/usr/bin/env python3

# protect.py <infile> <outfile>
# looks for file "truelist" in current dir

# cd data/xml
# for i in *xml ; do (cd ../../tools/fixedcase/ ; python3 ./protect.py ../../data/xml/$i /tmp/$i ; echo $i ); done > log


import lxml.etree as ET
import os
import sys
import copy
import itertools
import inspect

from collections import defaultdict

if __name__ == "__main__":
    from common import *
else:
    from .common import *

# recursive helper called by protect
# protect text of "node", including children, and tails of children
def protect_recurse(node, recased):
    if node.tag == "fixed-case":  # already protected
        newnode = copy.deepcopy(node)  # don't need to modify descendents
        newnode.tail = None  # tail will be protected by caller
        return newnode
    newnode = ET.Element(node.tag, node.attrib)

    def process(text, rc):
        i = 0
        for upper, chars in itertools.groupby(rc[: len(text)], lambda c: c.isupper()):
            charstr = "".join(chars)
            if upper:
                p = ET.Element("fixed-case")
                p.text = charstr
                newnode.append(p)
            else:
                append_text(newnode, text[i : i + len(charstr)])

            assert text[i : i + len(charstr)].lower() == charstr.lower(), (
                i,
                text,
                charstr,
            )
            i += len(charstr)

    if node.text:
        process(node.text, recased)
        recased = recased[len(node.text) :]
    for child in node:
        protected_child = protect_recurse(child, recased)
        recased = recased[len(protected_child.text) :]
        newnode.append(protected_child)
        if child.tail:
            process(child.tail, recased)
            recased = recased[len(child.tail) :]

    return newnode


def protect(node):
    rawtext = get_text(node).strip()
    text = tokenize(rawtext)
    fixed = fixedcase_title(
        text,
        truelist=truelist,
        phrase_truelist=phrase_truelist,
        amodifiers=amodifiers,
        ndescriptors=ndescriptors,
        falselist=falselist,
    )
    if any(fixed):
        # words = [w for w, b in zip(text, fixed) if b]
        recased = ''
        for w, b in zip(text, fixed):
            recased += w if b else w.lower()
            if len(rawtext) > len(recased) and rawtext[len(recased)] == ' ':
                recased += ' '
        assert rawtext.lower() == recased.lower(), (rawtext, recased)
        newnode = protect_recurse(node, recased)
        newnode.tail = node.tail  # tail of top level is not protected
        replace_node(node, newnode)


# Read in the truelist (list of words that should always be protected)
truelist = set()
phrase_truelist = defaultdict(set)
module_file = inspect.getfile(inspect.currentframe())
module_dir = os.path.dirname(os.path.abspath(module_file))
truelist_file = os.path.join(module_dir, "truelist")
for line in open(truelist_file):
    line = line.split("#")[0].strip()
    if line == "":
        continue
    assert not any(
        is_hyphen(c) for c in line
    ), f'Truelist entries should not contain hyphens: {line}'
    if ' ' not in line:
        truelist.add(line)
    else:
        toks = tuple(tokenize(line))
        phrase_truelist[len(toks)].add(toks)  # group phrases by number of tokens
phrase_truelist = sorted(
    phrase_truelist.items(), reverse=True
)  # bins sorted by phrase length
amodifiers = (
    'North',
    'South',
    'East',
    'West',
    'Northeast',
    'Northwest',
    'Southeast',
    'Southwest',
    'Central',
    'Northern',
    'Southern',
    'Eastern',
    'Western',
    'Northeastern',
    'Northwestern',
    'Southeastern',
    'Southwestern',
    'Modern',
    'Ancient',
)  # use subsequent word to determine fixed-case. will miss hyphenated modifiers (e.g. South-East)
ndescriptors = (
    'Bay',
    'Coast',
    'Gulf',
    'Island',
    'Isle',
    'Lake',
    'Republic',
    'University',
)  # use preceding word to determine fixed-case

if __name__ == "__main__":
    infile, outfile = sys.argv[1:]

    tree = ET.parse(infile)
    if not tree.getroot().tail:
        tree.getroot().tail = "\n"
    for paper in tree.getroot().findall(".//paper"):
        for title in paper.xpath("./title|./booktitle"):
            protect(title)
    tree.write(outfile, encoding="UTF-8", xml_declaration=True)
