#!/usr/bin/env python3

import sys
import logging
import collections, copy
import re
import latexcodec, codecs
import lxml.etree as etree

Entry = collections.namedtuple("Entry", ["open", "close", "tag", "type", "verbatim"])
table = [
    Entry("{", "}", None, "bracket", False),
    Entry("$", "$", "tex-math", "bracket", True),
    Entry(r"\(", r"\)", "tex-math", "bracket", True),
    Entry(r"\emph", None, "i", "unary", False),
    Entry(r"\em", None, "i", "setter", False),
    Entry(r"\textit", None, "i", "unary", False),
    Entry(r"\it", None, "i", "setter", False),
    Entry(r"\textsl", None, "i", "unary", False),
    Entry(r"\sl", None, "i", "setter", False),
    Entry(r"\textbf", None, "b", "unary", False),
    Entry(r"\bf", None, "b", "setter", False),
    # Entry(r'\textsc', None, 'sc', 'unary', False),
    # Entry(r'\sc', None, 'sc', 'setter', False),
    Entry(r"\url", None, "url", "unary", True),
    Entry(r"\footnote", None, "fn", "unary", False),
    Entry(r"\href", None, "delete", "unary", False),
    # \cite and friends. There are a lot more, but these are the most common.
    Entry(r"\cite", None, "cite", "unary", False),
    Entry(r"\newcite", None, "cite", "unary", False),
    Entry(r"\citet", None, "cite", "unary", False),
    Entry(r"\citep", None, "cite", "unary", False),
    Entry(r"\fixedcase", None, "fixed-case", "unary", False),  # for our internal use
    Entry(r"", None, None, "trivial", False),
]
openers = {e.open: e for e in table}
closers = {e.close: e for e in table if e.type == "bracket"}
tags = {e.tag: e for e in table}

token_re = re.compile(r"\\[A-Za-z]+\s*|\\.|.", re.DOTALL)


def tokenize_latex(s):
    return token_re.findall(s)


def parse_latex(s):
    """Parse LaTeX into a list of lists. The original string can be
    recovered by recursively joining the lists. A list is formed for
    anything listed in `table`. The first and last element of the list
    are always the opener and (possibly empty) closer, and the middle
    elements are the contents.
    """

    stack = [[""]]

    def close_implicit():
        # Implicitly close setters
        top = stack.pop()
        open = top[0].rstrip()
        if open == "$":
            logging.warning("unmatched $, treating as dollar sign")
            stack[-1].extend(top)
        else:
            if openers[open].type != "setter":
                logging.warning("closing unmatched {}".format(open))
            top.append("")
            stack[-1].append(top)

    math_mode = False
    for tok in tokenize_latex(s):
        tokr = tok.rstrip()

        # An opener starts a new list
        if (
            tokr != "$"
            and tokr in openers
            and openers[tokr].type != "trivial"
            or tokr == "$"
            and not math_mode
        ):
            stack.append([tok])

        # A closer
        elif tokr != "$" and tokr in closers or tokr == "$" and math_mode:

            # Look for the matching opener, which might not be on top
            for i in reversed(range(len(stack))):
                if stack[i][0].rstrip() == closers[tokr].open:
                    break
            else:
                logging.warning("unexpected {}".format(tokr))
                stack[-1].append(tok)
                continue

            # Close any intervening openers (e.g., \em in {a \em b})
            while len(stack) - 1 > i:
                close_implicit()

            stack[-1].append(tok)
            top = stack.pop()
            stack[-1].append(top)

        else:
            stack[-1].append(tok)

        if tokr == "$":
            math_mode = not math_mode

        if len(stack[-1]) == 2:
            open = stack[-1][0].rstrip()
            if openers[open].type == "unary":
                top = stack.pop()
                top.append("")
                stack[-1].append(top)

    while len(stack) > 1:
        close_implicit()
    stack[-1].append("")

    return stack[0]


def flatten(l):
    def visit(l):
        if isinstance(l, str):
            out.append(l)
        else:
            for c in l:
                visit(c)

    out = []
    visit(l)
    return "".join(out)


def latex_to_unicode(s):
    """Convert (La)TeX control sequences in string s to their Unicode equivalents."""

    # Convert \\ to newline; this also ensures that remaining
    # backslashes really introduce control sequences.
    s = re.sub(r"\\\\", "\n\n", s)

    ### Do a few conversions in the reverse direction first

    # % is probably percent (not a comment delimiter)
    s = re.sub(r"(?<!\\)%", r"\%", s)

    # Use a heuristic to decide whether ~ means "approximately" or is a tie
    s = re.sub(r"(?<=[ (])~(?=\d)", r"\\textasciitilde ", s)
    s = re.sub(r"^~(?=\d)", r"\\textasciitilde ", s)

    # An old bug in our system converted --- to –-; this undoes it
    s = s.replace("–", "--")

    ### Some normalization to make later processing easier.

    # It's easier to deal with control sequences if followed by exactly one space.
    # latexcodec does preserve this space.
    s = re.sub(r"(\\[A-Za-z]+)\s*", r"\1 ", s)

    # Change strings like \'{e} into {\'e}.
    # Also, this avoids a latexcodec bug for \"{\i}, etc.
    s = re.sub(r"(\\[A-Za-z]+ |\\.)\{([^\\{}]|\\i )}", r"{\1\2}", s)

    ### Call latexcodec

    # preserve leading space, which latexcodec strips
    leading_space = len(s) > 0 and s[0].isspace()
    s = codecs.decode(s, "ulatex+utf8")
    if leading_space:
        s = " " + s

    ### Missing from latexcodec (as of version 1.0.7)
    s = re.sub(r"\\textcommabelow ([SsTt])", "\\1\N{COMBINING COMMA BELOW}", s)
    s = s.replace(r"\dj ", "đ")
    s = s.replace(r"\DJ ", "Đ")
    s = s.replace(r"\hwithstroke ", "ħ")
    s = s.replace(r"\Hwithstroke ", "Ħ")
    s = s.replace(r"\textquotesingle ", "'")
    s = s.replace(r"\textquotedblleft ", "“")
    s = s.replace(r"\textquotedblright ", "”")

    ### Intentionally missing from latexcodec
    s = s.replace(r"\$", "$")
    s = s.replace(r"\&", "&")
    s = s.replace("`", "‘")

    # Clean up
    s = re.sub(r"(?<!\\)[{}]", "", s)  # unescaped curly braces
    s = s.replace(r"\{", "{")
    s = s.replace(r"\}", "}")

    def repl(s):
        logging.warning(f"discarding control sequence '{s.group(0)}' from '{s.string}'")
        return ""

    s = re.sub(r"\\[A-Za-z]+ |\\.", repl, s)

    return s


math_table = {r"\sim": r"\textasciitilde"}
for c in list(".,@%~") + [r"\%"]:
    math_table[c] = c


def flatten_trivial_math(node):
    """Convert math that doesn't really need to be math into text."""

    def visit(node):
        if isinstance(node, str):
            return
        elif openers[node[0].rstrip()].tag == "tex-math":
            if all(
                isinstance(child, str)
                and (child.isspace() or child.isdigit() or child in math_table)
                for child in node[1:-1]
            ):
                node[0] = "{"
                for i in range(1, len(node) - 1):
                    if node[i] in math_table:
                        node[i] = math_table[node[i]]
                node[-1] = "}"
        for child in node:
            visit(child)

    node = copy.deepcopy(node)
    visit(node)
    return node


def remove_notes(node):
    def visit(node, outparent):
        if isinstance(node, str):
            outparent.append(node)
        elif isinstance(node, list):
            if openers[node[0].rstrip()].tag in ["fn", "delete"]:
                return  # without copying
            elif openers[node[0].rstrip()].tag == "cite":
                outparent.append("(CITATION)")
            else:
                outnode = []
                for child in node:
                    visit(child, outnode)
                outparent.append(outnode)

    outroot = []
    visit(node, outroot)
    assert len(outroot) == 1
    return outroot[0]


def append_text(xnode, text):
    if len(xnode) == 0:
        xnode.text = (xnode.text or "") + text
    else:
        xnode[-1].tail = (xnode[-1].tail or "") + text


def latextree_to_xml(node):
    """Convert a LaTeX tree to XML."""

    def visit(node, xparent=None):
        if isinstance(node, str):
            append_text(xparent, node)

        else:
            open = node[0].rstrip()

            tag = openers[open].tag
            if tag is None:
                # Convert opener and closer into text
                append_text(xparent, node[0])
                for child in node[1:-1]:
                    visit(child, xparent)
                append_text(xparent, node[-1])

            else:
                # Create element with equivalent HTML tag
                xnode = etree.Element(tag)
                xparent.append(xnode)

                if openers[open].type == "unary":
                    # When the argument is a group, the braces are not included.
                    # This is especially important for \url
                    assert len(node) == 3 and node[1][0] == "{"
                    node = node[1]

                if openers[open].verbatim:
                    xnode.text = "".join(flatten(child) for child in node[1:-1])
                else:
                    for child in node[1:-1]:
                        visit(child, xnode)

    xroot = etree.Element("root")
    visit(node, xroot)
    return xroot


def xml_to_unicode(xtree):
    """Call latex_to_unicode on all text nodes in an XML tree."""

    def visit(xnode):
        if xnode.tag == "root" or not tags[xnode.tag].verbatim:
            if xnode.text:
                xnode.text = latex_to_unicode(xnode.text)
            for child in xnode:
                visit(child)
        if xnode.tail:
            xnode.tail = latex_to_unicode(xnode.tail)

    xtree = copy.deepcopy(xtree)
    visit(xtree)
    return xtree


def latex_to_xml(s, fixed_case=False, trivial_math=False):
    tree = parse_latex(s)
    if fixed_case:
        tree = find_fixed_case(tree, conservative=True)
    if trivial_math:
        tree = flatten_trivial_math(tree)
    tree = remove_notes(tree)
    tree = latextree_to_xml(tree)
    tree = xml_to_unicode(tree)
    return tree


def find_fixed_case(node, conservative=False):
    def visit(cur, prev):
        if isinstance(cur, str):
            return cur

        if cur[0] == "{":
            if (
                isinstance(cur[1], str)
                and cur[1].startswith("\\")
                or isinstance(cur[1], list)
                and cur[1][0].startswith("\\")
            ):
                # {\...} does *not* protect case
                return  # and don't recurse
            elif conservative and isinstance(prev, str) and prev.startswith("\\"):
                # \cmd{...} does protect case, but in practice,
                # this never seems to be the intent.
                pass
            elif (
                conservative
                and len(cur) == 3
                and isinstance(cur[1], list)
                and cur[1][0] in ["$", r"\)"]
            ):
                # Don't mark {$...$}
                pass
            else:
                cur[:] = [r"\fixedcase", cur[:], ""]

        elif cur[0] in ["$", r"\)"]:
            return  # Don't recurse into math

        prev = cur[0]
        for child in cur[1:-1]:
            visit(child, prev)
            prev = child

    if conservative:
        # Check if whole field is surrounded with braces
        braces = 0
        text = False
        for child in node[1:-1]:
            if isinstance(child, str) and not child.isspace():
                text = True
            if isinstance(child, list) and child[0] == "{":
                braces += 1
        if not text and braces == 1:
            return node

    node = copy.deepcopy(node)
    visit(node, None)
    return node


if __name__ == "__main__":
    import fileinput

    for line in fileinput.input():
        line = line.rstrip()
        tree = latex_to_xml(line, fixed_case=True, trivial_math=True)
        print(etree.tostring(tree, encoding="unicode"))
        # print(latex_to_unicode(line))
