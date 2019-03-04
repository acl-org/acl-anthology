#!/usr/bin/env python3

"""Try to convert ACL Anthology XML format to a standard form, in
which:

- Outside of formulas, no LaTeX is used; only Unicode
- Formulas are tagged as <tex-math> and use LaTeX

Usage: python3 normalize_anth.py <infile> <outfile>

Bugs: 

- Doesn't preserve line breaks and indentation.
"""

import lxml.etree as etree
import re
import difflib
import logging
from tex_unicode import convert_node

logging.basicConfig(format='%(levelname)s:%(location)s %(message)s', level=logging.INFO)
def filter(r):
    r.location = location
    return True
logging.getLogger().addFilter(filter)

def replace_node(old, new):
    save_tail = old.tail
    old.clear()
    old.tag = new.tag
    old.attrib.update(new.attrib)
    old.text = new.text
    old.extend(new)
    old.tail = save_tail

if __name__ == "__main__":
    import sys
    import argparse
    ap = argparse.ArgumentParser(description='Convert LaTeX commands and special characters.')
    ap.add_argument('infile', help="XML file to read")
    ap.add_argument('outfile', help="XML file to write")
    args = ap.parse_args()

    tree = etree.parse(args.infile)
    root = tree.getroot()
    for paper in root.findall('paper'):
        fullid = "{}-{}".format(root.attrib['id'], paper.attrib['id'])
        for oldnode in paper:
            location = "{}:{}".format(fullid, oldnode.tag)
            
            if oldnode.tag in ['url', 'href', 'mrf', 'doi', 'bibtype', 'bibkey',
                               'revision', 'erratum', 'attachment', 'paper',
                               'presentation', 'dataset', 'software', 'video']:
                continue
            
            try:
                newnode = convert_node(oldnode)
            except ValueError as e:
                logging.error("unicodify raised exception {}".format(e))
                continue
            
            oldstring = etree.tostring(oldnode, with_tail=False, encoding='utf8').decode('utf8')
            oldstring = " ".join(oldstring.split())
            newstring = etree.tostring(newnode, with_tail=False, encoding='utf8').decode('utf8')
            newstring = " ".join(newstring.split())
            
            if newstring != oldstring:
                replace_node(oldnode, newnode)
                for op, oi, oj, ni, nj in difflib.SequenceMatcher("", oldstring, newstring).get_opcodes():
                    if op != 'equal':
                        ws = 20
                        red = '\033[91m'
                        green = '\033[92m'
                        off = '\033[0m'
                        logging.info('{}{}{}{}{}'.format(oldstring[max(0,oi-ws):oi], red, oldstring[oi:oj], off, oldstring[oj:oj+ws]))
                        logging.info('{}{}{}{}{}'.format(newstring[max(0,ni-ws):ni], green, newstring[ni:nj], off, newstring[nj:nj+ws]))
                    
    tree.write(args.outfile, encoding="UTF-8", xml_declaration=True)
