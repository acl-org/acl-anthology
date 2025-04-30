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
Generates the Anthology RSS feed.
"""

import argparse
import os
import shutil
import ssl
import sys
import tempfile

from anthology import Anthology

class FeedItem:
    def __init__(title: str,
                 link: str):
        self.title = title
        self.link = link
        self.published = ''
        self.content = ''
        self.author = ''
        self.

def main(args):

    anthology = Anthology(importdir=args.importdir)

    feed = []
    for id_, volume in anthology.volumes.items():
        if volume.ingestion_date:
            feed.append(
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

    # Update XML
    xml_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'data', 'xml', f'{volume_id}.xml')
    tree = ET.parse(xml_file)
    if not tree.getroot().tail: tree.getroot().tail = '\n'
    for paper in tree.getroot().findall('paper'):
        if paper.attrib['id'] == paper_num:
            attachment = ET.Element('attachment')
            attachment.attrib['type'] = args.type
            attachment.text = file_name
            attachment.tail = '\n  '  # newline and one level of indent
            paper.append(attachment)
            print('Adding attachment node to XML', file=sys.stderr)

            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            break
    else:
        print(f'Fatal: paper ID {paper_id} not found in the Anthology', file=sys.stderr)
        sys.exit(1)

    volume_letter, year, paper_num = [args.paper_id[0], args.paper_id[1:3], args.paper_id[4:]]
    volume_id = '{}{}'.format(volume_letter, year)
    ext = args.path.split('.')[-1]

    file_name = f'{args.paper_id}.{args.type.capitalize()}.{ext}'
    output_dir = os.path.join(args.attachment_root, volume_letter, volume_id)

    # Make sure directory exists
    if not os.path.exists(output_dir):
        print('No such directory "{}"'.format(output_dir), file=sys.stderr)
        sys.exit(1)

    # Copy file
    dest_path = os.path.join(output_dir, file_name)
    maybe_copy(input_file_path, dest_path, do=True)

    # Clean up
    if args.path.startswith('http'):
        os.remove(input_file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('paper_id', help='The Antholgoy paper ID (e.g., P18-1001)')
    parser.add_argument('path', type=str, help='Path to the attachment (can be URL)')
    parser.add_argument('type', type=str, choices='poster presentation note software'.split(), help='Attachment type')
    parser.add_argument('--attachment-root', '-d', default=os.path.join(os.environ['HOME'], 'anthology-files/attachments'),
                        help='Anthology web directory root.')
    args = parser.parse_args()

    main(args)
