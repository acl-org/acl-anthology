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
from typing import Any, Dict, Iterator, Optional, List

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
        venue = anthology.venues.create(
            id=venue_slug, acronym=venue_abbrev, name=venue_title
        )
        venue.save()
    return venue_slug


def _find_book_pdf(
    path: str, year: str, venue_name: str, volume_name: str
) -> Optional[str]:
    potential_names = [
        os.path.join(path, "book.pdf"),
        os.path.join(path, "cdrom", "book.pdf"),
        os.path.join(
            path,
            "cdrom",
            f"{year}-{venue_name.lower()}-{volume_name}.pdf",
            f"{venue_name.lower()}-{year}.{volume_name}.pdf",
        ),
        os.path.join(path, "cdrom", f"{venue_name.upper()}-{year}.pdf"),
    ]
    for book_rel_path in potential_names:
        if os.path.exists(book_rel_path):
            return book_rel_path
    return None


def _aclpub_attachment_map(
    root_path: str,
    year: str,
    collection_id: str,
    volume_name: str,
    attachments_dest_dir: str,
) -> Dict[int, List[Dict[str, str]]]:
    attachments: Dict[int, List[Dict[str, str]]] = {}
    additional_dir = os.path.join(root_path, "additional")
    if not os.path.exists(additional_dir):
        return attachments
    os.makedirs(attachments_dest_dir, exist_ok=True)
    for attachment_file in os.listdir(additional_dir):
        if os.path.basename(attachment_file).startswith("."):
            continue
        attachment_file_path = os.path.join(additional_dir, attachment_file)
        match = re.match(rf"{year}\..*-\w+\.(\d+)_?(\w+)\.(\w+)$", attachment_file)
        if match is None:
            print(
                f"* Warning: no attachment match for {attachment_file}", file=sys.stderr
            )
            continue
        paper_num, type_, ext = match.groups()
        paper_num = int(paper_num)
        file_name = f"{collection_id}-{volume_name}.{paper_num}.{type_}.{ext}"
        dest_path = os.path.join(attachments_dest_dir, file_name)
        attachments.setdefault(paper_num, []).append(
            {"src": attachment_file_path, "dest": dest_path, "type": type_}
        )
    return attachments


def _aclpub_frontmatter_data(
    root_path: str, collection_id: str, volume_name: str
) -> Optional[Dict[str, Any]]:
    bib0 = os.path.join(root_path, "bib", "0.bib")
    if not os.path.exists(bib0):
        return None
    return read_bib_entry(bib0, f"{collection_id}-{volume_name}.0")


def read_ingest_metadata(
    anthology: Anthology, source: str, format_: str, args: argparse.Namespace
) -> Dict[str, Any]:
    if format_ == "aclpub":
        meta = read_meta(os.path.join(source, "meta"))
        venue_abbrev = meta["abbrev"]
        venue_slug = ensure_venue(
            anthology, venue_abbrev, meta.get("title", venue_abbrev)
        )
        collection_id = meta["year"] + "." + venue_slug
        volume_name = meta["volume"].lower()
        venue_name = venue_abbrev.lower()
        root_path = os.path.join(source, "cdrom")
        pdfs_dest_dir = os.path.join(args.pdfs_dir, venue_name)
        os.makedirs(pdfs_dest_dir, exist_ok=True)
        attachments_dest_dir = os.path.join(args.attachments_dir, venue_name)
        book_src = _find_book_pdf(source, str(meta["year"]), venue_name, volume_name)
        book_dest = (
            os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}.pdf")
            if book_src is not None
            else None
        )
        frontmatter_data = _aclpub_frontmatter_data(root_path, collection_id, volume_name)
        volume_title = (
            (frontmatter_data or {}).get("title")
            or normalize_latex_title(meta.get("booktitle") or meta.get("title"))
            or f"{meta['abbrev']} {meta['year']}"
        )
        volume_editors = []
        if frontmatter_data is not None:
            volume_editors = frontmatter_data["editors"] + frontmatter_data["authors"]
        return {
            "format": format_,
            "source": source,
            "raw_meta": meta,
            "collection_id": collection_id,
            "volume_name": volume_name,
            "volume_full_id": f"{collection_id}-{volume_name}",
            "venue_name": venue_name,
            "venue_abbrev": venue_abbrev,
            "volume_type": (
                VolumeType.JOURNAL if args.is_journal else VolumeType.PROCEEDINGS
            ),
            "year": str(meta["year"]),
            "month": (frontmatter_data or {}).get("month") or meta.get("month"),
            "publisher": (frontmatter_data or {}).get("publisher")
            or meta.get("publisher"),
            "address": (frontmatter_data or {}).get("address") or meta.get("location"),
            "title": volume_title,
            "editors": volume_editors,
            "venue_ids": [venue_name] + (["ws"] if args.is_workshop else []),
            "isbn": meta.get("isbn"),
            "journal_volume": volume_name if args.is_journal else None,
            "root_path": root_path,
            "pdfs_dest_dir": pdfs_dest_dir,
            "attachments_dest_dir": attachments_dest_dir,
            "proceedings_pdf_src": book_src,
            "proceedings_pdf_dest": book_dest,
            "sig": meta.get("sig"),
            "booktitle": meta.get("booktitle"),
        }

    if format_ == "aclpub2":
        meta = parse_conf_yaml(source)
        venue_abbrev = meta["anthology_venue_id"]
        venue_slug = ensure_venue(anthology, venue_abbrev, meta["event_name"])
        collection_id = meta["year"] + "." + venue_slug
        volume_name = meta["volume_name"].lower()
        venue_name = venue_abbrev.lower()
        pdfs_dest_dir = create_dest_path(args.pdfs_dir, venue_name)
        attachments_dest_dir = create_dest_path(args.attachments_dir, venue_name)
        source_path = Path(source)
        proceedings_pdf_src = None
        for path in [
            source_path / "proceedings.pdf",
            source_path / "build" / "proceedings.pdf",
        ]:
            if path.exists():
                proceedings_pdf_src = str(path)
                break
        proceedings_pdf_dest = (
            os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}.pdf")
            if proceedings_pdf_src is not None
            else None
        )
        return {
            "format": format_,
            "source": source,
            "raw_meta": meta,
            "collection_id": collection_id,
            "volume_name": volume_name,
            "volume_full_id": f"{collection_id}-{volume_name}",
            "venue_name": venue_name,
            "venue_abbrev": venue_abbrev,
            "volume_type": VolumeType.PROCEEDINGS,
            "year": str(meta["year"]),
            "month": meta.get("month"),
            "publisher": meta.get("publisher"),
            "address": meta.get("location"),
            "title": normalize_latex_title(meta["book_title"]) or meta["book_title"],
            "editors": [namespec_from_author(author) for author in meta["editors"]],
            "venue_ids": [venue_name] + (["ws"] if args.is_workshop else []),
            "isbn": str(meta["isbn"]) if meta.get("isbn") else None,
            "journal_volume": None,
            "root_path": str(source_path),
            "pdfs_dest_dir": pdfs_dest_dir,
            "attachments_dest_dir": attachments_dest_dir,
            "proceedings_pdf_src": proceedings_pdf_src,
            "proceedings_pdf_dest": proceedings_pdf_dest,
            "sig": None,
            "booktitle": meta.get("book_title"),
        }

    raise Exception(f"Unknown format: {format_}")


def iter_aclpub_papers(metadata: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    collection_id = metadata["collection_id"]
    volume_name = metadata["volume_name"]
    root_path = metadata["root_path"]
    pdfs_dest_dir = metadata["pdfs_dest_dir"]
    attachments_map = _aclpub_attachment_map(
        root_path,
        metadata["year"],
        collection_id,
        volume_name,
        metadata["attachments_dest_dir"],
    )
    pdf_src_dir = os.path.join(root_path, "pdf")
    paper_entries: List[tuple[int, str]] = []
    for pdf_file in os.listdir(pdf_src_dir):
        if os.path.basename(pdf_file).startswith("."):
            continue
        match = re.match(r".*?(\d+)\.pdf", pdf_file)
        if match is None:
            continue
        paper_entries.append((int(match[1]), pdf_file))

    for paper_num, pdf_file in sorted(paper_entries):
        anthology_id = f"{collection_id}-{volume_name}.{paper_num}"
        bib_path = os.path.join(root_path, "bib", pdf_file.replace(".pdf", ".bib"))
        parsed = read_bib_entry(bib_path, anthology_id)
        if parsed is None:
            continue
        if paper_num == 0:
            yield {
                "id": "0",
                "type": PaperType.FRONTMATTER,
                "title": parsed.get("title") or metadata["title"],
                "authors": parsed["authors"],
                "editors": parsed["editors"],
                "pdf_src": metadata["proceedings_pdf_src"],
                "pdf_dest": metadata["proceedings_pdf_dest"],
                "anthology_id": anthology_id,
                "archival": True,
                "attachments": [],
            }
            continue
        pdf_src_path = os.path.join(pdf_src_dir, pdf_file)
        pdf_dest_path = os.path.join(pdfs_dest_dir, f"{anthology_id}.pdf")
        yield {
            "id": str(paper_num),
            "type": PaperType.PAPER,
            "title": parsed["title"],
            "authors": parsed["authors"],
            "editors": parsed["editors"],
            "abstract": parsed.get("abstract"),
            "doi": parsed.get("doi"),
            "pages": parsed.get("pages"),
            "language": parsed.get("language"),
            "pdf_src": pdf_src_path,
            "pdf_dest": pdf_dest_path,
            "anthology_id": anthology_id,
            "archival": True,
            "attachments": attachments_map.get(paper_num, []),
        }


def iter_aclpub2_papers(metadata: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    collection_id = metadata["collection_id"]
    volume_name = metadata["volume_name"]
    source_path = Path(metadata["source"])
    papers = add_page_numbers(parse_paper_yaml(metadata["source"]), metadata["source"])
    pdfs_src_dir = source_path / "watermarked_pdfs"

    frontmatter_src = None
    for path in [
        source_path / "front_matter.pdf",
        source_path / "watermarked_pdfs" / "front_matter.pdf",
        source_path / "watermarked_pdfs" / "0.pdf",
    ]:
        if path.exists():
            frontmatter_src = str(path)
            break
    frontmatter_dest = (
        os.path.join(metadata["pdfs_dest_dir"], f"{collection_id}-{volume_name}.0.pdf")
        if frontmatter_src is not None
        else None
    )
    yield {
        "id": "0",
        "type": PaperType.FRONTMATTER,
        "title": metadata["title"],
        "authors": [],
        "editors": metadata["editors"],
        "pdf_src": frontmatter_src,
        "pdf_dest": frontmatter_dest,
        "anthology_id": f"{collection_id}-{volume_name}.0",
        "archival": True,
        "attachments": [],
    }

    attachments_src_dir = source_path / "attachments"
    for paper_num, paper in enumerate(papers, start=1):
        archival = paper.get("archival", ARCHIVAL_DEFAULT)
        anthology_id = f"{collection_id}-{volume_name}.{paper_num}"
        if not archival:
            continue
        paper_name = paper["file"]
        paper_id = str(paper["id"])
        pdf_src_path = (
            str(pdfs_src_dir / paper_name)
            if (pdfs_src_dir / paper_name).exists()
            else str(pdfs_src_dir / f"{paper_id}.pdf")
        )
        pdf_dest_path = os.path.join(metadata["pdfs_dest_dir"], f"{anthology_id}.pdf")
        attachments = []
        for attachment in paper.get("attachments", []):
            file_path_value = attachment.get("file")
            if file_path_value is None:
                continue
            file_path = Path(file_path_value)
            attach_src_path = None
            for p in [
                attachments_src_dir / file_path,
                attachments_src_dir / file_path.name,
            ]:
                if p.exists():
                    attach_src_path = str(p)
                    break
            if attach_src_path is None:
                continue
            attach_src_extension = attach_src_path.split(".")[-1]
            type_ = str(attachment["type"]).replace(" ", "")
            file_name = f"{collection_id}-{volume_name}.{paper_num}.{type_}.{attach_src_extension}"
            attach_dest_path = os.path.join(
                metadata["attachments_dest_dir"], file_name
            ).replace(" ", "")
            attachments.append(
                {"src": attach_src_path, "dest": attach_dest_path, "type": type_}
            )
        abstract = paper.get("abstract")
        if abstract is not None:
            abstract = normalize_abstract(abstract.replace("\n", ""))
        yield {
            "id": str(paper_num),
            "type": PaperType.PAPER,
            "title": normalize_latex_title(paper.get("title")),
            "authors": [
                namespec_from_author(author) for author in paper.get("authors", [])
            ],
            "editors": [],
            "abstract": abstract,
            "doi": paper.get("doi"),
            "pages": paper.get("pages"),
            "language": paper.get("language"),
            "pdf_src": pdf_src_path,
            "pdf_dest": pdf_dest_path,
            "anthology_id": anthology_id,
            "archival": True,
            "attachments": attachments,
        }


def iter_papers(metadata: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    if metadata["format"] == "aclpub":
        yield from iter_aclpub_papers(metadata)
        return
    if metadata["format"] == "aclpub2":
        yield from iter_aclpub2_papers(metadata)
        return
    raise Exception(f"Unknown metadata format: {metadata['format']}")


def ingest(
    anthology: Anthology,
    metadata: Dict[str, Any],
    paper_stream: Iterator[Dict[str, Any]],
    seen_volume_ids: set[str],
    args: argparse.Namespace,
) -> None:
    volume_full_id = metadata["volume_full_id"]
    if volume_full_id in seen_volume_ids:
        raise Exception(f"Duplicate volume ID encountered: {volume_full_id}")
    seen_volume_ids.add(volume_full_id)

    collection = anthology.get_collection(metadata["collection_id"])
    if collection is None:
        collection = anthology.collections.create(metadata["collection_id"])
    if collection.get(metadata["volume_name"]) is not None:
        del collection[metadata["volume_name"]]
        collection.is_modified = True

    volume_kwargs: Dict[str, Any] = {
        "id": metadata["volume_name"],
        "title": metadata["title"],
        "year": metadata["year"],
        "type": metadata["volume_type"],
        "ingest_date": args.ingest_date,
        "editors": metadata["editors"],
        "venue_ids": metadata["venue_ids"],
        "publisher": metadata["publisher"],
        "address": metadata["address"],
        "month": metadata["month"],
    }
    if metadata.get("journal_volume") is not None:
        volume_kwargs["journal_volume"] = metadata["journal_volume"]
    if metadata.get("isbn"):
        volume_kwargs["isbn"] = metadata["isbn"]
    if metadata.get("proceedings_pdf_src") and metadata.get("proceedings_pdf_dest"):
        maybe_copy(metadata["proceedings_pdf_src"], metadata["proceedings_pdf_dest"])
        volume_kwargs["pdf"] = pdf_reference_from_paths(
            anthology_id=metadata["volume_full_id"],
            src_path=metadata["proceedings_pdf_src"],
            dest_path=metadata["proceedings_pdf_dest"],
        )

    volume_obj = collection.create_volume(**volume_kwargs)

    for paper in paper_stream:
        if not paper.get("archival", True):
            continue
        kwargs: Dict[str, Any] = {
            "id": paper["id"],
            "type": paper["type"],
            "title": paper["title"],
            "authors": paper.get("authors", []),
            "editors": paper.get("editors", []),
        }
        if paper.get("pdf_src") and paper.get("pdf_dest"):
            maybe_copy(paper["pdf_src"], paper["pdf_dest"])
            kwargs["pdf"] = pdf_reference_from_paths(
                anthology_id=paper["anthology_id"],
                src_path=paper["pdf_src"],
                dest_path=paper["pdf_dest"],
            )
        for key in ("abstract", "doi", "pages"):
            value = paper.get(key)
            if value:
                kwargs[key] = value
        language = paper.get("language")
        if language:
            try:
                lang = iso639.languages.get(name=language)
                kwargs["language"] = lang.part3
            except KeyError:
                raise Exception(f"Can't find language '{language}'")
        attachment_refs = []
        for attachment in paper.get("attachments", []):
            if "copyright" in attachment["type"]:
                continue
            maybe_copy(attachment["src"], attachment["dest"])
            attachment_refs.append(
                (
                    attachment["type"],
                    attachment_reference_from_paths(
                        src_path=attachment["src"],
                        dest_path=attachment["dest"],
                    ),
                )
            )
        if attachment_refs:
            kwargs["attachments"] = attachment_refs
        volume_obj.create_paper(**kwargs)

    if metadata.get("sig"):
        register_volume_with_sig(
            anthology,
            metadata["sig"],
            volume_full_id,
            metadata.get("booktitle"),
        )
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
        metadata = read_ingest_metadata(anthology, source, format_, args)
        ingest(
            anthology=anthology,
            metadata=metadata,
            paper_stream=iter_papers(metadata),
            seen_volume_ids=seen_volume_ids,
            args=args,
        )

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
        "proceedings",
        nargs="+",
        help="List of paths to proceedings directories (ACLPUB or aclpub2).",
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
