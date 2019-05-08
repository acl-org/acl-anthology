#!/usr/bin/env python3

import lxml.etree as etree
import sys
import itertools
import copy
from common import *

tree = etree.parse(sys.argv[1])
if not tree.getroot().tail: tree.getroot().tail = '\n'

for paper in tree.getroot().findall('paper'):
    for old in paper.xpath("./title|./booktitle"):
        new = etree.Element(old.tag)
        if old.text: append_text(new, old.text)
        for child in old:
            if child.tag == 'fixed-case':
                assert len(child) == 0
                for upper, chars in itertools.groupby(child.text, lambda c: c.isupper()):
                    if upper:
                        newchild = etree.Element('fixed-case')
                        newchild.text = ''.join(chars)
                        new.append(newchild)
                    else:
                        append_text(new, ''.join(chars))
                if child.tail: append_text(new, child.tail)
            else:
                new.append(copy.deepcopy(child))
        new.tail = old.tail
        replace_node(old, new)

tree.write(sys.argv[2], xml_declaration=True, encoding="UTF-8")

    
