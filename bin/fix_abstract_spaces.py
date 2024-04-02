#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2023 Guy Aglionby <guy@guyaglionby.com>
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

"""Adds missing spaces between sentences in the abstracts in the
paper metadata. This script takes a conservative approach so as not
to split up URLs or the names of systems that include a full stop.
There are three criteria to be met before a space is added:

1. The words before and after the full stop must be valid English words
2. The word before the full stop must be all lowercase
3. The word after the full stop must have only the first letter capitalised

Usage: python3 fix_abstract_spaces.py
"""
import glob
import os
import re

from lxml import etree
from tqdm import tqdm


def load_english_words():
    try:
        with open('words_alpha.txt') as f:
            loaded_words = {line.strip() for line in f}
    except FileNotFoundError:
        raise FileNotFoundError(
            'Download words_alpha.txt from '
            'https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt'
        )

    loaded_words = {w for w in loaded_words if len(w) > 1}
    loaded_words -= {'com', 'org', 'net', 'edu', 'gov', 'mil', 'int', 'eu'}
    return loaded_words


missing_space_re = re.compile(r'([a-z]+)\.([A-Z][a-z]+)')
words = load_english_words()


def fix_abstract(text):
    has_change = False
    matches = missing_space_re.findall(text)

    for m in matches:
        if m[0].lower() not in words or m[1].lower() not in words:
            continue

        has_change = True
        text = text.replace(f'{m[0]}.{m[1]}', f'{m[0]}. {m[1]}')

    if has_change:
        return text

    return False


def handle_file(filename):
    root = etree.parse(filename)
    abstracts = root.xpath('//abstract')
    n_changes = 0

    for abstract in abstracts:
        text = abstract.text
        if text is None:
            continue
        fixed = fix_abstract(text)
        if fixed:
            abstract.text = fixed
            n_changes += 1

    root.write(filename, pretty_print=True, encoding='utf-8', xml_declaration=True)
    return n_changes


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    xml_data_files = list(glob.glob(os.path.join(root_dir, 'data', 'xml', '*.xml')))

    n_changes = 0

    for filename in tqdm(xml_data_files):
        n_changes += handle_file(filename)

    print(f'Fixed {n_changes} abstracts')


if __name__ == '__main__':
    main()
