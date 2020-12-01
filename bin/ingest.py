#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019, 2020 Matt Post <post@cs.jhu.edu>
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

"""Ingests data into the Anthology. It takes a list of one or more
ACLPUB proceedings/ directories and does the following:

- executes some basic sanity checks
- applies normalization to names and titles (e.g, fixed-case protection)
- generates the nexted XML in the Anthology repository
- copies the PDFs and attachments into place for rsyncing to the server

Updated in March 2020, this script replaces:
- the old ingest.py (which converted the old ACLPUB flat XML format)
- anthologize.pl in ACLPUB
- anthology_xml.py in ACLPUB

"""

import argparse
import os
import re
import readline
import shutil
import sys

import lxml.etree as etree

from collections import defaultdict, OrderedDict
from datetime import datetime

from normalize_anth import normalize
from anthology.bibtex import read_bibtex
from anthology.index import AnthologyIndex
from anthology.people import PersonName
from anthology.sigs import SIGIndex
from anthology.utils import (
    make_simple_element,
    build_anthology_id,
    deconstruct_anthology_id,
    indent,
    compute_hash_from_file,
)
from anthology.venues import VenueIndex

from itertools import chain
from typing import Dict, Any

from slugify import slugify


def log(text: str, fake: bool = False):
    message = "[DRY RUN] " if fake else ""
    print(f"{message}{text}", file=sys.stderr)


def read_meta(path: str) -> Dict[str, Any]:
    meta = {"chairs": []}
    with open(path) as instream:
        for line in instream:
            key, value = line.rstrip().split(" ", maxsplit=1)
            if key.startswith("chair"):
                meta["chairs"].append(value)
            else:
                meta[key] = value
    return meta


def maybe_copy(source_path, dest_path):
    """Copies the file if it's different from the target."""
    if not os.path.exists(dest_path) or compute_hash_from_file(
        source_path
    ) != compute_hash_from_file(dest_path):
        log(f"Copying {source_path} -> {dest_path}", args.dry_run)
        shutil.copyfile(source_path, dest_path)


def bib2xml(bibfilename, anthology_id):
    """
    Moved here from ACLPUB's anthology_xml.py script.
    """

    fields = [
        'title',
        'author',
        'editor',
        'booktitle',
        'month',
        'year',
        'address',
        'publisher',
        'pages',
        'abstract',
        'url',
        'doi',
        'language',
    ]

    try:
        collection_id, volume_name, paper_no = deconstruct_anthology_id(anthology_id)
    except ValueError:
        print(f"Couldn't split {anthology_id}", file=sys.stderr)
        sys.exit(1)
    if paper_no == '':
        return  # skip the master bib file; we only process the individual files

    bibdata = read_bibtex(bibfilename)
    if len(bibdata.entries) != 1:
        log(f"more than one entry in {bibfilename}")
    bibkey, bibentry = bibdata.entries.items()[0]
    if len(bibentry.fields) == 0:
        log(f"parsing bib of paper {paper_no} failed")
        sys.exit(1)

    paper = make_simple_element("paper", attrib={"id": paper_no})
    for field in list(bibentry.fields) + list(bibentry.persons):
        if field not in fields:
            log(f"unknown field {field}")

    for field in fields:
        if field in ['author', 'editor']:
            if field in bibentry.persons:
                for person in bibentry.persons[field]:
                    first_text = ' '.join(person.bibtex_first_names)
                    last_text = ' '.join(person.prelast_names + person.last_names)
                    if person.lineage_names:
                        last_text += ', ' + ' '.join(person.lineage_names)

                    # Don't distinguish between authors that have only a first name
                    # vs. authors that have only a last name; always make it a last name.
                    if last_text.strip() in [
                        '',
                        '-',
                    ]:  # Some START users have '-' for null
                        last_text = first_text
                        first_text = ''

                    name_node = make_simple_element(field, parent=paper)
                    make_simple_element("first", first_text, parent=name_node)
                    make_simple_element("last", last_text, parent=name_node)
        else:
            if field == 'url':
                value = f"{anthology_id}"
            elif field in bibentry.fields:
                value = bibentry.fields[field]
            elif field == 'bibtype':
                value = bibentry.type
            elif field == 'bibkey':
                value = bibkey
            else:
                continue

            try:
                make_simple_element(field, text=value, parent=paper)
            except:
                print(
                    f"Couldn't process {bibfilename} for {anthology_id}", file=sys.stderr
                )
                sys.exit(2)

    return paper


def main(args):
    collections = defaultdict(OrderedDict)
    volumes = {}

    anthology_datadir = os.path.join(os.path.dirname(sys.argv[0]), "..", "data")
    venue_index = VenueIndex(srcdir=anthology_datadir)
    venue_keys = [venue["slug"].lower() for _, venue in venue_index.items()]

    sig_index = SIGIndex(srcdir=anthology_datadir)

    # Build list of volumes, confirm uniqueness
    unseen_venues = []
    for proceedings in args.proceedings:
        meta = read_meta(os.path.join(proceedings, "meta"))

        venue_abbrev = meta["abbrev"]
        venue_slug = venue_index.get_slug(venue_abbrev)

        if str(datetime.now().year) in venue_abbrev:
            print(f"Fatal: Venue assembler put year in acronym: '{venue_abbrev}'")
            sys.exit(1)

        if venue_slug not in venue_keys:
            unseen_venues.append((venue_slug, venue_abbrev, meta["title"]))

        meta["path"] = proceedings

        meta["collection_id"] = collection_id = meta["year"] + "." + venue_slug
        volume_name = meta["volume"].lower()
        volume_full_id = f"{collection_id}-{volume_name}"

        if volume_full_id in volumes:
            print("Error: ")

        collections[collection_id][volume_name] = {}
        volumes[volume_full_id] = meta

        if "sig" in meta:
            print(
                f"Add this line to {anthology_datadir}/sigs/{meta['sig'].lower()}.yaml:"
            )
            print(f"  - {meta['year']}")
            print(f"    - {volume_full_id} # {meta['booktitle']}")

    # Make sure all venues exist
    if len(unseen_venues) > 0:
        for venue in unseen_venues:
            slug, abbrev, title = venue
            print(f"Creating venue '{abbrev}' ({title})")
            venue_index.add_venue(abbrev, title)
        venue_index.dump(directory=anthology_datadir)

    # Copy over the PDFs and attachments
    for volume, meta in volumes.items():
        root_path = os.path.join(meta["path"], "cdrom")
        collection_id = meta["collection_id"]
        venue_name = meta["abbrev"].lower()
        volume_name = meta["volume"].lower()
        year = meta["year"]

        pdfs_dest_dir = os.path.join(args.pdfs_dir, venue_name)
        if not os.path.exists(pdfs_dest_dir):
            os.makedirs(pdfs_dest_dir)

        # copy the book
        book_src_filename = meta["abbrev"] + "-" + year
        book_src_path = os.path.join(root_path, book_src_filename) + ".pdf"
        book_dest_path = None
        if os.path.exists(book_src_path):
            book_dest_path = (
                os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}") + ".pdf"
            )

            if not args.dry_run:
                maybe_copy(book_src_path, book_dest_path)

        # copy the paper PDFs
        pdf_src_dir = os.path.join(root_path, "pdf")
        for pdf_file in os.listdir(pdf_src_dir):
            # Skip . files
            if os.path.basename(pdf_file).startswith("."):
                continue

            # names are {abbrev}{number}.pdf
            match = re.match(rf".*\.(\d+)\.pdf", pdf_file)

            if match is not None:
                paper_num = int(match[1])
                paper_id_full = f"{collection_id}-{volume_name}.{paper_num}"

                bib_path = os.path.join(
                    root_path,
                    "bib",
                    pdf_file.replace("/pdf", "/bib/").replace(".pdf", ".bib"),
                )

                pdf_src_path = os.path.join(pdf_src_dir, pdf_file)
                pdf_dest_path = os.path.join(
                    pdfs_dest_dir, f"{collection_id}-{volume_name}.{paper_num}.pdf"
                )
                if not args.dry_run:
                    maybe_copy(pdf_src_path, pdf_dest_path)

                collections[collection_id][volume_name][paper_num] = {
                    "anthology_id": paper_id_full,
                    "bib": bib_path,
                    "pdf": pdf_dest_path,
                    "attachments": [],
                }

        # copy the attachments
        if os.path.exists(os.path.join(root_path, "additional")):
            attachments_dest_dir = os.path.join(args.attachments_dir, venue_name)
            if not os.path.exists(attachments_dest_dir):
                os.makedirs(attachments_dest_dir)
            for attachment_file in os.listdir(os.path.join(root_path, "additional")):
                if os.path.basename(attachment_file).startswith("."):
                    continue
                attachment_file_path = os.path.join(
                    root_path, "additional", attachment_file
                )
                match = re.match(
                    rf"{year}\.{venue_name}-\w+\.(\d+)_?(\w+)\.(\w+)$", attachment_file
                )
                if match is None:
                    print(
                        f"* Warning: no attachment match for {attachment_file}",
                        file=sys.stderr,
                    )
                    sys.exit(2)

                paper_num, type_, ext = match.groups()
                paper_num = int(paper_num)

                file_name = f"{collection_id}-{volume_name}.{paper_num}.{type_}.{ext}"
                dest_path = os.path.join(attachments_dest_dir, file_name)
                if not args.dry_run and not os.path.exists(dest_path):
                    log(f"Copying {attachment_file} -> {dest_path}", args.dry_run)
                    shutil.copyfile(attachment_file_path, dest_path)

                collections[collection_id][volume_name][paper_num]["attachments"].append(
                    (dest_path, type_)
                )

    people = AnthologyIndex(None, srcdir=anthology_datadir)

    def correct_caps(person, name_node, anth_id):
        """
        Many people submit their names in "ALL CAPS" or "all lowercase".
        Correct this with heuristics.
        """
        name = name_node.text
        if name.islower() or name.isupper():
            # capitalize all parts
            corrected = " ".join(list(map(lambda x: x.capitalize(), name.split())))
            print(
                f"-> Correcting capitalization of '{name}' to '{corrected}'",
                file=sys.stderr,
            )
            name_node.text = corrected

    def disambiguate_name(node, anth_id):
        name = PersonName.from_element(node)
        ids = people.get_ids(name)

        if len(ids) > 1:
            choice = -1
            while choice < 0 or choice >= len(ids):
                print(
                    f"({anth_id}): ambiguous author {name}; Please choose from the following:"
                )
                for i, id_ in enumerate(ids):
                    print(f"[{i}] {id_} ({people.get_comment(id_)})")
                choice = int(input("--> "))

            node.attrib["id"] = ids[choice]

    for collection_id, collection in collections.items():
        # Newly added volumes, so we can normalize and name-disambig later
        newly_added_volumes = []

        collection_file = os.path.join(
            args.anthology_dir, "data", "xml", f"{collection_id}.xml"
        )
        if os.path.exists(collection_file):
            root_node = etree.parse(collection_file).getroot()
        else:
            root_node = make_simple_element("collection", attrib={"id": collection_id})

        for volume_id, volume in collection.items():
            volume_node = make_simple_element(
                "volume",
                attrib={"id": volume_id, "ingest-date": args.ingest_date},
            )

            # Replace the existing one if present
            existing_volume_node = root_node.find(f"./volume[@id='{volume_id}']")
            for i, child in enumerate(root_node):
                if child.attrib["id"] == volume_id:
                    root_node[i] = volume_node
                    break
            else:
                root_node.append(volume_node)

            meta_node = None

            for paper_num, paper in sorted(volume.items()):
                paper_id_full = paper["anthology_id"]
                bibfile = paper["bib"]
                paper_node = bib2xml(bibfile, paper_id_full)

                if paper_node.attrib["id"] == "0":
                    # create metadata subtree
                    meta_node = make_simple_element("meta", parent=volume_node)
                    title_node = paper_node.find("title")
                    title_node.tag = "booktitle"
                    meta_node.append(title_node)
                    for author_or_editor in chain(
                        paper_node.findall("./author"), paper_node.findall("./editor")
                    ):
                        meta_node.append(author_or_editor)
                        author_or_editor.tag = "editor"
                    meta_node.append(paper_node.find("publisher"))
                    meta_node.append(paper_node.find("address"))
                    meta_node.append(paper_node.find("month"))
                    meta_node.append(paper_node.find("year"))
                    if book_dest_path is not None:
                        make_simple_element(
                            "url",
                            text=f"{collection_id}-{volume_name}",
                            attrib={"hash": compute_hash_from_file(book_dest_path)},
                            parent=meta_node,
                        )

                    # modify frontmatter tag
                    paper_node.tag = "frontmatter"
                    del paper_node.attrib["id"]
                else:
                    # remove unneeded fields
                    for child in paper_node:
                        if child.tag in [
                            "editor",
                            "address",
                            "booktitle",
                            "publisher",
                            "year",
                            "month",
                        ]:
                            paper_node.remove(child)

                url = paper_node.find("./url")
                if url is not None:
                    url.attrib["hash"] = compute_hash_from_file(paper["pdf"])

                for path, type_ in paper["attachments"]:
                    make_simple_element(
                        "attachment",
                        text=os.path.basename(path),
                        attrib={
                            "type": type_,
                            "hash": compute_hash_from_file(path),
                        },
                        parent=paper_node,
                    )

                if len(paper_node) > 0:
                    volume_node.append(paper_node)

                # Normalize
                for oldnode in paper_node:
                    normalize(oldnode, informat="latex")

                for name_node in chain(
                    paper_node.findall("./author"), paper_node.findall("./editor")
                ):
                    disambiguate_name(name_node, paper_id_full)
                    person = PersonName.from_element(name_node)
                    for name_part in name_node:
                        correct_caps(person, name_part, paper_id_full)

        # Other data from the meta file
        if "isbn" in meta:
            make_simple_element("isbn", meta["isbn"], parent=meta_node)

        indent(root_node)
        tree = etree.ElementTree(root_node)
        tree.write(
            collection_file, encoding="UTF-8", xml_declaration=True, with_tail=True
        )


if __name__ == "__main__":
    now = datetime.now()
    today = f"{now.year}-{now.month:02d}-{now.day:02d}"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "proceedings", nargs="+", help="List of paths to ACLPUB proceedings/ directories."
    )
    parser.add_argument(
        "--ingest-date",
        "-d",
        type=str,
        default=today,
        help="Ingestion date as YYYY-MM-DD. Default: %(default)s.",
    )
    anthology_path = os.path.join(os.path.dirname(sys.argv[0]), "..")
    parser.add_argument(
        "--anthology-dir",
        "-r",
        default=anthology_path,
        help="Root path of ACL Anthology Github repo. Default: %(default)s.",
    )
    pdfs_path = os.path.join(os.environ["HOME"], "anthology-files", "pdf")
    parser.add_argument(
        "--pdfs-dir", "-p", default=pdfs_path, help="Root path for placement of PDF files"
    )
    attachments_path = os.path.join(os.environ["HOME"], "anthology-files", "attachments")
    parser.add_argument(
        "--attachments-dir",
        "-a",
        default=attachments_path,
        help="Root path for placement of PDF files",
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Don't actually copy anything."
    )
    args = parser.parse_args()

    main(args)
