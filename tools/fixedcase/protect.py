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
from common import *

# recursive helper called by protect
# protect text of "node", including children, and tails of children
def protect_recurse(node, words):
    if node.tag == 'fixed-case':	# already protected
        newnode = copy.deepcopy(node)	# don't need to modify descendents
        newnode.tail = None		# tail will be protected by caller
        return newnode
    newnode = ET.Element(node.tag, node.attrib)
    
    def process(text):
        if text is None: return
        i = 0
        while i < len(text):
            for w in words:
                if text[i:].startswith(w) and not (i+len(w) < len(text) and text[i+len(w)].isalpha()):
                    for upper, chars in itertools.groupby(w, lambda c: c.isupper()):
                        if upper:
                            p = ET.Element('fixed-case')
                            p.text = ''.join(chars)
                            newnode.append(p)
                        else:
                            append_text(newnode, ''.join(chars))
                    i += len(w)
                    break
            else:
                append_text(newnode, text[i])
                i += 1

    process(node.text)
    for child in node:
        newnode.append(protect_recurse(child, words))
        process(child.tail)
    return newnode

def protect(node, words):
    newnode = protect_recurse(node, words)
    newnode.tail = node.tail		# tail of top level is not protected
    return newnode

if __name__ == "__main__":
    truelist = set()

    truelist_file = os.path.join(sys.path[0], 'truelist')
    for line in open(truelist_file):
        line = line.split('#')[0].strip()
        if line == "": continue
        truelist.add(line)

    infile, outfile = sys.argv[1:]

    tree = ET.parse(infile)
    if not tree.getroot().tail: tree.getroot().tail = '\n'

    for paper in tree.getroot().findall('paper'):
        for title in paper.xpath('./title|./booktitle'):
            titletext = tokenize(get_text(title))
            fixed = fixedcase_title(titletext, truelist=truelist, falselist=falselist)
            if any(fixed):
                print("old:", ET.tostring(title).decode('ascii').rstrip())
                words = [w for w, b in zip(titletext, fixed) if b]
                replace_node(title, protect(title, words))
                print("new:", ET.tostring(title).decode('ascii').rstrip())
    tree.write(outfile, encoding="UTF-8", xml_declaration=True)


