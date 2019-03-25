#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
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

import difflib
import lxml.etree as etree
import operator
import copy

unique_attributes = {'id'}
elements = {'volume', 'paper', 'author', 'editor'}
oldcolor = '\033[91m\033[7m'
newcolor = '\033[92m\033[7m'
nocolor = '\033[0m'
max_length = 65 # information in left margin is 14 chars

def opentag(node):
    copy = etree.Element(node.tag)
    copy.text = "\n"
    for a, v in sorted(node.attrib.items()):
        if a in unique_attributes:
            copy.attrib[a] = v
    s = etree.tostring(copy, encoding=str)
    return s.splitlines()[0]

def tostring(node, max_length=None):
    node = copy.deepcopy(node)

    # Strip leading and trailing whitespace
    if node.text is not None:
        node.text = node.text.lstrip()
    if len(node) > 0:
        if node[-1].tail is not None:
            node[-1].tail = node[-1].tail.rstrip()
    else:
        if node.text is not None:
            node.text = node.text.rstrip()
    
    s = etree.tostring(node, encoding=str, with_tail=False)
    s = ' '.join(s.split())
    if max_length is not None:
        return s[:max_length]
    else:
        return s

def diff_strings(a, b, aloc, bloc, max_length):
    sm = difflib.SequenceMatcher(a=a, b=b)
    ops = sm.get_opcodes()

    min_context = 15
    def visit(ai, aj, bi, bj):
        if aj-ai == bj-bi == 0: return

        # Widen the windows by min_context
        aa = max(0, ai-min_context)
        az = min(len(a), aj+min_context)
        ba = max(0, bi-min_context)
        bz = min(len(b), bj+min_context)
        
        if az-aa <= max_length and bz-ba <= max_length:
            # Widen more
            aa = max(0, min(ai - (max_length-(aj-ai))//2, len(a)-max_length))
            az = aa+max_length
            ba = max(0, min(bi - (max_length-(bj-bi))//2, len(b)-max_length))
            bz = ba+max_length
            
            # Print the differences all together
            print('{:5d} {:5s} - '.format(aloc, ''), end='')
            for op, ak, al, bk, bl in sm.get_opcodes():
                if ai == ak and bi == bk: # first piece, print left context
                    print(a[aa:ai], end='')
                if ai <= ak <= al <= aj:
                    if op == 'equal':
                        print(a[ak:al], end='')
                    else:
                        print(oldcolor+a[ak:al]+nocolor, end='')
                if al == aj and bl == bj: # last piece, print right context
                    print(a[aj:az], end='')
            print()

            print('{:5s} {:5d} + '.format('', bloc), end='')
            for op, ak, al, bk, bl in sm.get_opcodes():
                if ai == ak and bi == bk:
                    print(b[ba:bi], end='')
                if ai <= ak <= al <= aj:
                    if op == 'equal':
                        print(b[bk:bl], end='')
                    else:
                        print(newcolor+b[bk:bl]+nocolor, end='')
                if al == aj and bl == bj:
                    print(b[bj:bz], end='')
            print()

        else:
            # Try to split the strings in two (same way that difflib does it)
            ak, bk, l = sm.find_longest_match(ai, aj, bi, bj)
            if l > 0:
                visit(ai, ak, bi, bk)
                visit(ak+l, aj, bk+l, bj)
            else:
                # Just print the whole string with ... in the middle
                aij = a[ai:aj]
                if az-aa > max_length:
                    l = (max_length - 3 - (ai-aa) - (az-aj))//2
                    if l >= 0:
                        aij = a[ai:ai+l] + '...' + a[aj-l:aj]
                bij = b[bi:bj]
                if bz-ba > max_length:
                    l = (max_length - 3 - (bi-ba) - (bz-bj))//2
                    if l >= 0:
                        bij = b[bi:bi+l] + '...' + b[bj-l:bj]
                
                print('{:5d} {:5s} - {}'.format(aloc, '',
                                                  a[aa:ai] +
                                                  oldcolor + aij + nocolor +
                                                  a[aj:az]))
                print('{:5s} {:5d} + {}'.format('', bloc,
                                                  b[ba:bi] +
                                                  newcolor + bij + nocolor +
                                                  b[bj:bz]))
                
    # strip outermost non-differences
    diffs = [op for op in ops if op[0] != "equal"]
    _, ai, _, bi, _ = diffs[0]
    _, _, aj, _, bj = diffs[-1]
    visit(ai, aj, bi, bj)

def unified_diff(oldtree, newtree):

    def visit(oldnode, newnode):
        # Usually oldnode and newnode have the same tag, unless they are
        # both the root

        if oldnode.tag not in elements and newnode.tag not in elements:
            # Just compare the nodes as strings
            oldstring = tostring(oldnode)
            newstring = tostring(newnode)
            if oldstring != newstring:
                diff_strings(oldstring, newstring, oldnode.sourceline, newnode.sourceline, max_length)
                        
        else:
            if (oldnode.text or "").strip():
                print("warning: text at start of element at {}:{}".format(args.oldfile, oldnode.sourceline))
            if (newnode.text or "").strip():
                print("warning: text at start of element at {}:{}".format(args.newfile, newnode.sourceline))
            for c in oldnode:
                if (c.tail or "").strip():
                    print("warning: text after element at {}:{}".format(args.oldfile, c.sourceline))
            for c in newnode:
                if (c.tail or "").strip():
                    print("warning: text after element at {}:{}".format(args.newfile, c.sourceline))

            oldchildren = sorted(oldnode, key=opentag)
            newchildren = sorted(newnode, key=opentag)

            for op, oi, oj, ni, nj in difflib.SequenceMatcher(a=list(map(opentag, oldchildren)), b=list(map(opentag, newchildren))).get_opcodes():
                if op != 'equal':
                    for k in range(oi, oj):
                        print('{:5d} {:5s} - {}'.format(oldchildren[k].sourceline, "", oldcolor+tostring(oldchildren[k], max_length)+nocolor))
                    for k in range(ni, nj):
                        print('{:5s} {:5d} + {}'.format("", newchildren[k].sourceline, newcolor+tostring(newchildren[k], max_length)+nocolor))
                else:
                    for ok, nk in zip(range(oi, oj), range(ni, nj)):
                        visit(oldchildren[ok], newchildren[nk])

    oldroot = oldtree.getroot()
    newroot = newtree.getroot()
    visit(oldroot, newroot)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description='Compare two XML files.')
    ap.add_argument('oldfile', help="first XML file")
    ap.add_argument('newfile', help="second XML file")
    ap.add_argument('-w', '--width', type=int, default=80, help="terminal width")
    args = ap.parse_args()

    max_length = args.width - 15
    
    try:
        oldtree = etree.parse(args.oldfile)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("error: {}: {}".format(args.oldfile, e))
        exit(1)
        
    try:
        newtree = etree.parse(args.newfile)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("error: {}: {}".format(args.newfile, e))
        exit(1)
    
    print('*****       - {}'.format(args.oldfile))
    print('      ***** + {}'.format(args.newfile))

    unified_diff(oldtree, newtree)
