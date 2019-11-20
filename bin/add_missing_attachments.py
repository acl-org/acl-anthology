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
One-time script used to add missing attachments to the XML.

Collect files:

    find attachments -type f > missing.txt

Process:

    cat missing.txt | python3 add_missing_attachments.py
"""

import argparse
import os
import shutil
import ssl
import sys
import tempfile

from anthology.utils import build_anthology_id, deconstruct_anthology_id, indent

import lxml.etree as ET
import urllib.request

ALLOWED_TYPES = ["pdf", "pptx", "zip"]
ATTACHMENT_TYPES = "Poster Presentation Note Software Supplementary".split()


def main(args):

    for lineno, line in enumerate(sys.stdin, 1):
        # attachments/D/D15/D15-1272.Attachment.pdf
        tokens = line.rstrip().split("/")
        attachment_file_name = tokens[-1]
        try:
            anth_id, kind, *rest = attachment_file_name.split(".")
        except:
            print(f"Couldn't parse file {attachment_file_name} into 3 pieces")
            continue

        try:
            collection_id, volume_id, paper_id = deconstruct_anthology_id(anth_id)
        except:
            print(f"[{lineno}] BAD LINE {line.rstrip()}")

        # Update XML
        xml_file = os.path.join(
            os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{collection_id}.xml"
        )
        tree = ET.parse(xml_file)

        if int(paper_id) == 0:
            paper = tree.getroot().find(f"./volume[@id='{volume_id}']/frontmatter")
        else:
            paper = tree.getroot().find(
                f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']"
            )
        if paper is not None:
            # Check if attachment already exists
            for attachment in paper.findall("attachment"):
                if attachment.text == attachment_file_name:
                    #                    print(f'-> attachment {attachment_file_name} already exists in the XML', file=sys.stderr)
                    break
            else:
                attachment = ET.Element("attachment")
                attachment.attrib["type"] = kind.lower()
                attachment.text = attachment_file_name

                paper.append(attachment)
                indent(tree.getroot())
                tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
                print(
                    f"-> [{lineno}] added attachment {attachment_file_name} to the XML",
                    file=sys.stderr,
                )

        else:
            print(
                f"-> FATAL: [{lineno}] paper ({anth_id}) not found in the Anthology",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    main(args)
