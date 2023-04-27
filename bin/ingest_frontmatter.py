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
# Quick fix script, should be combined with ingest_aclpub2.py!
# Usage:
#   python bin/ingest_frontmatter.py
#
#
#
import os
import sys
import click
import lxml.etree as ET
from ingest_aclpub2 import create_des_path, parse_conf_yaml
from ingest import maybe_copy
from anthology.utils import compute_hash_from_file
from anthology.venues import VenueIndex
from typing import Dict, Tuple, Any


def copy_front_matter(
    meta: Dict[str, Any],
    pdfs_dir: str,
    dry_run: bool,
) -> Tuple[Dict[str, Dict[str, str]], str, str, str]:
    collection_id = meta['collection_id']
    venue_name = meta['anthology_venue_id'].lower()
    volume_name = meta['volume'].lower()

    pdfs_dest_dir = create_des_path(pdfs_dir, venue_name)

    # copy frontmatter (0.pdf)
    frontmatter_pdf_src_path = os.path.join(meta['path'], 'watermarked_pdfs/0.pdf')
    assert os.path.exists(frontmatter_pdf_src_path), 'frontmatter was not found'
    frontmatter_pdf_dest_path = (
        os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}") + ".0.pdf"
    )
    if dry_run:
        print(
            f'would\'ve moved {frontmatter_pdf_src_path} to {frontmatter_pdf_dest_path}'
        )
    if not dry_run:
        maybe_copy(frontmatter_pdf_src_path, frontmatter_pdf_dest_path)

    return frontmatter_pdf_dest_path


def update_frontmatter_hash(
    anthology_dir, collection_id, volume_name, frontmatter_pdf_dest_path
):
    xml_file = os.path.join(anthology_dir, 'data', 'xml', f'{collection_id}.xml')
    tree = ET.parse(xml_file)
    paper = tree.getroot().find(f"./volume[@id='{volume_name}']/frontmatter")
    url = paper.find("./url")
    print(f'old hash {url.attrib["hash"]}')
    url.attrib["hash"] = compute_hash_from_file(frontmatter_pdf_dest_path)
    print(f'new hash {url.attrib["hash"]}')
    tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


@click.command()
@click.option(
    '-i',
    '--ingestion_dir',
    help='Directory contains proceedings need to be ingested',
)
@click.option(
    '-p',
    '--pdfs_dir',
    default=os.path.join(os.environ['HOME'], 'anthology-files', 'pdf'),
    help='Root path for placement of PDF files',
)
@click.option(
    '-n',
    '--dry_run',
    default=False,
    help='Do not actually copy anything',
)
@click.option(
    '-r',
    '--anthology_dir',
    default=os.path.join(os.path.dirname(sys.argv[0]), ".."),
    help='Root path of ACL Anthology Github repo.',
)
def main(ingestion_dir, pdfs_dir, dry_run, anthology_dir):
    anthology_datadir = os.path.join(os.path.dirname(sys.argv[0]), "..", "data")
    venue_index = VenueIndex(srcdir=anthology_datadir)
    [venue["slug"].lower() for _, venue in venue_index.items()]

    meta = parse_conf_yaml(ingestion_dir)
    venue_abbrev = meta["anthology_venue_id"]
    venue_slug = venue_index.get_slug_from_acronym(venue_abbrev)

    meta["path"] = ingestion_dir
    meta["collection_id"] = collection_id = meta["year"] + "." + venue_slug

    volume_name = meta["volume"].lower()
    print(f'collection_id {collection_id}, venuename {volume_name}')
    # volume_full_id = f"{collection_id}-{volume_name}"

    frontmatter_pdf_dest_path = copy_front_matter(meta, pdfs_dir, dry_run)
    update_frontmatter_hash(
        anthology_dir, collection_id, volume_name, frontmatter_pdf_dest_path
    )


if __name__ == '__main__':
    main()
