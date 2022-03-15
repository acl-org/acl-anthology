#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2022 Xinru Yan <xinru1414@gmail.com>
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

import os
import click
import logging as log
from enum import Enum
from functools import partial

from anthology import Anthology
from anthology.utils import upload_file_to_queue
from anthology.utils import SeverityTracker
from anthology.data import (
    ANTHOLOGY_ATTACHMENTS_DIR,
    ANTHOLOGY_DATA_DIR,
    ANTHOLOGY_PDF_DIR,
    ResourceType,
)


# Enable show default by default
click.option = partial(click.option, show_default=True)


def get_proceedings_id_from_filename(resource_type: ResourceType, filename: str) -> str:
    trailing_dots = {ResourceType.PDF: 1, ResourceType.ATTACHMENT: 2}[resource_type]
    return filename.rsplit('.', trailing_dots)[0]


def get_hash_for_resource(
    anth: Anthology, resource_type: ResourceType, filename: str
) -> str:
    proceedings_id = get_proceedings_id_from_filename(resource_type, filename)
    if proceedings_id not in anth.papers and proceedings_id not in anth.volumes:
        raise Exception(f"Paper/Volume for PDF {proceedings_id!r} does not exist.")

    resource_hash = None
    if resource_type == ResourceType.PDF:
        resource_hash = anth.papers.get(
            proceedings_id, anth.volumes.get(proceedings_id)
        ).pdf_hash
    elif resource_type == ResourceType.ATTACHMENT:
        attachments = anth.papers[proceedings_id].attachments
        filename_to_hash = {a['filename']: a['hash'] for a in attachments}
        resource_hash = filename_to_hash.get(filename)

    if resource_hash is None:
        raise Exception(
            "Hash for resource is None. Please update with value before running this script."
        )

    return resource_hash


# Iterate over files in resource directory, find the hash in the Anthology and upload the file (if commit)
def enqueue_dir(
    anth: Anthology,
    resource_directory: str,
    resource_type: ResourceType,
    commit: bool = False,
):
    for venue_name in os.listdir(resource_directory):
        for filename in os.listdir(os.path.join(resource_directory, venue_name)):
            local_path = os.path.join(resource_directory, venue_name, filename)

            # Get resource hash
            try:
                resource_hash = get_hash_for_resource(anth, resource_type, filename)
            except Exception as e:
                log.error(f"{e} (filename: {local_path!r})", exc_info=True)
                continue

            upload_file_to_queue(
                local_path,
                resource_type=resource_type,
                venue_name=venue_name,
                filename=filename,
                file_hash=resource_hash,
                commit=commit,
            )


@click.command()
@click.option(
    '-i',
    '--importdir',
    type=click.Path(exists=True),
    default=ANTHOLOGY_DATA_DIR,
    help="Directory to import the Anthology XML files data files from.",
)
@click.option(
    '-p',
    '--pdfs-dir',
    type=click.Path(exists=True),
    default=ANTHOLOGY_PDF_DIR,
    help="Root path for placement of PDF files",
)
@click.option(
    '-a',
    '--attachments-dir',
    type=click.Path(exists=True),
    default=ANTHOLOGY_ATTACHMENTS_DIR,
    help="Root path for placement of PDF files",
)
@click.option(
    '-c',
    '--commit',
    is_flag=True,
    help="Commit (=write) the changes to the anthology server; will only do a dry run otherwise.",
)
@click.option('--debug', is_flag=True, help="Output debug-level log messages.")
def main(importdir, pdfs_dir, attachments_dir, commit, debug):
    log_level = log.DEBUG if debug else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    log.info("Instantiating the Anthology...")
    anth = Anthology(importdir=importdir)

    log.info("Enqueuing PDFs...")
    enqueue_dir(anth, pdfs_dir, ResourceType.PDF, commit)

    log.info("Enqueuing Attachments...")
    enqueue_dir(anth, attachments_dir, ResourceType.ATTACHMENT, commit)

    if not commit:
        if tracker.highest >= log.ERROR:
            log.warning(
                "There were errors! Please check them carefully before re-running this script with -c/--commit."
            )
        else:
            log.warning(
                "Re-run this script with -c/--commit to upload these files to the server."
            )

    if tracker.highest >= log.ERROR:
        exit(1)


if __name__ == "__main__":
    main()
