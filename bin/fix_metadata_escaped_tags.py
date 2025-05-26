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

"""Finds and fixes instances where HTML tags in the paper metadata have been escaped, and so are not rendered as HTML
 tags in the Anthology.

Usage: python3 fix_metadata_escaped_tags.py
"""
import glob
import os
import re

from tqdm import tqdm

# < and > are used for things other than HTML tags, so only capture common HTML tags
html_tag_re = re.compile(r'&lt;/?(?:b|i|sup)&gt;')


def fix_text(text):
    matches = html_tag_re.findall(text, re.MULTILINE)

    if not len(matches):
        return False

    # Validate that the tags are properly matched, making sure we only capture things that should be HTML tags
    # n.b. doesn't handle nesting, but there were no nested tags in the data
    assert len(matches) % 2 == 0
    match_pairs = list(zip(matches[::2], matches[1::2]))
    for _open, close in match_pairs:
        open_tag = _open.split()[0][4:].replace('&gt;', '')
        close_tag = close[5:].replace('&gt;', '')
        assert open_tag == close_tag, (open_tag, close_tag)

    # Do the replacements
    unique_matches = set(matches)
    for m in unique_matches:
        text = text.replace(m, m.replace('&gt;', '>').replace('&lt;', '<'))

    return text


def handle_file(filename):
    with open(filename) as f:
        lines = f.read()

    abstracts = re.findall(r'<abstract>.*?</abstract>', lines, re.DOTALL)
    titles = re.findall(r'<title>.*?</title>', lines, re.DOTALL)
    all_fields = abstracts + titles

    n_changes = 0

    for field in all_fields:
        potentially_changed = fix_text(field)
        if potentially_changed:
            lines = lines.replace(field, potentially_changed)
            n_changes += 1

    with open(filename, 'w') as f:
        f.write(lines)
    return n_changes


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    xml_data_files = list(glob.glob(os.path.join(root_dir, 'data', 'xml', '*.xml')))

    n_changes = 0

    for filename in tqdm(xml_data_files):
        n_changes += handle_file(filename)

    print(f'Fixed {n_changes} metadata fields')


if __name__ == '__main__':
    main()
