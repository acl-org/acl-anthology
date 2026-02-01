#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021, 2022 Xinru Yan <xinru1414@gmail.com>
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
#
# This script ingests attchments after the pdfs have already been ingested, based on ill-formatted aclpub2 ingestion material
# where attachments and paper mapping is inferred based on the first part of the attachment name that can be mapped to `Paper ID` in the papers.yaml file
# then the corresponding attachment is ingested.
#
# Usage:
#   python bin/backfill_aclpub2_attachments.py -i ~/Dropbox/ingests/2023/01-17-emnlp/findings/output/ -v findings -c 2022.findings -vn emnlp -x data/xml/2022.findings.xml
#
#
#
import click
import glob
import os
import lxml.etree as et
from typing import Dict, List, Tuple, Optional
from ingest_aclpub2 import parse_paper_yaml, create_des_path
from ingest import maybe_copy
from anthology.utils import make_simple_element, indent, compute_hash_from_file


def find_paper_from_attachment(ingestion_dir) -> Dict[str, Tuple[str, str]]:
    """
    Iterates over the attachment folder and extracs paper's paper_id based on each attachment name.
    Return a dictionary of paper_id: attachment_path
    """
    attachment_src_dir = ingestion_dir + "attachments"
    paper_ids = dict()
    for filename in glob.glob(attachment_src_dir + "/*"):
        paper_id = os.path.splitext(os.path.split(filename)[1])[0].split("_")[0]
        attachment_type = (
            os.path.splitext(os.path.split(filename)[1])[0].split("_")[1].lower()
        )
        paper_ids[paper_id] = (filename, attachment_type)
    return paper_ids


def locate_paper(papers: List[Dict], paper_id: str) -> Optional[None]:
    for i, paper in enumerate(papers):
        if str(paper["Paper ID"]) == paper_id:
            return i + 1
    return None


def ingest_attachment(
    papers: List[Dict],
    paper_ids: Dict[str, Tuple[str, str]],
    attachments_dir: str,
    venue_name: str,
    collection_id: str,
    volume_name: str,
    xml_file: str,
):
    for paper_id, (attachment_src_path, attachment_type) in paper_ids.items():
        attchs_dest_dir = create_des_path(attachments_dir, venue_name)
        _, attch_src_extension = os.path.splitext(attachment_src_path)
        paper_num = locate_paper(papers, paper_id)
        if paper_num is not None:
            file_name = f"{collection_id}-{volume_name}.{paper_num}.{attachment_type}{attch_src_extension}"
            attch_dest_path = os.path.join(attchs_dest_dir, file_name)
            maybe_copy(attachment_src_path, attch_dest_path)
            tree = et.parse(xml_file)
            root = tree.getroot()
            for volume in root.iter("volume"):
                if volume.attrib.get("id") == volume_name:
                    for paper in volume.iter("paper"):
                        if paper.find("url").text.split("-")[1].split(".")[1] == str(
                            paper_num
                        ):
                            make_simple_element(
                                "attachment",
                                text=os.path.basename(attch_dest_path),
                                attrib={
                                    "type": attachment_type,
                                    "hash": compute_hash_from_file(attch_dest_path),
                                },
                                parent=paper,
                            )
            indent(root)
            tree.write(xml_file, encoding="UTF-8", xml_declaration=True, with_tail=True)
        else:
            print(f"Can not find paper with paper id {paper_id}.")


@click.command()
@click.option(
    "-i",
    "--ingestion_dir",
    help="Directory contains proceedings need to be ingested",
)
@click.option(
    "-a",
    "--attachments_dir",
    default=os.path.join(os.environ["HOME"], "anthology-files", "attachments"),
    help="Root path for placement of attachment files",
)
@click.option(
    "-v",
    "--venue",
    default="emnlp",
    help="venue name",
)
@click.option(
    "-c",
    "--collection_id",
    default="2022.emnlp",
    help="venue name",
)
@click.option(
    "-vn",
    "--volume_name",
    default="main",
    help="volume name",
)
@click.option(
    "-x",
    "--xml_file",
    default="data/xml/2022.emnlp.xml",
    help="xml file",
)
def main(ingestion_dir, attachments_dir, venue, collection_id, volume_name, xml_file):
    papers = parse_paper_yaml(ingestion_dir)
    paper_ids = find_paper_from_attachment(ingestion_dir)
    ingest_attachment(
        papers, paper_ids, attachments_dir, venue, collection_id, volume_name, xml_file
    )


if __name__ == "__main__":
    main()
