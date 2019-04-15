import xml.etree.ElementTree as ET
import sys
from common import *

def find_any(text, words, i=0):
    for w in words:
        j = text.find(w, i)
        if j >= 0:
            return j, j+len(w)
    return None

# recursive helper called by protect
# protect text of "node", including children, and tails of children
def protect_recurse(node, words):
    if node.tag == 'fixed-case':	# already protected, do nothing
        return node
    newnode = ET.Element(node.tag, node.attrib)
    def process(text):
        if text is None: return
        i = 0
        span = find_any(text, words)
        while span is not None:
            append_text(newnode, text[i:span[0]])
            p = ET.Element('fixed-case')
            p.text = text[span[0]:span[1]]
            newnode.append(p)
            i = span[1]
            span = find_any(text, words, i)
        append_text(newnode, text[i:])
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
    for line in open("truelist"):
        line = line.split('#')[0].strip()
        if line == "": continue
        truelist.add(line)
    
    infile, outfile = sys.argv[1:]
    
    tree = ET.parse(infile)
    for paper in tree.getroot().findall('paper'):
        for title in paper.findall('title'):
            titletext = tokenize(get_text(title))
            fixed = fixedcase_title(titletext, truelist=truelist, falselist=falselist)
            if any(fixed):
                print("old:", ET.tostring(title).decode('ascii').rstrip())
                words = [w for w, b in zip(titletext, fixed) if b]
                replace_node(title, protect(title, words))
                print("new:", ET.tostring(title).decode('ascii').rstrip())
    tree.write(outfile, encoding="UTF-8", xml_declaration=True)
    with open(outfile, "a") as outfilehandle:
        outfilehandle.write("\n")


