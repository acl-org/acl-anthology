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
Used to add attachments to the Anthology.
Usage:

  add_attachment.py paper_id URL_OR_PATH TYPE

- The ACL ID of the paper (e.g., P17-1012)
- The path to the attachment (can be a URL)
- The attachment type (poster, presentation, note, software)

Puts the file in place and modifies the XML.
"""

import argparse
import os
import shutil
import ssl
import sys
import tempfile

from anthology.utils import build_anthology_id, deconstruct_anthology_id

import lxml.etree as ET
import urllib.request

def main(args):

    print(f'Processing attachment for {args.anthology_id}', file=sys.stderr)

    if args.path.startswith('http'):
        _, input_file_path = tempfile.mkstemp()
        try:
            print('-> Downloading file from {}'.format(args.path), file=sys.stderr)
            with urllib.request.urlopen(args.path) as url, open(input_file_path, mode='wb') as input_file_fh:
                input_file_fh.write(url.read())
        except ssl.SSLError:
            print('-> FATAL: An SSL error was encountered in downloading the files.', file=sys.stderr)
            sys.exit(1)
    else:
        input_file_path = args.path

    collection_id, volume_id, paper_id = deconstruct_anthology_id(args.anthology_id)
    paper_extension = args.path.split('.')[-1]

    if paper_extension not in ['pdf', 'pptx']:
        print('-> FATAL: unknown file extension {paper_extension}', file=sys.stderr)
        sys.exit(1)

    attachment_file_name = f'{args.anthology_id}.{args.type.capitalize()}.{paper_extension}'

    # Update XML
    xml_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'data', 'xml', f'{collection_id}.xml')
    tree = ET.parse(xml_file)
    # add newline to end-of-file if not present
    if not tree.getroot().tail: tree.getroot().tail = '\n'
    paper = tree.getroot().find(f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']")
    if paper is not None:
        # Check if attachment already exists
        for attachment in paper.findall('attachment'):
            if attachment.text == attachment_file_name:
                print(f'-> attachment {attachment_file_name} already exists in the XML', file=sys.stderr)
                break
        else:
            attachment = ET.Element('attachment')
            attachment.attrib['type'] = args.type
            attachment.text = attachment_file_name

            # Set tails to maintain proper indentation
            paper[-1].tail += '  '
            attachment.tail = '\n    '  # newline and two levels of indent

            paper.append(attachment)
            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            print(f'-> added attachment {attachment_file_name} to the XML', file=sys.stderr)

    else:
        print(f'-> FATAL: paper not found in the Anthology', file=sys.stderr)
        sys.exit(1)

    # Make sure directory exists
    output_dir = os.path.join(args.attachment_root, collection_id[0], collection_id)
    if not os.path.exists(output_dir):
        print(f'-> Creating directory {output_dir}', file=sys.stderr)
        os.makedirs(output_dir)

    # Copy file
    dest_path = os.path.join(output_dir, attachment_file_name)
    if os.path.exists(dest_path):
        print(f'-> target file {dest_path} already in place, refusing to overwrite', file=sys.stderr)
    else:
        shutil.copy(input_file_path, dest_path)
        os.chmod(dest_path, 0o644)
        print(f'-> copied {input_file_path} to {dest_path} and fixed perms', file=sys.stderr)

    # Clean up
    if args.path.startswith('http'):
        os.remove(input_file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('anthology_id', help='The Anthology ID (e.g., P18-1001)')
    parser.add_argument('path', type=str, help='Path to the attachment (can be URL)')
    parser.add_argument('type', type=str, choices='poster presentation note software supplementary'.split(), help='Attachment type')
    parser.add_argument('--attachment-root', '-d', default=os.path.join(os.environ['HOME'], 'anthology-files/attachments'),
                        help='Anthology web directory root.')
    args = parser.parse_args()

    main(args)
