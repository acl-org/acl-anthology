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

"""Ingests ACLPUB proceedings/ directories into the Anthology.

This script:
- executes some basic sanity checks
- applies normalization to names and titles
- ingests metadata through the acl_anthology Python library
- copies PDFs and attachments into place for rsyncing to the server
"""

import argparse
import iso639
import os
import pybtex.database.input.bibtex
import re
import shutil
import sys

from datetime import datetime
from pathlib import Path
from slugify import slugify
from typing import Any, Dict, Optional

from acl_anthology import Anthology
from acl_anthology.collections.types import PaperType, VolumeType
from acl_anthology.files import (
    AttachmentReference,
    PDFReference,
    compute_checksum_from_file,
)
from acl_anthology.people import Name, NameSpecification
from acl_anthology.text import MarkupText
from acl_anthology.utils.ids import parse_id
from fixedcase.protect import protect as protect_fixedcase


def log(text: str) -> None:
    print(f"{text}", file=sys.stderr)


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


def maybe_copy(source_path: str, dest_path: str):
    """Copies the file if it's different from the target."""
    if not os.path.exists(dest_path) or compute_checksum_from_file(
        source_path
    ) != compute_checksum_from_file(dest_path):
        log(f"Copying {source_path} -> {dest_path}")
        shutil.copyfile(source_path, dest_path)


def correct_caps(name: Optional[str]) -> Optional[str]:
    """
    Many people submit their names in "ALL CAPS" or "all lowercase".
    Correct this with heuristics.
    """
    if name is None:
        return None

    if name.islower() or name.isupper():
        corrected = " ".join(part.capitalize() for part in name.split())
        if corrected != name:
            print(
                f"-> Correcting capitalization of '{name}' to '{corrected}'",
                file=sys.stderr,
            )
        name = corrected

    return name


def venue_slug_from_acronym(acronym: str) -> str:
    """Build a venue slug from an acronym (legacy-compatible behavior)."""
    slug = slugify(acronym.replace("-", ""))
    if re.match(r"^[a-z][a-z0-9]+$", slug) is None:
        raise Exception(f"Invalid venue slug '{slug}' derived from '{acronym}'")
    return slug


def normalize_markup_text(text: Optional[str]) -> Optional[MarkupText]:
    """Normalize potentially-LaTeX text into MarkupText."""
    if text is None:
        return None
    return MarkupText.from_latex_maybe(text)


def normalize_title_text(text: Optional[str], tag: str) -> Optional[MarkupText]:
    """Normalize and apply truelist-based fixed-case protection for titles."""
    if text is None:
        return None
    markup = MarkupText.from_latex_maybe(text)
    elem = markup.to_xml(tag)
    protect_fixedcase(elem)
    return MarkupText.from_xml(elem)


def normalize_plain_text(text: Optional[str]) -> Optional[str]:
    """Normalize potentially-LaTeX text into plain text."""
    if text is None:
        return None
    return MarkupText.from_latex_maybe(text).as_text()


def make_name_spec(person) -> NameSpecification:
    first_text = " ".join(person.first_names)
    last_text = " ".join(person.prelast_names + person.last_names)

    if person.lineage_names:
        last_text += ", " + " ".join(person.lineage_names)

    if last_text.strip() in {"", "-"}:
        last_text = first_text
        first_text = ""

    first_text = correct_caps(first_text.strip())
    last_text = correct_caps(last_text.strip())

    return NameSpecification(
        name=Name(first_text if first_text else None, last_text if last_text else "")
    )


def read_bib_entry(bibfilename: str, anthology_id: str) -> Optional[Dict[str, Any]]:
    """Parse a single-entry BibTeX file into structured metadata."""
    _, _, paper_id = parse_id(anthology_id)
    if paper_id is None:
        return None

    bibdata = pybtex.database.input.bibtex.Parser().parse_file(bibfilename)
    if len(bibdata.entries) != 1:
        log(f"more than one entry in {bibfilename}")

    bibentry = next(iter(bibdata.entries.values()))
    if len(bibentry.fields) == 0:
        log(f"parsing bib of paper {paper_id} failed")
        sys.exit(1)

    return {
        "title": normalize_title_text(bibentry.fields.get("title"), "title"),
        "booktitle": normalize_title_text(bibentry.fields.get("booktitle"), "booktitle"),
        "month": normalize_plain_text(bibentry.fields.get("month")),
        "year": bibentry.fields.get("year"),
        "address": normalize_plain_text(bibentry.fields.get("address")),
        "publisher": normalize_plain_text(bibentry.fields.get("publisher")),
        "pages": normalize_plain_text(bibentry.fields.get("pages")),
        "abstract": normalize_markup_text(bibentry.fields.get("abstract")),
        "doi": bibentry.fields.get("doi"),
        "language": bibentry.fields.get("language"),
        "authors": [
            make_name_spec(person) for person in bibentry.persons.get("author", [])
        ],
        "editors": [
            make_name_spec(person) for person in bibentry.persons.get("editor", [])
        ],
    }


def set_disambiguation_ids(
    name_specs: list[NameSpecification], anthology: Anthology
) -> None:
    """Preserve old ingest behavior: pick first match when names are ambiguous."""
    for name_spec in name_specs:
        matches = anthology.people.get_by_name(name_spec.name)
        if len(matches) > 1:
            name_spec.id = matches[0].id


def main(args):
    volumes = {}

    anthology_datadir = Path(args.anthology_dir) / "data"
    anthology = Anthology(datadir=anthology_datadir)

    anthology.collections.load()
    anthology.collections.bibkeys.load()
    anthology.venues.load()
    anthology.people.load()

    venue_keys = {venue_id.lower() for venue_id in anthology.venues.keys()}

    unseen_venues = []

    for proceedings in args.proceedings:
        meta = read_meta(os.path.join(proceedings, "meta"))
        venue_abbrev = meta["abbrev"]
        venue_slug = venue_slug_from_acronym(venue_abbrev)

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
            print(f"Error: duplicate volume id {volume_full_id}")
            sys.exit(1)

        volumes[volume_full_id] = meta

        if "sig" in meta:
            print(
                f"Add this line to {anthology_datadir}/yaml/sigs/{meta['sig'].lower()}.yaml:"
            )
            print(f"  - {meta['year']}:")
            print(f"    - {volume_full_id} # {meta['booktitle']}")

    if len(unseen_venues) > 0:
        for slug, abbrev, title in unseen_venues:
            print(f"Creating venue '{abbrev}' ({title}) slug {slug}")
            anthology.venues.create(id=slug, acronym=abbrev, name=title)

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
            potential_names = [
                os.path.join(meta["path"], "book.pdf"),
                os.path.join(meta["path"], "cdrom", "book.pdf"),
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

        book_src_path = find_book()
        book_dest_path = None
        if book_src_path is not None:
            book_dest_path = os.path.join(
                pdfs_dest_dir, f"{collection_id}-{volume_name}.pdf"
            )
            maybe_copy(book_src_path, book_dest_path)

        volume = dict()

        pdf_src_dir = os.path.join(root_path, "pdf")
        for pdf_file in os.listdir(pdf_src_dir):
            if os.path.basename(pdf_file).startswith("."):
                continue

            match = re.match(r".*?(\d+)\.pdf", pdf_file)
            if match is None:
                continue

            paper_num = int(match[1])
            paper_id_full = f"{collection_id}-{volume_name}.{paper_num}"

            bib_path = os.path.join(
                root_path,
                "bib",
                pdf_file.replace("/pdf", "/bib/").replace(".pdf", ".bib"),
            )

            pdf_src_path = os.path.join(pdf_src_dir, pdf_file)
            pdf_dest_path = os.path.join(pdfs_dest_dir, f"{paper_id_full}.pdf")
            maybe_copy(pdf_src_path, pdf_dest_path)

            volume[paper_num] = {
                "anthology_id": paper_id_full,
                "bib": bib_path,
                "pdf_src": pdf_src_path,
                "pdf_dest": pdf_dest_path,
                "attachments": [],
            }

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
                    rf"{year}\..*-\w+\.(\d+)_?(\w+)\.(\w+)$", attachment_file
                )
                if match is None:
                    print(
                        f"* Warning: no attachment match for {attachment_file}",
                        file=sys.stderr,
                    )
                    continue

                paper_num, type_, ext = match.groups()
                paper_num = int(paper_num)

                file_name = f"{collection_id}-{volume_name}.{paper_num}.{type_}.{ext}"
                dest_path = os.path.join(attachments_dest_dir, file_name)
                if not os.path.exists(dest_path):
                    log(f"Copying {attachment_file} -> {dest_path}")
                    shutil.copyfile(attachment_file_path, dest_path)

                if paper_num not in volume:
                    print(f"Fatal: no key {paper_num} in volume", file=sys.stderr)
                    sys.exit(1)

                volume[paper_num]["attachments"].append(
                    {
                        "src": attachment_file_path,
                        "dest": dest_path,
                        "type": type_,
                    }
                )

        collection = anthology.get_collection(collection_id)
        if collection is None:
            collection = anthology.collections.create(collection_id)

        if collection.get(volume_name) is not None:
            del collection[volume_name]
            collection.is_modified = True

        volume_type = VolumeType.JOURNAL if args.is_journal else VolumeType.PROCEEDINGS

        frontmatter_data = None
        parsed_papers = {}
        for paper_num, paper in sorted(volume.items()):
            parsed = read_bib_entry(paper["bib"], paper["anthology_id"])
            if parsed is None:
                continue
            if paper_num == 0:
                frontmatter_data = parsed
            else:
                parsed_papers[paper_num] = parsed

        volume_title = (
            (frontmatter_data or {}).get("title")
            or normalize_title_text(
                meta.get("booktitle") or meta.get("title"), "booktitle"
            )
            or f"{meta['abbrev']} {meta['year']}"
        )

        volume_editors = []
        if frontmatter_data is not None:
            volume_editors = frontmatter_data["editors"] + frontmatter_data["authors"]
            set_disambiguation_ids(volume_editors, anthology)

        venue_ids = [venue_name]
        if args.is_workshop:
            venue_ids.append("ws")

        volume_kwargs = {
            "id": volume_name,
            "title": volume_title,
            "year": str(year),
            "type": volume_type,
            "ingest_date": args.ingest_date,
            "editors": volume_editors,
            "venue_ids": venue_ids,
            "publisher": (frontmatter_data or {}).get("publisher")
            or normalize_plain_text(meta.get("publisher")),
            "address": (frontmatter_data or {}).get("address")
            or normalize_plain_text(meta.get("location")),
            "month": (frontmatter_data or {}).get("month") or meta.get("month"),
        }

        if args.is_journal:
            volume_kwargs["journal_volume"] = volume_name

        if "isbn" in meta:
            volume_kwargs["isbn"] = meta["isbn"]

        if book_src_path is not None and book_dest_path is not None:
            volume_kwargs["pdf"] = PDFReference.from_file(book_dest_path)

        volume_obj = collection.create_volume(**volume_kwargs)

        if (
            frontmatter_data is not None
            and book_src_path is not None
            and book_dest_path is not None
        ):
            frontmatter_title = frontmatter_data.get("title") or volume_title
            frontmatter_kwargs = {
                "id": "0",
                "type": PaperType.FRONTMATTER,
                "title": frontmatter_title,
                "authors": frontmatter_data["authors"],
                "editors": frontmatter_data["editors"],
            }
            set_disambiguation_ids(frontmatter_kwargs["authors"], anthology)
            set_disambiguation_ids(frontmatter_kwargs["editors"], anthology)
            frontmatter_kwargs["pdf"] = PDFReference.from_file(book_dest_path)
            volume_obj.create_paper(**frontmatter_kwargs)

        for paper_num, paper in sorted(volume.items()):
            if paper_num == 0:
                continue

            parsed = parsed_papers[paper_num]

            title = parsed.get("title")
            if title is None:
                print(f"Fatal: missing title in {paper['bib']}", file=sys.stderr)
                sys.exit(1)

            authors = parsed["authors"]
            editors = parsed["editors"]
            set_disambiguation_ids(authors, anthology)
            set_disambiguation_ids(editors, anthology)

            kwargs: Dict[str, Any] = {
                "id": str(paper_num),
                "title": title,
                "authors": authors,
                "editors": editors,
                "pdf": PDFReference.from_file(paper["pdf_dest"]),
            }

            for key in ("abstract", "doi", "pages"):
                value = parsed.get(key)
                if value:
                    kwargs[key] = value

            language = parsed.get("language")
            if language:
                try:
                    lang = iso639.languages.get(name=language)
                except KeyError:
                    raise Exception(f"Can't find language '{language}'")
                kwargs["language"] = lang.part3

            attachments = []
            for attachment in paper["attachments"]:
                attachments.append(
                    (
                        attachment["type"],
                        AttachmentReference.from_file(attachment["dest"]),
                    )
                )
            if attachments:
                kwargs["attachments"] = attachments

            volume_obj.create_paper(**kwargs)

    anthology.save_all()


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
        "--is-workshop", "-w", action="store_true", help="Venue is a workshop"
    )
    parser.add_argument(
        "--is-journal", "-j", action="store_true", help="Venue is a journal"
    )
    args = parser.parse_args()

    main(args)
