import difflib
import lxml.etree as etree
import operator
import copy

unique_attributes = {'id'}
elements = {'volume', 'paper', 'author', 'editor'}
oldcolor = '\033[91m'
newcolor = '\033[92m'
nocolor = '\033[0m'

def opentag(node, only_unique=False):
    copy = etree.Element(node.tag)
    copy.text = "\n"
    for a, v in sorted(node.attrib.items()):
        if not only_unique or a in unique_attributes:
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

def unified_diff(oldtree, newtree):

    def visit(oldnode, newnode, indent=0):
        # Usually oldnode and newnode have the same tag, unless they are
        # both the root

        if oldnode.tag not in elements and newnode.tag not in elements:
            # Just compare the nodes as strings
            oldstring = tostring(oldnode)
            newstring = tostring(newnode)
            for op, oi, oj, ni, nj in difflib.SequenceMatcher(a=oldstring, b=newstring).get_opcodes():
                if op != 'equal':
                    c = (65-1-indent)//2
                    oa = max(0, oi-c)
                    oz = min(len(oldstring), oj+c)
                    na = max(0, ni-c)
                    nz = min(len(newstring), nj+c)
                    print('{:5d} {:5s} - {}{}'.format(oldnode.sourceline, "", ' '*indent, oldstring[oa:oi]+oldcolor+oldstring[oi:oj]+nocolor+oldstring[oj:oz]))
                    print('{:5s} {:5d} + {}{}'.format("", newnode.sourceline, ' '*indent, newstring[na:ni]+newcolor+newstring[ni:nj]+nocolor+newstring[nj:nz]))
                        
        else:
            indent += 2

            # to do: compare text/tails
            assert (oldnode.text or "").strip() == (newnode.text or "").strip() == ""
            for oc, nc in zip(oldnode, newnode):
                assert (oc.tail or "").strip() == (nc.tail or "").strip() == ""

            def key(c): return opentag(c, True)
            oldchildren = sorted(oldnode, key=key)
            newchildren = sorted(newnode, key=key)

            for op, oi, oj, ni, nj in difflib.SequenceMatcher(a=list(map(key, oldchildren)), b=list(map(key, newchildren))).get_opcodes():
                if op != 'equal':
                    for k in range(oi, oj):
                        print('{:5d} {:5s} - {}{}'.format(oldchildren[k].sourceline, "", ' '*indent, oldcolor+tostring(oldchildren[k], 65-indent)+nocolor))
                    for k in range(ni, nj):
                        print('{:5s} {:5d} + {}{}'.format("", newchildren[k].sourceline, ' '*indent, newcolor+tostring(newchildren[k], 65-indent)+nocolor))
                else:
                    for ok, nk in zip(range(oi, oj), range(ni, nj)):
                        visit(oldchildren[ok], newchildren[nk], indent)

    oldroot = oldtree.getroot()
    newroot = newtree.getroot()
    visit(oldroot, newroot)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description='Compare two XML files.')
    ap.add_argument('oldfile', help="first XML file")
    ap.add_argument('newfile', help="second XML file")
    args = ap.parse_args()
    
    oldtree = etree.parse(args.oldfile)
    newtree = etree.parse(args.newfile)
    
    unified_diff(oldtree, newtree)
