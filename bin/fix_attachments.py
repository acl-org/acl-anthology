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
One-time script used to remove duplicate attachments from the Anthology.
May be useful for salvaging in the future.

    python3 fix_attachments ../data/xml/*.xml
"""

import argparse
import os
import shutil
import ssl
import sys
import tempfile

from anthology.utils import indent

import lxml.etree as ET
import urllib.request


def main(args):

    for xml_file in args.files:
        # Update XML
        tree = ET.parse(xml_file)
        tree.getroot().tail = "\n"

        for paper in tree.getroot().findall(".//paper"):
            tail = paper.tail
            seen = []
            for attachment in paper.findall("./attachment"):
                if attachment.text in seen:
                    print(f"Removing: {attachment.text}")
                    paper.remove(attachment)
                seen.append(attachment.text)

            indent(paper, level=2)
            paper.tail = tail

        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    main(args)
