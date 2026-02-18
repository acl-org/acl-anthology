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
import yaml
import re
import shutil
import sys
import warnings
import PyPDF2

from datetime import datetime
from pathlib import Path
from slugify import slugify
from typing import Any, Dict, Optional, List

from acl_anthology import Anthology
from acl_anthology.collections.types import EventLink, PaperType, VolumeType
from acl_anthology.files import (
    AttachmentReference,
    PDFReference,
)
from acl_anthology.people import Name, NameSpecification
from acl_anthology.text import MarkupText
from acl_anthology.utils.ids import parse_id
from fixedcase.protect import protect as protect_fixedcase

ARCHIVAL_DEFAULT = True


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


def detect_ingestion_format(path: str) -> str:
    src = Path(path)
    has_meta = (src / "meta").is_file()
    has_cdrom = (src / "cdrom").is_dir()
    has_conf = any(
        p.is_file()
        for p in [
            src / "conference_details.yml",
            src / "inputs" / "conference_details.yml",
        ]
    )
    has_papers = any(
        p.is_file() for p in [src / "papers.yml", src / "inputs" / "papers.yml"]
    )

    if has_meta and has_cdrom:
        return "aclpub"
    if has_conf and has_papers:
        return "aclpub2"
    raise Exception(
        f"Could not detect ingestion format for {path}; expected ACLPUB (meta + cdrom/) or ACLPUB2 (conference_details.yml + papers.yml)"
    )


def parse_conf_yaml(ingestion_dir: str) -> Dict[str, Any]:
    ingestion_dir = Path(ingestion_dir)
    paths_to_check = [
        ingestion_dir / "inputs" / "conference_details.yml",
        ingestion_dir / "conference_details.yml",
    ]
    meta = None
    for path in paths_to_check:
        if path.exists():
            meta = yaml.safe_load(path.read_text())
            break
    else:
        raise Exception(f"Can't find conference_details.yml (looked in {paths_to_check})")

    meta["month"] = meta["start_date"].strftime("%B")
    meta["year"] = str(meta["start_date"].year)

    must_have_keys = [
        "book_title",
        "anthology_venue_id",
        "volume_name",
        "month",
        "year",
        "location",
        "editors",
        "publisher",
        "event_name",
    ]
    for key in must_have_keys:
        assert key in meta.keys(), f"{key} is missing in the conference_details.yml file"

    meta["volume_name"] = str(meta["volume_name"])
    if re.match(r"^[a-z0-9]+$", meta["volume_name"]) is None:
        raise Exception(
            f"Invalid volume key '{meta['volume_name']}' in {ingestion_dir / 'inputs' / 'conference_details.yml'}"
        )

    return meta


def parse_paper_yaml(ingestion_dir: str) -> List[Dict[str, Any]]:
    ingestion_dir = Path(ingestion_dir)
    paths_to_check = [
        ingestion_dir / "inputs" / "papers.yml",
        ingestion_dir / "papers.yml",
    ]
    papers = None
    for path in paths_to_check:
        if path.exists():
            papers = yaml.safe_load(path.read_text())
            break
    else:
        raise Exception("Can't find papers.yml (looked in root dir and under inputs/)")

    for paper in papers:
        if "archival" not in paper:
            paper["archival"] = ARCHIVAL_DEFAULT
    return papers


def add_page_numbers(
    papers: List[Dict[str, Any]], ingestion_dir: str
) -> List[Dict[str, Any]]:
    ingestion_dir = Path(ingestion_dir)
    start, end = 1, 0
    for paper in papers:
        if not paper["archival"]:
            continue
        assert "file" in paper.keys(), f"{paper['id']} is missing key 'file'"
        paper_id = str(paper["id"])
        paper_path = paper["file"]
        paths_to_check = [
            ingestion_dir / "watermarked_pdfs" / paper_path,
            ingestion_dir / "watermarked_pdfs" / f"{paper_id}.pdf",
        ]
        paper_need_read_path = None
        for path in paths_to_check:
            if path.exists():
                paper_need_read_path = str(path)
                break
        else:
            raise Exception(
                f"* Fatal: could not find paper ID {paper_id} ({paths_to_check})"
            )

        with open(paper_need_read_path, "rb") as pdf:
            pdf_reader = PyPDF2.PdfReader(pdf)
            num_of_pages = len(pdf_reader.pages)
            start = end + 1
            end = start + num_of_pages - 1
            paper["pages"] = f"{start}-{end}"

    return papers


def trim_orcid(orcid: str) -> str:
    match = re.match(r".*(\d{4}-\d{4}-\d{4}-\d{3}[\dX]).*", orcid, re.IGNORECASE)
    if match is not None:
        return match.group(1).upper()
    return orcid


def correct_names(author: Dict[str, Any]) -> Dict[str, Any]:
    if author.get("middle_name") is not None and author["middle_name"].lower() == "de":
        author["last_name"] = author["middle_name"] + " " + author["last_name"]
        del author["middle_name"]
    return author


def join_names(author: Dict[str, Any], fields=None) -> str:
    if fields is None:
        fields = ["first_name", "middle_name"]
    return " ".join(author[field] for field in fields if author.get(field) is not None)


def namespec_from_author(author: Dict[str, Any]) -> NameSpecification:
    author = correct_names(dict(author))
    first_name = correct_caps(join_names(author).strip())
    last_name = correct_caps((author.get("last_name") or "").strip())
    if first_name and not last_name:
        first_name, last_name = last_name, first_name
    if not last_name:
        raise Exception(f"BAD AUTHOR: {author}")
    kwargs: Dict[str, Any] = {"name": Name(first_name if first_name else None, last_name)}
    if "orcid" in author and author["orcid"]:
        kwargs["orcid"] = trim_orcid(str(author["orcid"]))
    affiliation = author.get("institution") or author.get("affiliation")
    if affiliation:
        kwargs["affiliation"] = affiliation
    return NameSpecification(**kwargs)


def create_dest_path(org_dir_name: str, venue_name: str) -> str:
    dest_dir = os.path.join(org_dir_name, venue_name)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    return dest_dir


def pdf_reference_from_paths(
    anthology_id: str, src_path: str, dest_path: str
) -> PDFReference:
    if os.path.exists(dest_path):
        return PDFReference.from_file(dest_path)
    return PDFReference(name=anthology_id)


def attachment_reference_from_paths(src_path: str, dest_path: str) -> AttachmentReference:
    if os.path.exists(dest_path):
        return AttachmentReference.from_file(dest_path)
    return AttachmentReference(name=os.path.basename(dest_path))


def add_parent_event(
    anthology: Anthology, parent_event: Optional[str], volume_full_id: str
) -> None:
    if parent_event is None:
        return
    anthology.events.load()
    event = anthology.get_event(parent_event)
    if event is None:
        print(f"No event node with id '{parent_event}' found", file=sys.stderr)
        return
    if anthology.get_volume(volume_full_id) is None:
        print(f"No such ingested volume {volume_full_id}", file=sys.stderr)
        return
    existing = {event_id for (event_id, _) in event.colocated_ids}
    collection_id, volume_name, _ = parse_id(volume_full_id)
    if any(collection_id == c and volume_name == v for (c, v, _) in existing):
        print(
            f"Event {volume_full_id} already listed as colocated with {parent_event}, skipping",
            file=sys.stderr,
        )
    else:
        event.add_colocated(volume_full_id, type_=EventLink.EXPLICIT)
        print(
            f"Created event entry in {parent_event} for {volume_full_id}", file=sys.stderr
        )


def ensure_venue(anthology: Anthology, venue_abbrev: str, venue_title: str) -> str:
    venue_slug = venue_slug_from_acronym(venue_abbrev)
    if str(datetime.now().year) in venue_abbrev:
        print(f"Fatal: Venue assembler put year in acronym: '{venue_abbrev}'")
        sys.exit(1)
    if re.match(r".*\d$", venue_abbrev) is not None:
        print(
            f"WARNING: Venue {venue_abbrev} ends in a number, this is probably a mistake"
        )
    if venue_slug not in anthology.venues:
        print(f"Creating venue '{venue_abbrev}' ({venue_title}) slug {venue_slug}")
        anthology.venues.create(id=venue_slug, acronym=venue_abbrev, name=venue_title)
    return venue_slug


def ingest_aclpub(
    anthology: Anthology,
    proceedings: str,
    seen_volume_ids: set[str],
    args: argparse.Namespace,
) -> None:
    meta = read_meta(os.path.join(proceedings, "meta"))
    venue_abbrev = meta["abbrev"]
    venue_slug = ensure_venue(anthology, venue_abbrev, meta.get("title", venue_abbrev))

    meta["path"] = proceedings
    collection_id = meta["year"] + "." + venue_slug
    volume_name = meta["volume"].lower()
    volume_full_id = f"{collection_id}-{volume_name}"
    if volume_full_id in seen_volume_ids:
        raise Exception(f"Duplicate volume ID encountered: {volume_full_id}")
    seen_volume_ids.add(volume_full_id)

    root_path = os.path.join(meta["path"], "cdrom")
    venue_name = meta["abbrev"].lower()
    year = meta["year"]

    pdfs_dest_dir = os.path.join(args.pdfs_dir, venue_name)
    os.makedirs(pdfs_dest_dir, exist_ok=True)

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
        book_dest_path = os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}.pdf")
        maybe_copy(book_src_path, book_dest_path)

    volume = {}
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
            root_path, "bib", pdf_file.replace("/pdf", "/bib/").replace(".pdf", ".bib")
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

    additional_dir = os.path.join(root_path, "additional")
    if os.path.exists(additional_dir):
        attachments_dest_dir = os.path.join(args.attachments_dir, venue_name)
        os.makedirs(attachments_dest_dir, exist_ok=True)
        for attachment_file in os.listdir(additional_dir):
            if os.path.basename(attachment_file).startswith("."):
                continue
            attachment_file_path = os.path.join(additional_dir, attachment_file)
            match = re.match(rf"{year}\..*-\w+\.(\d+)_?(\w+)\.(\w+)$", attachment_file)
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
                {"src": attachment_file_path, "dest": dest_path, "type": type_}
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
        or normalize_latex_title(meta.get("booktitle") or meta.get("title"))
        or f"{meta['abbrev']} {meta['year']}"
    )
    volume_editors = []
    if frontmatter_data is not None:
        volume_editors = frontmatter_data["editors"] + frontmatter_data["authors"]

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
        "publisher": (frontmatter_data or {}).get("publisher") or meta.get("publisher"),
        "address": (frontmatter_data or {}).get("address") or meta.get("location"),
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
        frontmatter_kwargs = {
            "id": "0",
            "type": PaperType.FRONTMATTER,
            "title": frontmatter_data.get("title") or volume_title,
            "authors": frontmatter_data["authors"],
            "editors": frontmatter_data["editors"],
            "pdf": PDFReference.from_file(book_dest_path),
        }
        volume_obj.create_paper(**frontmatter_kwargs)

    for paper_num, paper in sorted(volume.items()):
        if paper_num == 0:
            continue
        parsed = parsed_papers[paper_num]
        title = parsed.get("title")
        if title is None:
            print(f"Fatal: missing title in {paper['bib']}", file=sys.stderr)
            sys.exit(1)
        kwargs: Dict[str, Any] = {
            "id": str(paper_num),
            "title": title,
            "authors": parsed["authors"],
            "editors": parsed["editors"],
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
        attachments = [
            (attachment["type"], AttachmentReference.from_file(attachment["dest"]))
            for attachment in paper["attachments"]
        ]
        if attachments:
            kwargs["attachments"] = attachments
        volume_obj.create_paper(**kwargs)

    if "sig" in meta:
        register_volume_with_sig(
            anthology, meta["sig"], volume_full_id, meta.get("booktitle")
        )
    add_parent_event(anthology, args.parent_event, volume_full_id)


def ingest_aclpub2(
    anthology: Anthology,
    ingestion_dir: str,
    seen_volume_ids: set[str],
    args: argparse.Namespace,
) -> None:
    meta = parse_conf_yaml(ingestion_dir)
    venue_abbrev = meta["anthology_venue_id"]
    venue_slug = ensure_venue(anthology, venue_abbrev, meta["event_name"])
    meta["path"] = Path(ingestion_dir)
    collection_id = meta["year"] + "." + venue_slug
    volume_name = meta["volume_name"].lower()
    volume_full_id = f"{collection_id}-{volume_name}"
    if volume_full_id in seen_volume_ids:
        raise Exception(f"Duplicate volume ID encountered: {volume_full_id}")
    seen_volume_ids.add(volume_full_id)

    papers = add_page_numbers(parse_paper_yaml(ingestion_dir), ingestion_dir)
    venue_name = meta["anthology_venue_id"].lower()
    pdfs_dest_dir = Path(create_dest_path(args.pdfs_dir, venue_name))

    proceedings_pdf_src_path = None
    for path in [
        meta["path"] / "proceedings.pdf",
        meta["path"] / "build" / "proceedings.pdf",
    ]:
        if path.exists():
            proceedings_pdf_src_path = str(path)
            break
    proceedings_pdf_dest_path = None
    if proceedings_pdf_src_path is not None:
        proceedings_pdf_dest_path = str(
            pdfs_dest_dir / f"{collection_id}-{volume_name}.pdf"
        )
        maybe_copy(proceedings_pdf_src_path, proceedings_pdf_dest_path)

    volume_data: Dict[int, Dict[str, Any]] = {
        0: {
            "anthology_id": f"{collection_id}-{volume_name}.0",
            "attachments": [],
            "archival": True,
        }
    }
    frontmatter_src_path = None
    for path in [
        meta["path"] / "front_matter.pdf",
        meta["path"] / "watermarked_pdfs" / "front_matter.pdf",
        meta["path"] / "watermarked_pdfs" / "0.pdf",
    ]:
        if path.exists():
            frontmatter_src_path = str(path)
            break
    if frontmatter_src_path is not None:
        frontmatter_dest_path = str(
            pdfs_dest_dir / f"{collection_id}-{volume_name}.0.pdf"
        )
        maybe_copy(frontmatter_src_path, frontmatter_dest_path)
        volume_data[0]["pdf_src"] = frontmatter_src_path
        volume_data[0]["pdf_dest"] = frontmatter_dest_path

    pdfs_src_dir = meta["path"] / "watermarked_pdfs"
    for paper_num, paper in enumerate(papers, start=1):
        paper_id_full = f"{collection_id}-{volume_name}.{paper_num}"
        volume_data[paper_num] = {
            "anthology_id": paper_id_full,
            "attachments": [],
            "archival": paper.get("archival", ARCHIVAL_DEFAULT),
        }
        if not volume_data[paper_num]["archival"]:
            continue
        paper_name = paper["file"]
        paper_id = str(paper["id"])
        pdf_src_path = (
            str(pdfs_src_dir / paper_name)
            if (pdfs_src_dir / paper_name).exists()
            else str(pdfs_src_dir / f"{paper_id}.pdf")
        )
        pdf_dest_path = str(pdfs_dest_dir / f"{paper_id_full}.pdf")
        maybe_copy(pdf_src_path, pdf_dest_path)
        volume_data[paper_num]["pdf_src"] = pdf_src_path
        volume_data[paper_num]["pdf_dest"] = pdf_dest_path
        if "attachments" in paper:
            attachs_dest_dir = create_dest_path(args.attachments_dir, venue_name)
            attachs_src_dir = meta["path"] / "attachments"
            for attachment in paper["attachments"]:
                file_path_value = attachment.get("file")
                if file_path_value is None:
                    continue
                file_path = Path(file_path_value)
                attach_src_path = None
                for p in [attachs_src_dir / file_path, attachs_src_dir / file_path.name]:
                    if p.exists():
                        attach_src_path = str(p)
                        break
                if attach_src_path is None:
                    continue
                attach_src_extension = attach_src_path.split(".")[-1]
                type_ = str(attachment["type"]).replace(" ", "")
                file_name = f"{collection_id}-{volume_name}.{paper_num}.{type_}.{attach_src_extension}"
                attach_dest_path = os.path.join(attachs_dest_dir, file_name).replace(
                    " ", ""
                )
                maybe_copy(attach_src_path, attach_dest_path)
                volume_data[paper_num]["attachments"].append(
                    {"src": attach_src_path, "dest": attach_dest_path, "type": type_}
                )

    collection = anthology.get_collection(collection_id)
    if collection is None:
        collection = anthology.collections.create(collection_id)
    if collection.get(volume_name) is not None:
        del collection[volume_name]
        collection.is_modified = True

    editors = [namespec_from_author(author) for author in meta["editors"]]
    venue_ids = [venue_name]
    if args.is_workshop:
        venue_ids.append("ws")
    volume_kwargs: Dict[str, Any] = {
        "id": volume_name,
        "title": normalize_latex_title(meta["book_title"]) or meta["book_title"],
        "year": str(meta["year"]),
        "type": VolumeType.PROCEEDINGS,
        "ingest_date": args.ingest_date,
        "editors": editors,
        "venue_ids": venue_ids,
        "publisher": meta.get("publisher"),
        "address": meta.get("location"),
        "month": meta.get("month"),
    }
    if "isbn" in meta and meta["isbn"]:
        volume_kwargs["isbn"] = str(meta["isbn"])
    if proceedings_pdf_src_path is not None and proceedings_pdf_dest_path is not None:
        volume_kwargs["pdf"] = pdf_reference_from_paths(
            anthology_id=f"{collection_id}-{volume_name}",
            src_path=proceedings_pdf_src_path,
            dest_path=proceedings_pdf_dest_path,
        )
    volume_obj = collection.create_volume(**volume_kwargs)

    frontmatter_kwargs: Dict[str, Any] = {
        "id": "0",
        "type": PaperType.FRONTMATTER,
        "title": normalize_latex_title(meta["book_title"]) or meta["book_title"],
        "editors": editors,
    }
    if "pdf_src" in volume_data[0] and "pdf_dest" in volume_data[0]:
        frontmatter_kwargs["pdf"] = pdf_reference_from_paths(
            anthology_id=f"{collection_id}-{volume_name}.0",
            src_path=volume_data[0]["pdf_src"],
            dest_path=volume_data[0]["pdf_dest"],
        )
    volume_obj.create_paper(**frontmatter_kwargs)

    for paper_num, volume_entry in sorted(volume_data.items()):
        if paper_num == 0 or not volume_entry["archival"]:
            continue
        paper = papers[paper_num - 1]
        title = normalize_latex_title(paper.get("title"))
        abstract = paper.get("abstract")
        if abstract is not None:
            abstract = normalize_abstract(abstract.replace("\n", ""))
        authors = [namespec_from_author(author) for author in paper.get("authors", [])]
        kwargs: Dict[str, Any] = {
            "id": str(paper_num),
            "title": title,
            "authors": authors,
            "pages": paper.get("pages"),
            "pdf": pdf_reference_from_paths(
                anthology_id=volume_entry["anthology_id"],
                src_path=volume_entry["pdf_src"],
                dest_path=volume_entry["pdf_dest"],
            ),
        }
        if abstract:
            kwargs["abstract"] = abstract
        attachment_refs = [
            (
                attachment["type"],
                attachment_reference_from_paths(
                    src_path=attachment["src"],
                    dest_path=attachment["dest"],
                ),
            )
            for attachment in volume_entry["attachments"]
            if "copyright" not in attachment["type"]
        ]
        if attachment_refs:
            kwargs["attachments"] = attachment_refs
        volume_obj.create_paper(**kwargs)

    add_parent_event(anthology, args.parent_event, volume_full_id)


def maybe_copy(source_path: str, dest_path: str):
    """Copies the file if it's different from the target."""
    try:
        if (
            not os.path.exists(dest_path)
            or PDFReference.from_file(source_path).checksum
            != PDFReference.from_file(dest_path).checksum
        ):
            log(f"Copying {source_path} -> {dest_path}")
            shutil.copyfile(source_path, dest_path)
    except Exception as e:
        log(f"Error copying {source_path} to {dest_path}: {e}")
        raise


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


def normalize_latex_title(text: Optional[str]) -> Optional[MarkupText]:
    """Normalize and apply truelist-based fixed-case protection for LaTeX text."""
    if text is None:
        return None
    markup = MarkupText.from_latex_maybe(text)
    elem = markup.to_xml()
    protect_fixedcase(elem)
    return MarkupText.from_xml(elem)


def normalize_abstract(text: Optional[str]) -> Optional[MarkupText]:
    """Normalize and apply truelist-based fixed-case protection for LaTeX text."""
    if text is None:
        return None
    return MarkupText.from_latex_maybe(text)


def make_name_spec(person) -> NameSpecification:
    first_text = " ".join(person.first_names + person.middle_names)
    last_text = " ".join(person.prelast_names + person.last_names)

    if person.lineage_names:
        last_text += ", " + " ".join(person.lineage_names)

    if last_text.strip() in {"", "-"}:
        last_text = first_text
        first_text = ""

    first_text = correct_caps(first_text.strip())
    last_text = correct_caps(last_text.strip())

    return NameSpecification(name=Name(first_text, last_text))


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

    page_range = bibentry.fields.get("pages")
    if page_range is not None:
        page_range = page_range.replace("--", "-")

    return {
        "title": normalize_latex_title(bibentry.fields.get("title")),
        "booktitle": normalize_latex_title(bibentry.fields.get("booktitle")),
        "month": bibentry.fields.get("month"),
        "year": bibentry.fields.get("year"),
        "address": bibentry.fields.get("address"),
        "publisher": bibentry.fields.get("publisher"),
        "pages": page_range,
        "abstract": normalize_abstract(bibentry.fields.get("abstract")),
        "doi": bibentry.fields.get("doi"),
        "language": bibentry.fields.get("language"),
        "authors": [
            make_name_spec(person) for person in bibentry.persons.get("author", [])
        ],
        "editors": [
            make_name_spec(person) for person in bibentry.persons.get("editor", [])
        ],
    }


def register_volume_with_sig(
    anthology: Anthology,
    sig_id: str,
    volume_full_id: str,
    booktitle: Optional[str] = None,
) -> None:
    """Register an ingested volume with a SIG if that SIG exists."""
    sig_key = sig_id.lower()
    if sig_key not in anthology.sigs:
        print(
            f"Warning: SIG '{sig_key}' not found; cannot register {volume_full_id}",
            file=sys.stderr,
        )
        return

    sig = anthology.sigs[sig_key]
    if volume_full_id not in sig.meetings:
        sig.meetings.append(volume_full_id)
    anthology.sigs.reverse[parse_id(volume_full_id)].add(sig_key)


def main(args):
    anthology_datadir = Path(args.anthology_dir) / "data"
    anthology = Anthology(datadir=anthology_datadir)

    anthology.collections.bibkeys.load()
    anthology.sigs.load()
    seen_volume_ids: set[str] = set()
    for source in args.proceedings:
        format_ = detect_ingestion_format(source)
        log(f"Detected {format_} format for {source}")
        if format_ == "aclpub":
            ingest_aclpub(anthology, source, seen_volume_ids, args)
        elif format_ == "aclpub2":
            ingest_aclpub2(anthology, source, seen_volume_ids, args)

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"SIG metadata is not yet automatically saved\\..*",
            category=UserWarning,
        )
        anthology.save_all()
    anthology.sigs.save()


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
    parser.add_argument(
        "--parent-event",
        default=None,
        help="Event ID (e.g., naacl-2025) workshop was colocated with",
    )
    args = parser.parse_args()

    main(args)
