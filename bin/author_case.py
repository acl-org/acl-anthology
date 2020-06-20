#!/usr/bin/env python3

"""author_case.py

Try to correct author names that are written in all uppercase or all lowercase.

usage: author_case.py

Writes to stdout a list of changes that can be read by
change_authors.py. The user can edit this list before giving it to
change_authors.py to actually apply the changes.
"""

import sys
import os.path
import anthology
import logging
import re

logging.basicConfig(level=logging.INFO)

# Two-letter words that should be changed from upper->titlecase
two_letter = [
    # Mandarin Pinyin
    # https://gist.github.com/stevejackson/1429696
    'ba pa ma fa da ta na la ga ka ha za ca sa',
    'za ca sa',
    'ai',
    'an',
    'ao',
    'me de te ne le ge ke he re ce se',
    'ei',
    'er',
    'yi bi pi mi di ti ni li ji qi xi ri zi ci si',
    'ya ye yo yu',
    'bo po mo fo lo',
    'ou',
    'wu bu pu mu fu du tu nu lu gu ku hu ru zu cu su',
    'wa wo',
    'nv lv ju qu',
    # Cantonese
    'ng',
]
two_letter = set().union(*[s.split() for s in two_letter])

# Words that should not be changed from upper->titlecase
upper = set('III PVS GSK'.split())


def normalize(s):
    if s == s.lower():
        s = s.title()
    else:
        words = re.split(r'([ .-])', s)
        for i in range(0, len(words), 2):
            w = words[i]
            if w == w.upper() and (
                len(w) >= 3 and w not in upper or len(w) == 2 and w.lower() in two_letter
            ):
                w = w.title()
            words[i] = w
        s = ''.join(words)
    return s


if __name__ == "__main__":
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    datadir = os.path.join(scriptdir, '..', 'data')
    anth = anthology.Anthology(importdir=datadir)
    for paperid, paper in anth.papers.items():
        for role in ['author', 'editor']:
            if role in paper.attrib:
                for name, personid in paper.attrib[role]:
                    # Many mononyms are corporate authors containing
                    # acronyms; better not to touch these
                    if name.first is None or name.first == '':
                        continue
                    first_norm = normalize(name.first)
                    last_norm = normalize(name.last)
                    if name.first != first_norm or name.last != last_norm:
                        print(
                            '{}\t{}\t{} || {}\t{} || {}'.format(
                                paperid,
                                role,
                                name.first,
                                name.last,
                                first_norm,
                                last_norm,
                            )
                        )
