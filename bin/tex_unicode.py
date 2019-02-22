# To do: preserve whitespace

import sys
import latexcodec, codecs, unicodedata
import lxml.etree as etree
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
    stack = [['root']]

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

def make_tree(root):
    """Convert output of parse_latex into an XML string."""

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

    visit(root)
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
    s = s.replace('~', ' ')
    
    s = s.replace('–', '--') # a bug in our system converts --- to –-; this undoes it
    s = s.replace(r'\&', '&amp;') # to avoid having an unescaped & in the output
    
    leading_space = len(s) > 0 and s[0].isspace()
    s = codecs.decode(s, "ulatex+utf8")
    if leading_space: s = " " + s

    # Missed due to bugs in latexcodec
    s = s.replace(r'\^{ı}', 'î')
    s = s.replace(r'\"{ı}', 'ï')
    s = s.replace(r'\'{ı}', 'í')
    s = s.replace(r'\={ı}', 'ī')
    s = s.replace("---", '—')
    s = s.replace("--", '–')
    s = s.replace("``", '“')
    s = s.replace("''", '”')
    # In latest version of latexcodec, but not the one I have
    s = re.sub(r'\\r\s*{([Aa])}', '{\\1\u030a}', s)
    s = re.sub(r'\\r\s+([Aa])', '\\1\u030a', s)
    # Not in latexcodec yet
    s = s.replace(r'\dh(?![A-Za-z])', 'ð')
    s = s.replace(r'\DH(?![A-Za-z])', 'Ð')
    s = s.replace(r'\th(?![A-Za-z])', 'þ')
    s = s.replace(r'\TH(?![A-Za-z])', 'Þ')
    s = s.replace(r'\textregistered(?![A-Za-z])', '®')
    s = s.replace(r'\texttrademark(?![A-Za-z])', '™')
    s = s.replace(r"\textasciigrave(?![A-Za-z])", "‘")
    s = s.replace(r"\textquotesingle(?![A-Za-z])", "’")

    s = s.replace('\u00ad', '') # soft hyphen
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

    m = re.search(r'(\\[A-Za-z]+|\\.)', s)
    if m:
        logging.warning("deleting remaining control sequence {}".format(m.group(1)))
    s = re.sub(r'(\\[A-Za-z]+|\\.)', '', s)
    return s

def unicodify_node(t):
    """Convert all text in XML tree from LaTeX to Unicode."""
    def visit(node):
        if node.tag in tags and tags[node.tag].verbatim:
            return
        if node.text is not None:
            node.text = unicodify_string(node.text)
        for child in node:
            visit(child)
            if child.tail is not None:
                child.tail = unicodify_string(child.tail)

    # By converting from a tree to a string and back, we pick up any
    # additional XML tags that the original string might have had.
    s = etree.tostring(t, with_tail=False, encoding='utf8').decode('utf8')
    l = parse_latex(s)
    t = make_tree(l)
    t = etree.fromstring(t)
    visit(t)
    return t
    
if __name__ == "__main__":
    import fileinput
    for line in fileinput.input():
        line = line.rstrip()
        t = etree.fromstring(line)
        t = unicodify_node(t)
        print(etree.tostring(t, encoding='utf8').decode('utf8'))
