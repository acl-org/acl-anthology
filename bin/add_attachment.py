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

"""Used to add an attachment as an additional attachment to the Anthology.

This script is heavily adopted from add_attachments.py
Only adding attachment without reading in .csv file and keeping a log

Usage:

    add_attachment.py anth_id attachment_URL 'ATTACHMENT_TYPE'
"""

import argparse
import filetype
import os
import shutil
import sys
import tempfile

from pathlib import Path

from acl_anthology import Anthology
from acl_anthology.files import AttachmentReference, FileReference
from acl_anthology.utils.ids import parse_id

ALLOWED_TYPES = ["pdf", "pptx", "zip"]
ATTACHMENT_TYPES = "Poster Presentation Note Software Supplementary Dataset".split()


def add_attachment(anthology, anthology_id, path, attach_type, overwrite=False):
    """
    Adds a single attachment to the Anthology data files.

    Arguments:
    - The Anthology object.
    - The ACL ID of the paper (e.g., P17-1012)
    - The path to the attachment (can be a URL)
    - The attachment type (poster, presentation, note, software)
    - Whether to overwrite the downloaded file.
    """

    collection_id, _, _ = parse_id(anthology_id)

    paper = anthology.get_paper(anthology_id)
    if paper is None:
        print(f"Paper {anthology_id} not found in the Anthology", file=sys.stderr)
        return None

    if path.startswith("http"):
        _, input_file_path = tempfile.mkstemp()
        input_file_path = Path(input_file_path)
        print(f"-> Downloading file from {path} to {input_file_path}", file=sys.stderr)
        FileReference(name=path).download(input_file_path)
    else:
        input_file_path = Path(path)

    file_extension = path.replace("?dl=1", "").split(".")[-1]
    # Many links from file sharing services are not informative and don't have
    # extensions, so we could try to guess.
    if file_extension not in ALLOWED_TYPES:
        detected = filetype.guess(str(input_file_path))
        if detected is not None:
            file_extension = detected.mime.split("/")[-1]
            if file_extension not in ALLOWED_TYPES:
                print(
                    f"Could not determine file extension for {anthology_id} at {path}",
                    file=sys.stderr,
                )

    attachment_file_name = f"{anthology_id}.{attach_type}.{file_extension}"

    # Make sure directory exists
    output_dir = Path(args.attachment_root) / collection_id[0] / collection_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy file
    dest_path = output_dir / attachment_file_name
    if dest_path.exists() and not overwrite:
        print(
            f"-> target file {dest_path} already in place, refusing to overwrite",
            file=sys.stderr,
        )
    else:
        shutil.copy(input_file_path, dest_path)
        os.chmod(dest_path, 0o644)
        print(
            f"-> copied {input_file_path} to {dest_path} and fixed perms",
            file=sys.stderr,
        )

    # Update XML via the library
    if any(ref.name == attachment_file_name for _, ref in paper.attachments):
        print(
            f"-> attachment {attachment_file_name} already exists in the XML",
            file=sys.stderr,
        )
    else:
        reference = AttachmentReference.from_file(dest_path)
        paper.attachments += ((attach_type.lower(), reference),)
        paper.collection.save()
        print(
            f"-> added attachment {attachment_file_name} to the XML",
            file=sys.stderr,
        )

    # Clean up
    if path.startswith("http"):
        os.remove(input_file_path)

    return dest_path


def main(args):
    anthology = Anthology.from_within_repo()
    add_attachment(
        anthology, args.anthology_id, args.path, args.attach_type, overwrite=False
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "anthology_id", help="The Anthology paper ID to revise (e.g., P18-1001)"
    )
    parser.add_argument("path", type=str, help="Path to the attachment (can be URL)")
    parser.add_argument(
        "attach_type", type=str, default="Supplementary", help="attachment type"
    )

    parser.add_argument(
        "--attachment-root",
        default=os.path.join(
            os.environ.get(
                "ANTHOLOGY_FILES",
                os.path.join(os.environ["HOME"], "anthology-files"),
            ),
            "attachments",
        ),
        help="Anthology web directory root.",
    )
    args = parser.parse_args()

    main(args)
