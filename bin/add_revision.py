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

import urllib.request

def maybe_copy(file_from, file_to, do=False):
    if do:
        print('Copying from {} -> {}'.format(file_from, file_to), file=sys.stderr)
        shutil.copy(file_from, file_to)
        os.chmod(file_to, 0644)
    else:
        print('DRY RUN: Copying from {} -> {}'.format(file_from, file_to), file=sys.stderr)

def main(args):

    # TODO: make sure path exists, or download URL to temp file
    if args.path.startswith('http'):
        _, input_file_path = tempfile.mkstemp()
        try:
            print('Downloading file from {}'.format(args.path), file=sys.stderr)
            with urllib.request.urlopen(args.path) as url, open(input_file_path, mode='wb') as input_file_fh:
                input_file_fh.write(url.read())
        except ssl.SSLError:
            print('An SSL error was encountered in downloading the files.', file=sys.stderr)
            sys.exit(1)
    else:
        input_file_path = args.path

    volume_letter, year, paper_num = [args.paper_id[0], args.paper_id[1:3], args.paper_id[4:]]
    volume_id = '{}{}'.format(volume_letter, year)

    file_prefix = os.path.join(args.anthology_dir, volume_letter, volume_id, args.paper_id)
    output_dir = os.path.dirname(file_prefix)

    # Sanity checks
    if not os.path.exists(output_dir):
        print('No such directory "{}"'.format(output_dir), file=sys.stderr)
        sys.exit(1)

    # Look for existing versions (looking for pattern {paper_id}{letter}{num})
    letter = 'e' if args.erratum else 'v'

    existing_revisions = list(filter(lambda f: f.startswith('{}{}'.format(args.paper_id, letter)), os.listdir(output_dir)))
    new_version = len(existing_revisions) + 1

    revised_file_generic_path = '{}.pdf'.format(file_prefix, new_version)

    if not args.erratum and new_version == 1:
        # There are no versioned files the first time around, so create the first one
        revised_file_v1_path = '{}{}1.pdf'.format(file_prefix, letter)
        maybe_copy(revised_file_generic_path, revised_file_v1_path, args.do)
        maybe_copy(input_file_path, revised_file_generic_path, args.do)
        new_version = 2

    revised_file_versioned_path = '{}{}{}.pdf'.format(file_prefix, letter, new_version)

    maybe_copy(input_file_path, revised_file_versioned_path, args.do)

    if args.path.startswith('http'):
        os.remove(input_file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('paper_id', help='The paper ID to revise (e.g., P18-1001)')
    parser.add_argument('path', type=str, help='Path to the revised paper ID (can be URL)')
    parser.add_argument('explanation', help='Brief description of the changes.')
    parser.add_argument('--erratum', '-e', action='store_true', help='This is an erratum instead of a revision.')
    parser.add_argument('--do', '-x', action='store_true', default=False, help='Actually do the copying')
    parser.add_argument('--anthology-dir', default=os.path.join(os.environ['HOME'], 'anthology-files/pdf'),
                        help='Anthology web directory root.')
    args = parser.parse_args()

    main(args)
