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

import sys
import latexcodec, codecs, unicodedata
import lxml.etree as etree, html
import re
import collections
import logging

Entry = collections.namedtuple('Entry', ['open', 'close', 'tag', 'type', 'verbatim'], defaults=[False])
table = [Entry('{', '}', None, 'bracket'),
         Entry('$', '$', 'tex-math', 'bracket', True),
         Entry(r'\(', r'\)', 'tex-math', 'bracket', True),
         Entry(r'\textit', None, 'i', 'unary'),
         Entry(r'\it', None, 'i', 'setter'),
         Entry(r'\emph', None, 'i', 'unary'),
         Entry(r'\em', None, 'i', 'setter'),
         Entry(r'\textbf', None, 'b', 'unary'),
         Entry(r'\bf', None, 'b', 'setter'),
         Entry(r'\url', None, 'url', 'unary', True),
         Entry(r'\fixedcase', None, 'fixed-case', 'unary'),
         Entry(r'root', None, 'root', None),
]
openers = {e.open:e for e in table}
closers = {e.close:e for e in table if e.type == 'bracket'}
tags = {e.tag:e for e in table}
            
token_re = re.compile(r'\\[A-Za-z]+\s*|\\.|.', re.DOTALL)

def parse_latex(s):
    """Parse LaTeX into a list of lists."""
    toks = token_re.findall(s)
    toks = collections.deque(toks)
    stack = [[r'root']]

    def close_implicit():
        # Implicitly close setters
        top = stack.pop()
        open = top[0].rstrip()
        if open == '$':
            logging.warning("unmatched $, treating as dollar sign")
            stack[-1].extend(top)
        else:
            if openers[open].type != 'setter':
                logging.warning("closing unmatched {}".format(open))
            stack[-1].append(top)

    math_mode = False
    while len(toks) > 0:
        tok = toks.popleft()
        tokr = tok.rstrip()

        if (tokr in openers and
            openers[tokr].type in ['bracket', 'setter'] and
            (tokr != '$' or not math_mode)):
            stack.append([tok])
            
        elif (tokr in closers and
              (tokr != '$' or math_mode)):
            open = stack[-1][0].rstrip()
            while open != closers[tokr].open:
                close_implicit()
                open = stack[-1][0].rstrip()
            top = stack.pop()
            stack[-1].append(top)
            
        else:
            stack[-1].append(tok)

        if tokr == '$':
            math_mode = not math_mode
        
        if len(stack[-1]) >= 3 and isinstance(stack[-1][-2], str):
            prev = stack[-1][-2].rstrip()
            if prev in openers and openers[prev].type == 'unary':
                last = stack[-1].pop()
                node = stack[-1].pop()
                stack[-1].append([node, last])

    while len(stack) > 1:
        close_implicit()
        
    return stack[0]

def unparse_latex(l, delete_root=False):
    """Inverse of parse_latex."""
    if isinstance(l, str):
        return l
    elif isinstance(l, list):
        if delete_root:
            return ''.join(map(unparse_latex, l[1:]))
        else:
            open = l[0].rstrip()
            close = openers[open].close or ''
            return ''.join(map(unparse_latex, l)) + close

trivial_math_re = re.compile(r'@?[\d.,]*(\\%|%)?')

def xmlify_string(s):
    """Convert output of parse_latex into an XML string. 
    It does *not* escape <, >, and &."""

    out = []
    
    def visit(node):
        if isinstance(node, str):
            out.append(node)
            return
        
        open = node[0].rstrip()
        tag = openers[open].tag
        if openers[open].verbatim:
            # Delete outer pair of braces if any, so that
            # \url{...} doesn't print braces
            if (len(node) == 2 and
                isinstance(node[1], list) and
                node[1][0] == '{'):
                node[1:] = node[1][1:]
            text = unparse_latex(node, delete_root=True)
            
            # I don't know if this really belongs here, but there are some
            # formulas that should just be plain text
            if tag == 'tex-math' and trivial_math_re.fullmatch(text):
                out.append(text)
            else:
                out.append('<{}>{}</{}>'.format(tag, text, tag))
        else:
            if tag is None:
                close = openers[open].close
            elif tag == 'root':
                open = close = ''
            else:
                open, close = '<{}>'.format(tag), '</{}>'.format(tag)
            out.append(open)
            for child in node[1:]:
                visit(child)
            out.append(close)

    visit(parse_latex(s))
    return ''.join(out)

def unicodify_string(s):
    # BibTeX sometimes has HTML escapes
    #s = html.unescape(s)
    
    # Do a few conversions in the reverse direction first
    # We don't want unescaped % to be treated as a comment character, so escape it
    s = re.sub(r'(?<!\\)%', r'\%', s)

    # Use a heuristic to escape some ties (~),
    s = re.sub(r'(?<=[ (])~(?=\d)', r'\\textasciitilde', s)
    # and go ahead and replace the rest because of a bug in latexcodec
    s = re.sub(r'(?<!\\)~', ' ', s)
    
    s = s.replace('–', '--') # a bug in our system converts --- to –-; this undoes it
    s = s.replace(r'\&', '&')
    
    # A group with a single char should be equivalent to the bare char.
    # Also, this avoids a latexcodec bug for \"{\i}, etc.
    s = re.sub(r'(\\[A-Za-z]+ |\\.)\{([.]|\\i)}', r'\1\2', s)
    
    leading_space = len(s) > 0 and s[0].isspace()
    s = codecs.decode(s, "ulatex+utf8")
    if leading_space: s = " " + s

    # It's easier to deal with control sequences if followed by exactly one space.
    s = re.sub(r'(\\[A-Za-z]+)\s*', r'\1 ', s)

    # Missed due to bugs in latexcodec
    s = s.replace("---", '—')
    s = s.replace("--", '–')
    s = s.replace("``", '“')
    s = s.replace("''", '”')
    # In latest version of latexcodec, but not the one I have
    s = re.sub(r'\\r ([Aa])', '\\1\u030a', s)   # ring
    # Not in latexcodec yet
    s = re.sub(r'\\cb ([SsTt])', '\\1\u0326', s) # comma-below
    s = s.replace(r'\dh ', 'ð')
    s = s.replace(r'\DH ', 'Ð')
    s = s.replace(r'\th ', 'þ')
    s = s.replace(r'\TH ', 'Þ')
    s = s.replace(r'\textregistered ', '®')
    s = s.replace(r'\texttrademark ', '™')
    s = s.replace(r'\textasciigrave ', "‘")
    s = s.replace(r'\textquotesingle ', "’")

    s = s.replace('\u00ad', '') # soft hyphen
    # NFKC normalization would get these, but also others we don't want
    s = s.replace('ﬁ', 'fi') 
    s = s.replace('ﬂ', 'fl')
    s = s.replace('ﬀ', 'ff')
    s = s.replace('ﬃ', 'ffi')
    s = s.replace('ﬄ', 'ffl')

    s = s.replace(r'\$', '$')
    
    # Straight double quote
    # If preceded by a word (possibly with intervening
    # punctuation), it's a right quote.
    s = re.sub(r'(\w[^\s"]*)"', r'\1”', s)
    # Else, if followed by a word, it's a left quote
    s = re.sub(r'"(\w)', r'“\1', s)

    # Backquote
    s = s.replace("`", '‘')

    # Straight single quote
    # Exceptions for apostrophe at start of word
    s = re.sub(r"'(em|round|n|tis|twas|cause|scuse|\d0s)\b", r'’\1', s, flags=re.IGNORECASE)
    s = re.sub(r"(\w[^\s']*)'", r'\1’', s)
    s = re.sub(r"'(\w)", r'‘\1', s)
    
    # Convert combining characters when possible
    s = unicodedata.normalize('NFC', s)

    # Clean up remaining curly braces
    s = re.sub(r'(?<!\\)[{}]', '', s)
    s = re.sub(r'\\([{}])', r'\1', s)

    def repl(m):
        logging.warning("deleting remaining control sequence {}".format(m.group(1)))
        return ""
    s = re.sub(r'(\\[A-Za-z]+\s*|\\.)', repl, s)

    return s

def unicodify_node(t):
    """Convert all text in XML node from LaTeX to Unicode. Destructive."""
    def visit(node):
        if node.tag in tags and tags[node.tag].verbatim:
            return
        if node.text is not None:
            node.text = unicodify_string(node.text)
        for child in node:
            visit(child)
            if child.tail is not None:
                child.tail = unicodify_string(child.tail)
    visit(t)

def contents(node):
    out = []
    if node.text is not None:
        out.append(html.escape(node.text))
    for child in node:
        out.append(etree.tostring(child, encoding=str, with_tail=True))
    return ''.join(out)
    
def convert_string(s):
    s = html.escape(s)
    s = xmlify_string(s)
    s = "<root>{}</root>".format(s)
    t = etree.fromstring(s)
    unicodify_node(t)
    return contents(t)

def convert_node(t):
    """Converts TeX in an XML node to both Unicode and new XML nodes. Nondestructive."""
    # This roundabout path handles things like \emph{foo <b>bar</b> baz} correctly
    s = etree.tostring(t, encoding=str, with_tail=False)
    s = xmlify_string(s)
    t = etree.fromstring(s)
    unicodify_node(t)
    return t

if __name__ == "__main__":
    import fileinput
    for line in fileinput.input():
        """line = convert_string(line)
        print(line)"""
        node = etree.fromstring(line)
        node = convert_node(node)
        print(etree.tostring(node, encoding=str))
