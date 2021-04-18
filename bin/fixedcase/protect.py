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
    if node.tag in ("fixed-case", "tex-math"):  # already protected text, or math
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
        recased = recased[len(get_text(protected_child)) :]
        newnode.append(protected_child)
        if child.tail:
            process(child.tail, recased)
            recased = recased[len(child.tail) :]

    return newnode


def protect(node):
    rawtext = get_text(node).strip()
    recased = None
    if rawtext.lower() in special_titles:
        recased = special_titles[rawtext.lower()]
    else:
        text = tokenize(rawtext)
        fixed = fixedcase_title(
            text,
            truelist=truelist,
            phrase_truelist=phrase_truelist,
            amodifiers=amodifiers,
            ndescriptors=ndescriptors,
        )
        if any(fixed):
            # Generate the recased string so we know where to look in the XML
            # to apply fixed-case
            recasedtoks = [(w if b else w.lower()) for w, b in zip(text, fixed)]
            recased = TreebankWordDetokenizer().detokenize(recasedtoks)
            # PTB (de)tokenizer doesn't think of hyphens as separate tokens,
            # so we need to manually detokenize them.
            # Assuming the only edits that need to be made are adding/deleting
            # spaces, the following will work:
            i = 0
            while i < len(rawtext):
                # scan rawtext from left to right and adjust recased by adding/removing
                # spaces until it matches
                t = rawtext[i]
                assert i < len(recased), ((i, t), rawtext, recased)
                c = recased[i]
                if t.isspace() and not c.isspace():  # may be ' ' or '\n'
                    # add space to recased
                    recased = recased[:i] + t + recased[i:]
                    i += 1
                elif c.isspace() and not t.isspace():
                    # remove space from recased
                    recased = recased[:i] + recased[i + 1 :]
                    # don't increment i
                elif t != c and t.isspace() and c.isspace():
                    recased = recased[:i] + t + recased[i + 1 :]
                    i += 1
                else:
                    assert t == c or t.lower() == c.lower(), (
                        (i, t, c),
                        rawtext,
                        recased,
                        text,
                    )
                    i += 1
            if len(recased) > len(rawtext):
                recased = recased[: len(rawtext)]
            assert rawtext.lower() == recased.lower(), (rawtext, recased)

    if recased:
        newnode = protect_recurse(node, recased)
        newnode.tail = node.tail  # tail of top level is not protected
        replace_node(node, newnode)


# Read in the truelist (list of words that should always be protected)
truelist, phrase_truelist, special_titles, amodifiers, ndescriptors = load_lists()

if __name__ == "__main__":
    infile, outfile = sys.argv[1:]

    tree = ET.parse(infile)
    if not tree.getroot().tail:
        tree.getroot().tail = "\n"
    for paper in tree.getroot().findall(".//paper"):
        for title in paper.xpath("./title|./booktitle"):
            protect(title)
    tree.write(outfile, encoding="UTF-8", xml_declaration=True)
