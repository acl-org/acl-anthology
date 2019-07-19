#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Matt Post <post@cs.jhu.edu>
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

"""
Used to add revisions to the Anthology.
Assumes all files have a base format like ANTHOLOGY_ROOT/P/P18/P18-1234.pdf format.
The revision process is as follows.

- The original paper is named as above.
- When a first revision is created, the original paper is archived to PYY-XXXXv1.pdf.
- The new revision is copied to PYY-XXXXvN, where N is the next revision ID (usually 2).
  The new revision is also copied to PYY-XXXX.pdf.
  This causes it to be returned by the anthology when the base paper format is queried.

Usage:

  add_revision.py paper_id URL_OR_PATH.pdf "Short explanation".

By default, a dry run happens.
When you are ready, add `--do`.

TODO: add the <revision> tag to the XML automatically.
(The script has all the info it needs).
"""

import argparse
import os
import shutil
import ssl
import sys
import tempfile

from anthology.utils import deconstruct_anthology_id, indent
from anthology.data import ANTHOLOGY_URL

import lxml.etree as ET
import urllib.request


def maybe_copy(file_from, file_to, do=False):
    if do:
        print('-> Copying from {} -> {}'.format(file_from, file_to), file=sys.stderr)
        shutil.copy(file_from, file_to)
        os.chmod(file_to, 0o644)
    else:
        print('-> DRY RUN: Copying from {} -> {}'.format(file_from, file_to), file=sys.stderr)


def main(args):

    change_type = 'erratum' if args.erratum else 'revision'
    change_letter = 'e' if args.erratum else 'v'

    print(f'Processing {change_type} to {args.anthology_id}...')

    # TODO: make sure path exists, or download URL to temp file
    if args.path.startswith('http'):
        _, input_file_path = tempfile.mkstemp()
        try:
            print(f'-> Downloading file from {args.path}', file=sys.stderr)
            with urllib.request.urlopen(args.path) as url, open(input_file_path, mode='wb') as input_file_fh:
                input_file_fh.write(url.read())
        except ssl.SSLError:
            print('An SSL error was encountered in downloading the files.', file=sys.stderr)
            sys.exit(1)
    else:
        input_file_path = args.path

    collection_id, volume_id, paper_id = deconstruct_anthology_id(args.anthology_id)
    paper_extension = args.path.split('.')[-1]

    # The new version
    revno = None

    # Update XML
    xml_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'data', 'xml', f'{collection_id}.xml')
    tree = ET.parse(xml_file)
    paper = tree.getroot().find(f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']")
    if paper is not None:
        revisions = paper.findall(change_type)
        revno = 1 if args.erratum else 2
        for revision in revisions:
            revno = int(revision.attrib['id']) + 1

        if args.do:
            revision = ET.Element(change_type)
            revision.attrib['id'] = str(revno)
            revision.attrib['href'] = f'{args.anthology_id}{change_letter}{revno}'
            revision.text = args.explanation

            # Set tails to maintain proper indentation
            paper[-1].tail += '  '
            revision.tail = '\n    '  # newline and two levels of indent

            paper.append(revision)

            indent(tree.getroot())

            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            print(f'-> Added {change_type} node "{revision.text}" to XML', file=sys.stderr)

    else:
        print(f'-> FATAL: paper ID {args.anthology_id} not found in the Anthology', file=sys.stderr)
        sys.exit(1)

    output_dir = os.path.join(args.anthology_dir, 'pdf', collection_id[0], collection_id)

    # Make sure directory exists
    if not os.path.exists(output_dir):
        print(f'-> Creating directory {output_dir}', file=sys.stderr)
        os.makedirs(output_dir)

    canonical_path = os.path.join(output_dir, f'{args.anthology_id}.pdf')

    if not args.erratum and revno == 2:
        # There are no versioned files the first time around, so create the first one
        # (essentially backing up the original version)
        revised_file_v1_path = os.path.join(output_dir, f'{args.anthology_id}{change_letter}1.pdf')

        current_version = ANTHOLOGY_URL.format(args.anthology_id)
        if args.do:
            try:
                print(f'-> Downloading file from {args.path} to {revised_file_v1_path}', file=sys.stderr)
                with urllib.request.urlopen(current_version) as url, open(revised_file_v1_path, mode='wb') as fh:
                    fh.write(url.read())
            except ssl.SSLError:
                print(f'-> FATAL: An SSL error was encountered in downloading {args.path}.', file=sys.stderr)
                sys.exit(1)
        else:
            print(f'-> DRY RUN: Downlading file from {args.path} to {revised_file_v1_path}', file=sys.stderr)


    revised_file_versioned_path = os.path.join(output_dir, f'{args.anthology_id}{change_letter}{revno}.pdf')

    maybe_copy(input_file_path, revised_file_versioned_path, args.do)
    maybe_copy(input_file_path, canonical_path, args.do)

    if args.path.startswith('http'):
        os.remove(input_file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('anthology_id', help='The Anthology paper ID to revise (e.g., P18-1001)')
    parser.add_argument('path', type=str, help='Path to the revised paper ID (can be URL)')
    parser.add_argument('explanation', help='Brief description of the changes.')
    parser.add_argument('--erratum', '-e', action='store_true', help='This is an erratum instead of a revision.')
    parser.add_argument('--do', '-x', action='store_true', default=False, help='Actually do the copying')
    parser.add_argument('--anthology-dir', default=os.path.join(os.environ['HOME'], 'anthology-files'),
                        help='Anthology web directory root.')
    args = parser.parse_args()

    main(args)
