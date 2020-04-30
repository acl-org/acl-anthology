#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import sys
from collections import Counter

from common import *

if __name__ == "__main__":
    c = Counter()
    # First pass: count 2-, 3-, 4-, and 5-grams (counting hyphens as spaces)
    # where at least the first and last words have initial caps
    for xmlfile in sys.argv[1:]:
        print(xmlfile)
        tree = ET.parse(xmlfile)
        for paper in tree.getroot().findall(".//paper"):
            for abstract in paper.findall("abstract"):
                toks = tokenize(get_text(abstract).replace('-', ' '))
                for i, w in enumerate(toks[:-1]):
                    if w[0].isupper():
                        queue = []
                        if toks[i + 1][0].isupper():
                            queue.append(tuple(toks[i : i + 2]))  # bigram
                        if i + 2 < len(toks) and toks[i + 2][0].isupper():
                            queue.append(tuple(toks[i : i + 3]))  # trigram
                        if i + 3 < len(toks) and toks[i + 3][0].isupper():
                            queue.append(tuple(toks[i : i + 4]))  # 4-gram
                        if i + 4 < len(toks) and toks[i + 4][0].isupper():
                            queue.append(tuple(toks[i : i + 5]))  # 5-gram
                        for phr in queue:
                            if '.' in phr or ',' in phr or '(' in phr or ')' in phr:
                                continue
                            c[phr] += 1

    print(f'{len(c)} entries before filtering')
    for k, v in c.copy().items():
        if v < 3:
            del c[k]
    print(f'{len(c)} entries after min 3 threshold')

    d = {' '.join(k).lower(): Counter() for k in sorted(c)}
    print(f'{len(d)} unique entries ignoring case')

    # Second pass: filter to n-grams that are capitalized in most abstracts,
    # and that appear in titles

    # Count each way of capitalizing the phrase (first match per abstract),
    # and occurrences in titles regardless of capitalization
    intitles = Counter()
    for xmlfile in sys.argv[1:]:
        print(xmlfile)
        tree = ET.parse(xmlfile)
        for paper in tree.getroot().findall(".//paper"):
            for abstract in paper.findall("abstract"):
                toks = tokenize(get_text(abstract).replace('-', ' '))
                s = ' '.join(toks)
                s_lower = s.lower()
                for q in d:
                    i = s_lower.find(q)
                    if i > -1:
                        d[q][s[i : i + len(q)]] += 1
            for title in paper.findall("title") + paper.findall("booktitle"):
                titleS = ' '.join(tokenize(get_text(title).replace('-', ' ').lower()))
                for q in d:
                    if f' {q} ' in f' {titleS} ':
                        intitles[q] += 1

    print(f'{len(intitles)} of the entries occur in titles')

    # # normalize hyphens
    # for q in d.copy():
    #     if ' - ' in q:
    #         hyphC = d[q]
    #         dehyphC = Counter({k.replace(' - ', ' '): v for k,v in hyphC.items()})
    #         d.setdefault(q.replace(' - ', ' '), Counter())
    #         d[q.replace(' - ', ' ')] += dehyphC
    #         del d[q]
    #         intitles[q.replace(' - ', ' ')] += intitles[q]
    #         del intitles[q]
    # print(f'{len(d)} unique entries after normalizing hyphens')

    old_uni_truelist, old_phrase_truelist, amodifiers, ndescriptors = load_lists()

    newC = Counter()
    filterLater = set()
    for q in d:
        if (
            intitles[q] > 0 and d[q][q] / sum(d[q].values()) <= 0.25
        ):  # no more than 25% instances of the phrase are all-lowercase
            top_spelling = d[q].most_common(1)[0][0]
            # this is a spelling where the first and last word are capitalized
            if (
                top_spelling[0].isupper()
                and top_spelling[top_spelling.rindex(' ') + 1].isupper()
            ):
                # store the most frequent capitalization
                # with # of times the phrase occurred non-lowercased
                newC[top_spelling] = sum(d[q].values()) - d[q][q]

                # would this be truecased already?
                toks = top_spelling.split()
                # all-caps title heuristic can be unfair on short n-grams,
                # so append some dummy words
                bs = fixedcase_title(
                    toks + ['The', 'the', 'The', 'the', 'The'],
                    truelist=old_uni_truelist,
                    phrase_truelist=old_phrase_truelist,
                    amodifiers=amodifiers,
                    ndescriptors=ndescriptors,
                )

                # does this spelling meet all the criteria for a truelist phrase?
                # if not, count it for now (to apply inclusion-exclusion)
                # but mark it for removal later
                keep = False
                for tok, b in zip(toks, bs):
                    if (
                        not b
                        and tok[0].isupper()
                        and not any(c.isupper() for c in tok[1:])
                    ):
                        keep = True
                        break
                if not keep:
                    filterLater.add(top_spelling)

    print(f'{len(newC)} usually capitalized phrases that occur in titles')

    # print(newC)
    newC1 = newC.copy()

    # For 3-, 4-, and 5-grams, subtract counts for subsumed (n-1)-grams
    for phr, n in sorted(newC.copy().items(), key=lambda s: s.count(' '), reverse=True):
        if phr.count(' ') > 1:
            toks = tuple(phr.split())
            newC[' '.join(toks[:-1])] -= n
            newC[' '.join(toks[1:])] -= n
            if len(toks) > 3:  # inclusion-exclusion
                # correct for double-counting of overlap between 2 spans just decremented
                newC[' '.join(toks[1:-1])] += n

                if len(toks) > 4:
                    newC[' '.join(toks[2:-1])] -= n
                    newC[' '.join(toks[1:-2])] -= n

    # print(newC)

    new_truelist = [phr for phr in newC1 if newC[phr] >= 3 and phr not in filterLater]
    new_truelist.sort()

    # truelist = []
    # for w_lower in c:
    #     if w_lower in falselist:
    #         continue
    #     if w_lower != max(c[w_lower], key=c[w_lower].get):
    #         for w in c[w_lower]:
    #             if fixedcase_word(w) == None:
    #                 truelist.append(w)
    # truelist.sort()

    with open("truelist-phrasal-auto", "w") as outfile:
        print("# Automatically generated by train_phrasal.py", file=outfile)
        for phr in new_truelist:
            print(phr, file=outfile)
