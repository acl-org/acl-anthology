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
import readline
import shutil
import sys

import lxml.etree as etree

from collections import defaultdict, OrderedDict
from datetime import datetime
from glob import glob

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
from typing import Dict, Any, List, Tuple, Optional


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
    if "volume" in meta and re.match(rf"^[a-z0-9]+$", meta["volume"]) is None:
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


def build_volumes(
    path: str, venue_index: VenueIndex, venue_keys: List[str]
) -> Tuple[List, Dict]:
    unseen_venues = []
    volumes = {}

    for proceedings in path:  # args.proceedings
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
            sys.exit(1)

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
            print(f"Add this line to sigs/{meta['sig'].lower()}.yaml:")
            print(f"  - {meta['year']}:")
            print(f"    - {volume_full_id} # {meta['booktitle']}")
    return unseen_venues, volumes


def create_venues(unseen_venues: List, venue_index: VenueIndex, anthology_datadir: str):
    '''
    Create yaml file for new venues
    '''
    if len(unseen_venues) > 0:
        for venue in unseen_venues:
            slug, abbrev, title = venue
            print(f"Creating venue '{abbrev}' ({title}) slug {slug}")
            venue_index.add_venue(anthology_datadir, abbrev, title)


def find_book(meta) -> Optional[str]:
    """Book location has shifted a bit over the years"""
    year = meta["year"]
    venue_name = meta["abbrev"].lower()
    volume_name = meta["volume"].lower()

    potential_names = [
        os.path.join(meta["path"], "book.pdf"),
        os.path.join(
            meta["path"],
            "cdrom",
            f"{year}-{venue_name.lower()}-{volume_name}.pdf",
        ),
        os.path.join(meta["path"], "cdrom", f"{venue_name.upper()}-{year}.pdf"),
    ]

    for book_rel_path in potential_names:
        if os.path.exists(book_rel_path):
            return book_rel_path

    return None


def copy_pdf_and_attachment(meta, pdfs_dir: str) -> Dict:  # args.pdfs_dir
    root_path = os.path.join(meta["path"], "cdrom")
    collection_id = meta["collection_id"]
    venue_name = meta["abbrev"].lower()
    volume_name = meta["volume"].lower()
    year = meta["year"]

    pdfs_dest_dir = os.path.join(pdfs_dir, venue_name)
    if not os.path.exists(pdfs_dest_dir):
        os.makedirs(pdfs_dest_dir)

    # handle proceedings.pdf
    proceedings_src_path = find_book(meta)
    proceedings_dest_path = None

    if proceedings_src_path is not None and not args.dry_run:
        proceedings_dest_path = (
            os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}") + ".pdf"
        )
        maybe_copy(proceedings_src_path, proceedings_dest_path)

    # temp holder for volume
    volume = dict()

    # handle pdfs
    pdfs_src_dir = os.path.join(root_path, "pdf")
    for pdf_file in os.listdir(pdfs_src_dir):
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

            pdf_src_path = os.path.join(pdfs_src_dir, pdf_file)
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

    # handle attachments
    if os.path.exists(os.path.join(root_path, "additional")):
        attachments_dest_dir = os.path.join(args.attachments_dir, venue_name)
        if not os.path.exists(attachments_dest_dir):
            os.makedirs(attachments_dest_dir)
        for attachment_file in os.listdir(os.path.join(root_path, "additional")):
            if os.path.basename(attachment_file).startswith("."):
                continue
            attachment_file_path = os.path.join(root_path, "additional", attachment_file)
            # Find the attachment file, using a bit of a fuzzy
            # match. The fuzzy match is because sometimes people
            # generate the proceedings with the wrong venue
            # code. If we correct it, we still need to be able to
            # find the file.
            match = re.match(rf"{year}\..*-\w+\.(\d+)_?(\w+)\.(\w+)$", attachment_file)
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

    return volume, proceedings_dest_path


def check_frontmatter(volume: Dict) -> bool:
    '''
    Check if front matter pdf exists
    '''
    for _, volume_content in volume.items():
        if volume_content['anthology_id'].split('.')[-1] == '0':
            return True
    return False


def create_xml(
    volume: Dict,
    meta: Dict,
    prooceedings_dst_dir,
    anthology_dir: str,
    ingest_date: str,
    people,
):
    collection_id = meta["collection_id"]
    volume_name = meta["volume"].lower()
    venue_name = meta["abbrev"].lower()

    collection_file = os.path.join(anthology_dir, "data", "xml", f"{collection_id}.xml")
    if os.path.exists(collection_file):
        root_node = etree.parse(collection_file).getroot()
    else:
        root_node = make_simple_element("collection", attrib={"id": collection_id})

    volume_node = make_simple_element(
        "volume",
        attrib={"id": volume_name, "ingest-date": ingest_date},
    )

    # Replace the existing one if present
    existing_volume_node = root_node.find(f"./volume[@id='{volume_name}']")
    for i, child in enumerate(root_node):
        if child.attrib["id"] == volume_name:
            root_node[i] = volume_node
            break
        else:
            root_node.append(volume_node)

    meta_node = None

    # Flag to make sure meta and frontmatter block only gets generated once
    set_meta_frontmatter_block = check_frontmatter(volume)

    for _, paper in sorted(volume.items()):
        paper_id_full = paper["anthology_id"]
        bibfile = paper["bib"]
        paper_node = bib2xml(bibfile, paper_id_full)

        # 0 is the front matter pdf
        if paper_node.attrib["id"] == "0" or set_meta_frontmatter_block is False:
            # create metadata subtree
            meta_node = make_simple_element("meta", parent=volume_node)

            if paper_node.attrib["id"] == "0":
                title_node = paper_node.find("title")
                title_node.tag = "booktitle"
            else:
                title_node = make_simple_element(
                    "booktitle", meta['booktitle'], parent=meta_node
                )
            meta_node.append(title_node)

            # editors
            if paper_node.attrib["id"] == "0":
                author_or_editors = chain(
                    paper_node.findall("./author"), paper_node.findall("./editor")
                )

                for author_or_editor in author_or_editors:
                    disamb_name, name_choice = disambiguate_name(
                        author_or_editor, paper_id_full, people
                    )
                    if name_choice != -1:
                        author_or_editor.attrib["id"] = disamb_name
                    for name_part in author_or_editor:
                        name_part.text = correct_caps(name_part.text)
                    meta_node.append(author_or_editor)
                    author_or_editor.tag = "editor"
            else:
                editors = meta.get('chairs')
                if len(editors) == 0:
                    print(f'chairs are missing in meta file')
                    sys.exit(2)
                for editor in editors:
                    name_node = make_simple_element('editor', parent=meta_node)
                    make_simple_element(
                        "first", ' '.join(editor.split(' ')[0:-1]), parent=name_node
                    )
                    make_simple_element("last", editor.split(' ')[-1], parent=name_node)

            # publisher info
            if meta.get('publisher') is None:
                print('publisher is missing in meta')
                sys.exit(2)
            publisher_node = (
                paper_node.find("publisher")
                if (
                    paper_node.attrib["id"] == "0"
                    and paper_node.find("publisher") is not None
                )
                else make_simple_element("publisher", meta.get("publisher"))
            )
            meta_node.append(publisher_node)
            # address info
            if meta.get('location') is None:
                print('location is missing in meta')
                sys.exit(2)
            address_node = (
                paper_node.find("address")
                if (
                    paper_node.attrib["id"] == "0"
                    and paper_node.find("address") is not None
                )
                else make_simple_element("address", meta.get("location"))
            )
            meta_node.append(address_node)
            # month info
            if meta.get('month') is None:
                print('month is missing in meta')
                sys.exit(2)
            month_node = (
                paper_node.find("month")
                if (
                    paper_node.attrib["id"] == "0"
                    and paper_node.find("month") is not None
                )
                else make_simple_element("month", meta.get("month"))
            )
            meta_node.append(month_node)
            # year info
            if meta.get('year') is None:
                print('year is missing in meta')
                sys.exit(2)
            year_node = (
                paper_node.find("year")
                if (
                    paper_node.attrib["id"] == "0" and paper_node.find("year") is not None
                )
                else make_simple_element("year", meta.get("year"))
            )
            meta_node.append(year_node)

            if prooceedings_dst_dir is not None:
                make_simple_element(
                    "url",
                    text=f"{collection_id}-{volume_name}",
                    attrib={"hash": compute_hash_from_file(prooceedings_dst_dir)},
                    parent=meta_node,
                )

            # Add the venue tag
            make_simple_element("venue", venue_name, parent=meta_node)

            # Front matter block
            if paper_node.attrib["id"] == "0":
                # modify frontmatter tag
                paper_node.tag = "frontmatter"
                del paper_node.attrib["id"]
            else:
                make_simple_element("frontmatter", parent=volume_node)
            set_meta_frontmatter_block = True

        if paper_node.attrib["id"] != "0":
            print(f'onto removing stuff for paper {paper_node.attrib["id"]}')
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
            disamb_name, name_choice = disambiguate_name(name_node, paper_id_full, people)
            if name_choice != -1:
                name_node.attrib["id"] = disamb_name
            person = PersonName.from_element(name_node)
            for name_part in name_node:
                name_part.text = correct_caps(name_part.text)

    # Other data from the meta file
    if "isbn" in meta:
        make_simple_element("isbn", meta["isbn"], parent=meta_node)

    indent(root_node)
    tree = etree.ElementTree(root_node)
    tree.write(collection_file, encoding="UTF-8", xml_declaration=True, with_tail=True)


def correct_caps(name: str) -> str:
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


def disambiguate_name(node, anth_id, people):
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


def main(args):
    anthology_datadir = os.path.join(os.path.dirname(sys.argv[0]), "..", "data")
    venue_index = VenueIndex(srcdir=anthology_datadir)
    venue_keys = [venue["slug"].lower() for _, venue in venue_index.items()]

    people = AnthologyIndex(srcdir=anthology_datadir)
    people.bibkeys = load_bibkeys(anthology_datadir)

    # Build list of volumes, confirm uniqueness
    unseen_venues, volumes = build_volumes(args.proceedings, venue_index, venue_keys)

    create_venues(unseen_venues, venue_index, anthology_datadir)

    # Copy over the PDFs and attachments and create xml
    for _, meta in volumes.items():
        volume, prooceedings_dst_dir = copy_pdf_and_attachment(meta, args.pdfs_dir)
        create_xml(
            volume,
            meta,
            prooceedings_dst_dir,
            args.anthology_dir,
            args.ingest_date,
            people,
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
