#!/usr/bin/env python3

import re, sys, os
import inspect
import nltk.tokenize, nltk.corpus
from collections import defaultdict

from nltk.tokenize.treebank import TreebankWordDetokenizer

falselist = set([w for w in nltk.corpus.words.words() if w.islower()])
separators = [":", "--", "\u2013", "---", "\u2014", "\u2015"]


def is_hyphen(s):
    return s in ("-", "–")


def no_hyphens(ws):
    return tuple(w for w in ws if not is_hyphen(w))


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
    """Splits tokens (hyphens/slashes count as separate tokens)."""
    tokens = []
    # NLTK tokenizer uses PTB standard, which doesn't split on hyphens or slashes
    for tok in nltk.tokenize.word_tokenize(s):
        # tokenizer normalizes quotes etc., so we need to detokenize later
        tokens.extend([t for t in re.split(r"([-–/])", tok) if t != ""])
    return tokens


def fixedcase_word(w, truelist=None, falselist=None, allcaps=False):
    """Returns True if w should be fixed-case, False if not, None if unsure."""
    if not allcaps and any(c.isupper() for c in w[1:]):
        return True
    if truelist is not None and w in truelist:
        return True
    if falselist is not None and w in falselist:
        return False


def fixedcase_prefix(
    ws, truelist=None, phrase_truelist=None, falselist=None, allcaps=False
):
    """Returns a list of 1 or more bools: True if some prefix of the tuple 'ws' should be fixed-case,
    False if not, None if unsure."""
    # phrase_truelist is sorted in descending order by phrase length
    if phrase_truelist is not None:
        for n, truelist_bin in phrase_truelist:
            if ws[:n] in truelist_bin:
                return [True] * n
            if len(no_hyphens(ws)) >= n and no_hyphens(ws)[:n] in truelist_bin:
                # no hyphens in truelist entries
                bs = []
                i = 0
                for tok in ws:
                    if is_hyphen(tok):
                        bs.append(False)
                    else:
                        bs.append(True)
                        i += 1
                        if i == n:
                            break
                return bs
    return [
        fixedcase_word(ws[0], truelist=truelist, falselist=falselist, allcaps=allcaps)
    ]


def fixedcase_title(
    ws,
    truelist=None,
    phrase_truelist=None,
    amodifiers=None,
    ndescriptors=None,
    falselist=None,
):
    """Returns a list of bools: True if w should be fixed-case, False if
    not, None if unsure."""

    # Consider a title to be "all caps" if at least 50% of letters
    # are capitals. Non-alpha tokens are considered upper case.
    allcaps = len([w for w in ws if w == w.upper()]) / len(ws) > 0.5
    bs = []
    ws = tuple(ws)
    i = 0
    while i < len(ws):
        b = fixedcase_prefix(
            ws[i:],
            truelist=truelist,
            phrase_truelist=phrase_truelist,
            falselist=falselist,
            allcaps=allcaps,
        )
        if i == 0:
            if b[0] is None and len(ws) >= 2 and ws[1] in separators:
                # In titles of the form "BLEU: a Method for Automatic Evaluation of Machine Translation,"
                # where the first part is a single word, mark it as fixed-case
                b[0] = True
        elif b[0] and amodifiers and ws[i - 1] in amodifiers:  # e.g. North America
            bs[-1] = True
        elif b[0] and is_hyphen(ws[i - 1]) and amodifiers and ws[i - 2] in amodifiers:
            bs[-2] = True
        elif not b[0] and bs[-1] and ndescriptors and ws[i] in ndescriptors:
            # "<name> <ndescriptor>", e.g. Columbia University
            b[0] = True
        elif ndescriptors and i >= 2 and ws[i - 1] == "of" and ws[i - 2] in ndescriptors:
            # "<ndescriptor> of <name>", e.g. University of Edinburgh
            if b[0]:
                bs[-2] = True
            else:
                print(ws[i - 2 :], file=sys.stderr)
                # mainly: University of X where X is not in the truelist
        bs.extend(b)
        i += len(b)
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


def load_lists():
    truelist = set()
    phrase_truelist = defaultdict(set)
    module_file = inspect.getfile(inspect.currentframe())
    module_dir = os.path.dirname(os.path.abspath(module_file))
    truelist_file = os.path.join(module_dir, "truelist")
    for line in open(truelist_file):
        line = line.split("#")[0].strip()
        if line == "":
            continue
        assert not any(
            is_hyphen(c) for c in line
        ), f'Truelist entries should not contain hyphens: {line}'
        if ' ' not in line:
            truelist.add(line)
        else:
            toks = tuple(tokenize(line))
            phrase_truelist[len(toks)].add(toks)  # group phrases by number of tokens
    phrase_truelist = sorted(
        phrase_truelist.items(), reverse=True
    )  # bins sorted by phrase length
    amodifiers = (
        'North',
        'South',
        'East',
        'West',
        'Northeast',
        'Northwest',
        'Southeast',
        'Southwest',
        'Central',
        'Northern',
        'Southern',
        'Eastern',
        'Western',
        'Northeastern',
        'Northwestern',
        'Southeastern',
        'Southwestern',
        'Modern',
        'Ancient',
    )  # use subsequent word to determine fixed-case. will miss hyphenated modifiers (e.g. South-East)
    ndescriptors = (
        'Bay',
        'Coast',
        'Gulf',
        'Island',
        'Isle',
        'Lake',
        'Republic',
        'University',
    )  # use preceding word to determine fixed-case

    return truelist, phrase_truelist, amodifiers, ndescriptors
