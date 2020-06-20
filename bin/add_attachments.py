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

"""Used to add attachments to the Anthology.
Usage:

    add_attachments.py CSV_FILE

Where CSV_FILE is output from the Microsoft form (https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAMAABqTSThUN0I2VEdZMTk4Sks3S042MVkxUEZQUVdOUS4u) we use to collect attachments, and has the following headers:

    ID,Start time,Completion time,Email,Name,Anthology ID,URL where we can download the attachment,Attachment type,"For corrections or errata, please explain in detailed prose what has changed.",Your name,Your email address,I agree to the Anthology's CC-BY-4.0 distribution license.

Downloads the files, edits the XML, and dumps a log to
add_attachments.log, along with emails to be sent to those whose
imports failed.
"""

import argparse
import csv
import filetype
import os
import shutil
import ssl
import sys
import tempfile

from anthology.utils import (
    build_anthology_id,
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
    attachments = {}
    with open(args.csv_file) as csv_file:
        for row in csv.DictReader(csv_file):
            # ID,Start time,Completion time,Email,Name,Anthology ID,URL where we can download the attachment,Attachment type,"For corrections or errata, please explain in detailed prose what has changed.",Your name,Your email address,I agree to the Anthology's CC-BY-4.0 distribution license
            anthology_id = row["Anthology ID"].strip()
            download_path = row["URL"]
            attachment_type = row["Attachment type"]
            submitter_name = row["Your name"]
            submitter_email = row["Your email address"]
            submitted = row["Completion time"]

            if attachment_type not in ATTACHMENT_TYPES:
                print(
                    f"{anthology_id}: Skipping unknown type {attachment_type}: {download_path}",
                    file=sys.stderr,
                )
                continue

            if anthology_id in attachments:
                print(
                    f"{anthology_id}: Received multiple entries, only processing the last one ({attachment_type}): {download_path}",
                    file=sys.stderr,
                )

            attachments[anthology_id] = (
                download_path,
                attachment_type,
                submitter_name,
                submitter_email,
                submitted,
            )

    succeeded = 0
    failed = 0
    with open(args.logfile, "a") as log:
        for anthology_id, (path, attach_type, name, email, date) in attachments.items():
            try:
                print(f"Processing attachment for {anthology_id}", file=sys.stderr)
                success = add_attachment(
                    anthology_id, path, attach_type, overwrite=args.overwrite
                )
                if success:
                    succeeded += 1
                    print(f"{anthology_id}: SUCCESS.", file=log)
                else:
                    print(f"{anthology_id}: ALREADY DONE (use -o to redo).", file=log)
            except Exception as reason:
                failed += 1
                print(f"{anthology_id}: FAILURE", file=log)
                with open(f"{args.logfile}.{anthology_id}.txt", "w") as email_log:
                    print(
                        f"{email}\n"
                        f"ACL Anthology: failed to add attachment for {anthology_id}\n"
                        f"Dear {name},\n"
                        f"\n"
                        f"On {date} you submitted the following attachment to the ACL Anthology\n"
                        f"\n"
                        f"  paper ID: {anthology_id}\n"
                        f"      link: {path}\n"
                        f"\n"
                        f"Adding this attachment failed. The reason reported was:\n"
                        f"\n"
                        f"  {reason}\n"
                        f"\n"
                        f"To resubmit, follow the instructions here:\n"
                        f"\n"
                        f"  https://www.aclweb.org/anthology/info/corrections/\n",
                        f"\n"
                        f"There is no need to respond to this email.\n"
                        f"\n"
                        f"Sincerely,\n"
                        f"Matt Post\n"
                        f"Anthology Director\n",
                        file=email_log,
                    )

    print(
        f"Processed {len(attachments)} attachments ({succeeded} succeeded, {failed} failed)."
    )
    print(f"Wrote logfile to {args.logfile}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", help="The CSV file from the Microsoft form")
    parser.add_argument(
        "--overwrite", "-o", action="store_true", help="Overwrite attachments"
    )
    parser.add_argument(
        "--logfile", "-l", default="add_attachments.log", help="Logfile to write to"
    )
    parser.add_argument(
        "--attachment-root",
        "-d",
        default=os.path.join(os.environ["HOME"], "anthology-files/attachments"),
        help="Anthology web directory root.",
    )
    args = parser.parse_args()

    main(args)
