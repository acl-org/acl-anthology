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
import iso639
import os
import re
import shutil
import sys

import lxml.etree as etree

from datetime import datetime
from glob import glob

from normalize_anth import normalize
from anthology.bibtex import read_bibtex
from anthology.index import AnthologyIndex
from anthology.people import PersonName
from anthology.sigs import SIGIndex
from anthology.utils import (
    make_simple_element,
    deconstruct_anthology_id,
    indent,
    compute_hash_from_file,
)
from anthology.venues import VenueIndex

from itertools import chain
from typing import Dict, Any


def log(text: str, fake: bool = False):
    message = "[DRY RUN] " if fake else ""
    print(f"{message}{text}", file=sys.stderr)


def load_bibkeys(anthology_datadir):
    bibkeys = set()
    for xmlfile in glob(os.path.join(anthology_datadir, "xml", "*.xml")):
        tree = etree.parse(xmlfile)
        root = tree.getroot()
        bibkeys.update(str(elem.text) for elem in root.iterfind(".//bibkey"))
    return bibkeys


def read_meta(path: str) -> Dict[str, Any]:
    meta = {"chairs": []}
    with open(path) as instream:
        for line in instream:
            if re.match(r"^\s*$", line):
                continue
            key, value = line.rstrip().split(" ", maxsplit=1)
            if key.startswith("chair"):
                meta["chairs"].append(value)
            else:
                meta[key] = value
    if "volume" in meta and re.match(r"^[a-z0-9]+$", meta["volume"]) is None:
        raise Exception(f"Invalid volume key '{meta['volume']}' in {path}")

    return meta


def maybe_copy(source_path, dest_path):
    """Copies the file if it's different from the target."""
    if not os.path.exists(dest_path) or compute_hash_from_file(
        source_path
    ) != compute_hash_from_file(dest_path):
        log(f"Copying {source_path} -> {dest_path}")
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
    bibkey, bibentry = list(bibdata.entries.items())[0]
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
            except Exception:
                print(
                    f"Couldn't process {bibfilename} for {anthology_id}", file=sys.stderr
                )
                sys.exit(2)

    return paper


def main(args):
    volumes = {}

    anthology_datadir = os.path.join(os.path.dirname(sys.argv[0]), "..", "data")
    venue_index = VenueIndex(srcdir=anthology_datadir)
    venue_keys = [venue["slug"].lower() for _, venue in venue_index.items()]

    SIGIndex(srcdir=anthology_datadir)

    people = AnthologyIndex(srcdir=anthology_datadir)
    people.bibkeys = load_bibkeys(anthology_datadir)

    def correct_caps(name):
        """
        Many people submit their names in "ALL CAPS" or "all lowercase".
        Correct this with heuristics.
        """
        if name.islower() or name.isupper():
            # capitalize all parts
            corrected = " ".join(list(map(lambda x: x.capitalize(), name.split())))
            print(
                f"-> Correcting capitalization of '{name}' to '{corrected}'",
                file=sys.stderr,
            )
            name = corrected

        return name

    def disambiguate_name(node, anth_id):
        name = PersonName.from_element(node)
        ids = people.get_ids(name)
        choice = -1
        if len(ids) > 1:
            while choice < 0 or choice >= len(ids):
                print(
                    f"({anth_id}): ambiguous author {name}; Please choose from the following:"
                )
                for i, id_ in enumerate(ids):
                    print(f"[{i}] {id_} ({people.get_comment(id_)})")
                choice = int(input("--> "))

        return ids[choice], choice

    # Build list of volumes, confirm uniqueness
    unseen_venues = []

    for proceedings in args.proceedings:
        meta = read_meta(os.path.join(proceedings, "meta"))
        venue_abbrev = meta["abbrev"]
        venue_slug = venue_index.get_slug_from_acronym(venue_abbrev)

        if str(datetime.now().year) in venue_abbrev:
            print(f"Fatal: Venue assembler put year in acronym: '{venue_abbrev}'")
            sys.exit(1)

        if re.match(r".*\d$", venue_abbrev) is not None:
            print(
                f"WARNING: Venue {venue_abbrev} ends in a number, this is probably a mistake"
            )

        if venue_slug not in venue_keys:
            unseen_venues.append((venue_slug, venue_abbrev, meta["title"]))

        meta["path"] = proceedings

        meta["collection_id"] = collection_id = meta["year"] + "." + venue_slug
        volume_name = meta["volume"].lower()
        volume_full_id = f"{collection_id}-{volume_name}"

        if volume_full_id in volumes:
            print("Error: ")

        volumes[volume_full_id] = meta

        if "sig" in meta:
            print(
                f"Add this line to {anthology_datadir}/sigs/{meta['sig'].lower()}.yaml:"
            )
            print(f"  - {meta['year']}:")
            print(f"    - {volume_full_id} # {meta['booktitle']}")

    # Make sure all venues exist
    if len(unseen_venues) > 0:
        for venue in unseen_venues:
            slug, abbrev, title = venue
            print(f"Creating venue '{abbrev}' ({title}) slug {slug}")
            venue_index.add_venue(anthology_datadir, abbrev, title)

    # Copy over the PDFs and attachments
    for volume_full_id, meta in volumes.items():
        root_path = os.path.join(meta["path"], "cdrom")
        collection_id = meta["collection_id"]
        venue_name = meta["abbrev"].lower()
        volume_name = meta["volume"].lower()
        year = meta["year"]

        pdfs_dest_dir = os.path.join(args.pdfs_dir, venue_name)
        if not os.path.exists(pdfs_dest_dir):
            os.makedirs(pdfs_dest_dir)

        def find_book():
            """Book location has shifted a bit over the years"""

            potential_names = [
                os.path.join(meta["path"], "book.pdf"),
                os.path.join(
                    meta["path"],
                    "cdrom",
                    f"{year}-{venue_name.lower()}-{volume_name}.pdf",
                    f"{venue_name.lower()}-{year}.{volume_name}.pdf",
                ),
                os.path.join(meta["path"], "cdrom", f"{venue_name.upper()}-{year}.pdf"),
            ]

            for book_rel_path in potential_names:
                if os.path.exists(book_rel_path):
                    return book_rel_path

            return None

        # copy the book from the top-level proceedings/ dir, named "VENUE-year.pdf",
        # or sometimes "book.pdf"
        book_src_path = find_book()
        book_dest_path = None
        if book_src_path is not None and not args.dry_run:
            book_dest_path = (
                os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}") + ".pdf"
            )
            maybe_copy(book_src_path, book_dest_path)

        # temp holder for papers in each volume
        volume = dict()

        # copy the paper PDFs
        pdf_src_dir = os.path.join(root_path, "pdf")
        for pdf_file in os.listdir(pdf_src_dir):
            # Skip . files
            if os.path.basename(pdf_file).startswith("."):
                continue

            # names are {abbrev}{number}.pdf
            match = re.match(r".*\.(\d+)\.pdf", pdf_file)

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

                volume[paper_num] = {
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
                # Find the attachment file, using a bit of a fuzzy
                # match. The fuzzy match is because sometimes people
                # generate the proceedings with the wrong venue
                # code. If we correct it, we still need to be able to
                # find the file.
                match = re.match(
                    rf"{year}\..*-\w+\.(\d+)_?(\w+)\.(\w+)$", attachment_file
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

                volume[paper_num]["attachments"].append((dest_path, type_))

        # create xml
        collection_file = os.path.join(
            args.anthology_dir, "data", "xml", f"{collection_id}.xml"
        )
        if os.path.exists(collection_file):
            root_node = etree.parse(collection_file).getroot()
        else:
            root_node = make_simple_element("collection", attrib={"id": collection_id})

        volume_node = make_simple_element(
            "volume",
            attrib={
                "id": volume_name,
                "ingest-date": args.ingest_date,
                "type": "proceedings",
            },
        )

        # Replace the existing one if present
        root_node.find(f"./volume[@id='{volume_name}']")
        for i, child in enumerate(root_node):
            if child.attrib["id"] == volume_name:
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
                    disamb_name, name_choice = disambiguate_name(
                        author_or_editor, paper_id_full
                    )
                    if name_choice != -1:
                        author_or_editor.attrib["id"] = disamb_name
                    PersonName.from_element(author_or_editor)
                    for name_part in author_or_editor:
                        name_part.text = correct_caps(name_part.text)
                    meta_node.append(author_or_editor)
                    author_or_editor.tag = "editor"

                # Here, we grab the publisher from the meta file, in case it's not in the
                # frontmatter paper. We don't handle the situation where it's in neither!
                publisher_node = paper_node.find("publisher")
                if publisher_node is None:
                    publisher_node = make_simple_element("publisher", meta["publisher"])
                meta_node.append(publisher_node)

                # Look for the address in the bib file, then the meta file
                address_node = paper_node.find("address")
                if address_node is None:
                    address_node = make_simple_element("address", meta["location"])
                meta_node.append(address_node)

                meta_node.append(paper_node.find("month"))
                meta_node.append(paper_node.find("year"))
                if book_dest_path is not None:
                    make_simple_element(
                        "url",
                        text=f"{collection_id}-{volume_name}",
                        attrib={"hash": compute_hash_from_file(book_dest_path)},
                        parent=meta_node,
                    )

                # Add the venue tag
                make_simple_element("venue", venue_name, parent=meta_node)

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

            # Adjust the language tag
            language_node = paper_node.find("./language")
            if language_node is not None:
                try:
                    lang = iso639.languages.get(name=language_node.text)
                except KeyError:
                    raise Exception(f"Can't find language '{language_node.text}'")
                language_node.text = lang.part3

            # Fix author names
            for name_node in chain(
                paper_node.findall("./author"), paper_node.findall("./editor")
            ):
                disamb_name, name_choice = disambiguate_name(name_node, paper_id_full)
                if name_choice != -1:
                    name_node.attrib["id"] = disamb_name
                PersonName.from_element(name_node)
                for name_part in name_node:
                    name_part.text = correct_caps(name_part.text)

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
