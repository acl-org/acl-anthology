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

"""Adds missing <url> HTML tags to abstracts. Also fixes URLs that incorrectly have spaces within them

Usage: python3 fix_abstract_urls.py --mode {fix_spaces,fix_tags}
"""
import argparse
import glob
import os
import re

from tqdm import tqdm

tld_regex = r'[a-zA-Z]+'
# regex to capture valid urls (ensure it starts with a bracket or a space to avoid joined-together URLS)
# e.g. http://web.archive.org/web/20230924000431/http://www.google.com
url_domain = rf'(?<=[ ([:“,])(?:https?|ftp)://[-a-zA-Z0-9@:%._+~#=]+\.(?:{tld_regex})'
url_path = r'\b(?:[-a-zA-Z0-9@:%_+.~#?&/=]*[-a-zA-Z0-9@:%_+~#?&/=])?'
# regex for URL that is not between <url> tags
url_regex = re.compile(rf'{url_domain}{url_path}')

# regex to capture valid urls that are split up by spaces, being careful not to pick up any words after the URL
url_spaces_domain = rf'(?:https?|ftp)://(?: ?[-a-zA-Z0-9@:%_+~#=]+\.)+ ?(?:{tld_regex})'
url_spaces_path = (
    r'\b(?: [-a-zA-Z0-9@:%._+~#=&?]*/|[-a-zA-Z0-9@:%._+~#=&?/]*)*[-a-zA-Z0-9@:%_+~#=&?/]'
)

url_spaces_regex_str = rf'{url_spaces_domain}{url_spaces_path}'
url_spaces_regex = re.compile(url_spaces_regex_str)


def fix_abstract_url_tags(text):
    url_begin_tag = '<url>'
    url_end_tag = '</url>'

    addtl_chars = 0

    for match in url_regex.finditer(text):
        match_start, match_end = match.span()
        match_start += addtl_chars
        match_end += addtl_chars

        potential_opening_tag = text[match_start - len(url_begin_tag) : match_start]
        potential_closing_tag = text[match_end : match_end + len(url_end_tag)]

        opening_tag_is_url = potential_opening_tag == url_begin_tag
        closing_tag_is_url = potential_closing_tag == url_end_tag

        if opening_tag_is_url and closing_tag_is_url:
            # already has tags
            continue
        else:
            assert not opening_tag_is_url and not closing_tag_is_url, (
                match.group(),
                opening_tag_is_url,
                closing_tag_is_url,
                text,
            )
            text = (
                text[:match_start]
                + url_begin_tag
                + match.group()
                + url_end_tag
                + text[match_end:]
            )
            addtl_chars += len(url_begin_tag) + len(url_end_tag)

    return text


def fix_abstract_url_space(text):
    # fix abstracts that have spaces in the URL
    matches = url_spaces_regex.findall(text)
    matches = [m for m in matches if ' ' in m]

    for m in matches:
        text = text.replace(m, m.replace(' ', ''))

    return text


def handle_file(filename, method_fn):
    with open(filename) as f:
        lines = f.read()
    abstracts = re.findall(r'<abstract>.*?</abstract>', lines, re.DOTALL)

    for abstract in abstracts:
        lines = lines.replace(abstract, method_fn(abstract))

    with open(filename, 'w') as f:
        f.write(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['fix_spaces', 'fix_tags'], required=True)
    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    xml_data_files = list(glob.glob(os.path.join(root_dir, 'data', 'xml', '*.xml')))

    if args.mode == 'fix_spaces':
        method_fn = fix_abstract_url_space
    else:
        method_fn = fix_abstract_url_tags

    for filename in tqdm(xml_data_files):
        handle_file(filename, method_fn)


if __name__ == '__main__':
    main()
