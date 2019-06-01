#!/usr/bin/env python3

import re
import nltk.tokenize, nltk.corpus

falselist = set([w for w in nltk.corpus.words.words() if w.islower()])
separators = [':', '-', '--', '\u2013', '---', '\u2014', '\u2015']

def get_text(node):
    result = []
    def visit(node):
        if node is not None:
            if node.text is not None:
                result.append(node.text)
            for child in node:
                visit(child)
            if node.tail is not None:
                result.append(node.tail)
    visit(node)
    return "".join(result)

def tokenize(s):
    tokens = []
    # NLTK tokenizer uses PTB standard, which doesn't split on hyphens or slashes
    for tok in nltk.tokenize.word_tokenize(s):
        tokens.extend([t for t in re.split(r'[-–/]', tok) if t != ''])
    return tokens
    
def fixedcase_word(w, truelist=None, falselist=None, allcaps=False):
    """Returns True if w should be fixed-case, False if not, None if unsure."""
    if not allcaps and any(c.isupper() for c in w[1:]): return True
    if truelist is not None and w in truelist: return True
    if falselist is not None and w in falselist: return False

def fixedcase_title(ws, truelist=None, falselist=None):
    """Returns a list of bools: True if w should be fixed-case, False if
    not, None if unsure."""
    
    # Consider a title to be "all caps" if at least 50% of letters
    # are capitals. Non-alpha tokens are considered upper case.    
    allcaps = len([w for w in ws if w == w.upper()])/len(ws) > 0.5
    bs = []
    for i, w in enumerate(ws):
        b = fixedcase_word(w, truelist=truelist, falselist=falselist, allcaps=allcaps)
        if b is None:
            # In titles of the form "BLEU: a Method for Automatic Evaluation of Machine Translation,"
            # where the first part is a single word, mark it as fixed-case
            if len(ws) >= 2 and i == 0 and ws[1] in separators:
                b = True
        bs.append(b)
    return bs
        
def replace_node(old, new):
    old.clear()
    old.tag = new.tag
    old.attrib.update(new.attrib)
    old.text = new.text
    old.extend(new)
    old.tail = new.tail

def append_text(node, text):
    if len(node) == 0:
        if node.text is None:
            node.text = ""
        node.text += text
    else:
        if node[-1].tail is None:
            node[-1].tail = ""
        node[-1].tail += text
