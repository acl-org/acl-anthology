#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Matt Post <post@cs.jhu.edu>
# Copyright 2019 David Wei Chiang <dchiang@nd.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Used to merge in missing information to many papers in commit 24ab9efd2ec05b9dcc80337695e5b33219aab679.
(See issue #173).

Author: David Chiang
"""

import logging
import difflib
import lxml.etree as etree
import copy

unique_attributes = {'id'}
recurse_elements = {'volume', 'paper'}
exclude_elements = {'paper'} # papers are usually removed for a reason; don't put them back

def opentag(node):
    copy = etree.Element(node.tag)
    copy.text = "\n"
    for a, v in sorted(node.attrib.items()):
        if a in unique_attributes:
            copy.attrib[a] = v
    s = etree.tostring(copy, encoding=str)
    return s.splitlines()[0]

def merge(atree, btree):
    def visit(anode, bnode):

        if anode.tag not in recurse_elements and bnode.tag not in recurse_elements: return
        
        achildren = sorted(anode, key=opentag)
        bchildren = sorted(bnode, key=opentag)

        indent = anode.text or ""
        after = anode[-1].tail or ""
        assert indent.strip() == after.strip() == ""

        for op, ai, aj, bi, bj in difflib.SequenceMatcher(a=list(map(opentag, achildren)), b=list(map(opentag, bchildren))).get_opcodes():
            if op in ['insert', 'replace']:
                for bchild in bchildren[bi:bj]:
                    if bchild.tag in exclude_elements:
                        logging.info("don't insert {}:<{}>".format(bchild.sourceline, bchild.tag))
                        continue
                    # hacky exception: papers shouldn't have editors
                    if bchild.tag == 'editor' and bchild.getparent().find('bibtype').text in ['inproceedings', 'incollection', 'article']:
                        logging.info("don't insert {}:<{}>".format(bchild.sourceline, bchild.tag))
                        continue
                        
                    logging.info('insert {}:{}'.format(bchild.sourceline, etree.tostring(bchild, encoding=str, with_tail=False)))
                    anode[-1].tail = indent
                    anode.append(copy.deepcopy(bchild))
                    anode[-1].tail = after
            elif op == 'equal':
                for achild, bchild in zip(achildren[ai:aj], bchildren[bi:bj]):
                    visit(achild, bchild)
    
    aroot = atree.getroot()
    broot = btree.getroot()
    visit(aroot, broot)

if __name__ == "__main__":
    import sys
    import argparse
    ap = argparse.ArgumentParser(description='Merge two XML files.')
    ap.add_argument('afile', help="first XML file (fields in this file take priority")
    ap.add_argument('bfile', help="second XML file")
    ap.add_argument('-o', '--outfile', help="XML file to write (default stdout)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO)
    
    if args.outfile:
        outfile = open(args.outfile, "w")
    else:
        outfile = sys.stdout

    atree = etree.parse(args.afile)
    btree = etree.parse(args.bfile)
    
    merge(atree, btree)

    outfile.write(etree.tostring(atree, encoding='UTF-8', xml_declaration=True, with_tail=True).decode('utf8'))
    
