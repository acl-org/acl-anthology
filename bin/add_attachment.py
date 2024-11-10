#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 Xinru Yan <xinru1414@gmail.com>
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

"""Used to add attachment revision as an additional attachament to the Anthology.

This script is heavily adopted from add_attachments.py
Only adding attachment without reading in .csv file and keeping a log

Usage:

    add_attachment.py anth_id attachment_revision_URL 'ATTACHMENT_TYPE'
"""

import argparse
import filetype
import os
import shutil
import ssl
import sys
import tempfile

from anthology.utils import (
    deconstruct_anthology_id,
    indent,
    compute_hash,
)

import lxml.etree as ET
import urllib.request

ALLOWED_TYPES = ["pdf", "pptx", "zip"]
ATTACHMENT_TYPES = "Poster Presentation Note Software Supplementary Dataset".split()


def add_attachment(anthology_id, path, attach_type, overwrite=False):
    """
    Adds a single attachment to the Anthology data files.

    Arguments:
    - The ACL ID of the paper (e.g., P17-1012)
    - The path to the attachment (can be a URL)
    - The attachment type (poster, presentation, note, software)
    - Whether to overwrite the downloaded file.
    """

    collection_id, volume_id, paper_id = deconstruct_anthology_id(anthology_id)

    if path.startswith("http"):
        _, input_file_path = tempfile.mkstemp()
        try:
            print(
                f"-> Downloading file from {path} to {input_file_path}", file=sys.stderr
            )
            request = urllib.request.Request(path, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request) as url, open(
                input_file_path, mode="wb"
            ) as input_file_fh:
                input_file_fh.write(url.read())
        except ssl.SSLError:
            raise Exception(f"Could not download {path}")
        except Exception as e:
            raise e
    else:
        input_file_path = path

    file_extension = path.replace("?dl=1", "").split(".")[-1]
    # Many links from file sharing services are not informative and don't have
    # extensions, so we could try to guess.
    if file_extension not in ALLOWED_TYPES:
        detected = filetype.guess(input_file_path)
        if detected is not None:
            file_extension = detected.mime.split("/")[-1]
            if file_extension not in ALLOWED_TYPES:
                print(
                    f"Could not determine file extension for {anthology_id} at {path}",
                    file=sys.stderr,
                )

    with open(input_file_path, "rb") as f:
        checksum = compute_hash(f.read())

    # Update XML
    xml_file = os.path.join(
        os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{collection_id}.xml"
    )
    tree = ET.parse(xml_file)

    attachment_file_name = f"{anthology_id}.{attach_type}.{file_extension}"

    paper = tree.getroot().find(f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']")
    if paper is not None:
        # Check if attachment already exists
        for attachment in paper.findall("attachment"):
            if attachment.text == attachment_file_name:
                print(
                    f"-> attachment {attachment_file_name} already exists in the XML",
                    file=sys.stderr,
                )
                break
        else:
            attachment = ET.Element("attachment")
            attachment.attrib["type"] = attach_type.lower()
            attachment.attrib["hash"] = checksum
            attachment.text = attachment_file_name

            paper.append(attachment)
            indent(tree.getroot())
            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            print(
                f"-> added attachment {attachment_file_name} to the XML", file=sys.stderr
            )

    else:
        print(f"Paper {anthology_id} not found in the Anthology", file=sys.stderr)

    # Make sure directory exists
    output_dir = os.path.join(args.attachment_root, collection_id[0], collection_id)
    if not os.path.exists(output_dir):
        #        print(f"-> Creating directory {output_dir}", file=sys.stderr)
        os.makedirs(output_dir)

    # Copy file
    dest_path = os.path.join(output_dir, attachment_file_name)
    if os.path.exists(dest_path) and not overwrite:
        print(
            f"-> target file {dest_path} already in place, refusing to overwrite",
            file=sys.stderr,
        )
        return None

    shutil.copy(input_file_path, dest_path)
    os.chmod(dest_path, 0o644)
    print(f"-> copied {input_file_path} to {dest_path} and fixed perms", file=sys.stderr)

    # Clean up
    if path.startswith("http"):
        os.remove(input_file_path)

    return dest_path


def main(args):
    add_attachment(args.anthology_id, args.path, args.attach_type, overwrite=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "anthology_id", help="The Anthology paper ID to revise (e.g., P18-1001)"
    )
    parser.add_argument(
        "path", type=str, help="Path to the revised attachment ID (can be URL)"
    )
    parser.add_argument(
        "attach_type", type=str, default='Supplementary', help="attachment type"
    )

    parser.add_argument(
        "--attachment-root",
        default=os.path.join(os.environ["HOME"], "anthology-files/attachments"),
        help="Anthology web directory root.",
    )
    args = parser.parse_args()

    main(args)
