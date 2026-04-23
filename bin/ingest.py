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

"""
Ingests data into the ACL Anthology from either ACLPUB or aclpub2 formats.

Each format has a metadata file (meta for ACLPUB, conference_details.yml for ACLPUB2)
that describes the volume to be ingested, and a set of papers with associated metadata
and files. These papers are abstracted away into a stream. The script copies the PDFs
and attachments to their final location in the anthology directory structure, creates
the relevant entries in the anthology data model, and links them together.
"""

import argparse
import iso639  # iso-639 pypi package
import logging as log
import pybtex.database.input.bibtex
import yaml
import re
import shutil
import sys
import PyPDF2

from datetime import datetime
from pathlib import Path
from slugify import slugify
from typing import Any, Dict, Iterator, Optional, List

from acl_anthology import Anthology
from acl_anthology.collections.types import PaperType, VolumeType
from acl_anthology.collections.volume import Volume
from acl_anthology.files import (
    AttachmentReference,
    PDFReference,
)
from acl_anthology.people import Name, NameSpecification
from acl_anthology.text import MarkupText
from acl_anthology.utils import setup_rich_logging
from fixedcase.protect import protect as protect_fixedcase

ARCHIVAL_DEFAULT = True


def read_meta(path: str) -> Dict[str, Any]:
    """Reads the ACLPUB meta file, which is a simple space-delimited key-value format with one entry per line. The "chair" key can be repeated for multiple chairs.
    Each chair is expected to be in BibTeX format, e.g., "Last name, First name(s)"."""
    meta = {"editors": []}
    with open(path) as instream:
        for line in instream:
            if re.match(r"^\s*$", line):
                continue
            key, value = line.rstrip().split(" ", maxsplit=1)
            if key.startswith("chair") or key.startswith("editor"):
                # Allow for Bib format, an occasional error in the meta file
                for value in value.split(" and "):
                    meta["editors"].append(value)
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
                paper_need_read_path = path
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


def correct_names(author: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fold middle name into the first name.
    """
    if author.get("middle_name") is not None:
        author["first_name"] = author["first_name"] + " " + author["middle_name"]
        del author["middle_name"]
    return author


def join_names(author: Dict[str, Any], fields=None) -> str:
    """
    Joins first and middle name, if present.
    """
    if fields is None:
        fields = ["first_name", "middle_name"]
    return " ".join(author[field] for field in fields if author.get(field) is not None)


def namespec_from_author(author: Dict[str, Any]) -> NameSpecification:
    """Creates a NameSpecification from an author dictionary (aclpub2)."""
    first_name = join_names(author).strip()
    last_name = (author.get("last_name") or "").strip()
    kwargs: Dict[str, Any] = {"name": Name(first_name if first_name else None, last_name)}
    if "orcid" in author and author["orcid"]:
        kwargs["orcid"] = str(author["orcid"])
    affiliation = author.get("institution") or author.get("affiliation")
    if affiliation:
        kwargs["affiliation"] = affiliation
    return NameSpecification(**kwargs)


def add_parent_event(
    anthology: Anthology, parent_event: Optional[str], volume_full_id: str
) -> None:
    """
    If a parent event is specified, then this volume should be listed in
    that parent's <event> block. This facilitates listing colocated volumes
    (mostly workshops, but also Findings) in a main volume's event page.
    """
    if parent_event is None:
        return

    event = anthology.get_event(parent_event)
    if event is None:
        print(f"No event node with id '{parent_event}' found", file=sys.stderr)
        return
    if volume := anthology.get_volume(volume_full_id) is None:
        print(f"No such ingested volume {volume_full_id}", file=sys.stderr)
        return

    if event in volume.get_events():
        print(
            f"Event {volume_full_id} already listed as colocated with {parent_event}, skipping",
            file=sys.stderr,
        )
    else:
        event.add_colocated(volume_full_id)
        print(
            f"Created event entry in {parent_event} for {volume_full_id}", file=sys.stderr
        )


def ensure_venue(anthology: Anthology, venue_abbrev: str, venue_title: str) -> str:
    """
    Looks for existing venue or creates a new one.
    """
    venue_slug = venue_slug_from_acronym(venue_abbrev)
    year = str(datetime.now().year)
    if year in venue_abbrev or year[2:] in venue_abbrev:
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
) -> Optional[Path]:
    """
    Searches for the full-book PDF.
    """
    path = Path(path)
    potential_paths = [
        path / "book.pdf",
        path / "cdrom" / "book.pdf",
        path / "cdrom" / f"{year}-{venue_name.lower()}-{volume_name}.pdf",
        path / "cdrom" / f"{venue_name.lower()}-{year}.{volume_name}.pdf",
        path / "cdrom" / f"{venue_name.upper()}-{year}.pdf",
    ]
    for book_path in potential_paths:
        if book_path.exists():
            return book_path
    return None


def _aclpub_attachment_map(
    root_path: str,
    year: str,
    collection_id: str,
    volume_name: str,
    attachments_dest_dir: str,
) -> Dict[int, List[Dict[str, Any]]]:
    attachments: Dict[int, List[Dict[str, Any]]] = {}
    additional_dir = Path(root_path) / "additional"
    if not additional_dir.exists():
        return attachments
    attachments_dest = Path(attachments_dest_dir)
    for attachment_path in additional_dir.iterdir():
        attachment_file = attachment_path.name
        if attachment_file.startswith("."):
            continue
        match = re.match(rf"{year}\..*-\w+\.(\d+)_?(\w+)\.(\w+)$", attachment_file)
        if match is None:
            print(
                f"* Warning: no attachment match for {attachment_file}", file=sys.stderr
            )
            continue
        paper_num, type_, ext = match.groups()
        paper_num = int(paper_num)
        file_name = f"{collection_id}-{volume_name}.{paper_num}.{type_}.{ext}"
        dest_path = attachments_dest / file_name
        attachments.setdefault(paper_num, []).append(
            {"src": attachment_path, "dest": dest_path, "type": type_}
        )
    return attachments


def _aclpub_frontmatter_data(
    root_path: str, collection_id: str, volume_name: str
) -> Optional[Dict[str, Any]]:
    bib0 = Path(root_path) / "bib" / "0.bib"
    if not bib0.exists():
        return None
    return read_bib_entry(bib0, "0")


def read_ingest_metadata(
    anthology: Anthology, source: str, format_: str, args: argparse.Namespace
) -> Dict[str, Any]:
    if format_ == "aclpub":
        source_path = Path(source)
        meta = read_meta(source_path / "meta")
        venue_abbrev = meta["abbrev"]
        venue_slug = ensure_venue(
            anthology, venue_abbrev, meta.get("title", venue_abbrev)
        )
        collection_id = meta["year"] + "." + venue_slug
        volume_name = meta.get("issue", meta["volume"]).lower()
        venue_name = venue_abbrev.lower()
        root_path = source_path / "cdrom"
        pdfs_dest_dir = Path(args.pdfs_dir) / venue_name
        attachments_dest_dir = Path(args.attachments_dir) / venue_name
        book_src = _find_book_pdf(source, str(meta["year"]), venue_name, volume_name)
        book_dest = (
            pdfs_dest_dir / f"{collection_id}-{volume_name}.pdf"
            if book_src is not None
            else None
        )
        frontmatter_data = _aclpub_frontmatter_data(root_path, collection_id, volume_name)
        volume_title = (
            (frontmatter_data or {}).get("title")
            or normalize_latex(meta.get("booktitle") or meta.get("title"))
            or f"{meta['abbrev']} {meta['year']}"
        )
        volume_editors = []
        if frontmatter_data is not None:
            volume_editors = frontmatter_data["editors"] + frontmatter_data["authors"]
        if not volume_editors and meta.get("editors"):
            volume_editors = [
                namespec_from_bib(pybtex.database.Person(name))
                for name in meta["editors"]
            ]
        return {
            "format": format_,
            "source": source_path,
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
            "journal_volume": meta.get("volume") if args.is_journal else None,
            "journal_issue": meta.get("issue") if args.is_journal else None,
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
        pdfs_dest_dir = Path(args.pdfs_dir) / venue_name
        attachments_dest_dir = Path(args.attachments_dir) / venue_name
        source_path = Path(source)
        proceedings_pdf_src = None
        for path in [
            source_path / "proceedings.pdf",
            source_path / "build" / "proceedings.pdf",
        ]:
            if path.exists():
                proceedings_pdf_src = path
                break

        proceedings_pdf_dest = (
            pdfs_dest_dir / f"{collection_id}-{volume_name}.pdf"
            if proceedings_pdf_src is not None
            else None
        )
        return {
            "format": format_,
            "source": source_path,
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
            "title": normalize_latex(meta["book_title"]) or meta["book_title"],
            "editors": [namespec_from_author(author) for author in meta["editors"]],
            "venue_ids": [venue_name] + (["ws"] if args.is_workshop else []),
            "isbn": str(meta["isbn"]) if meta.get("isbn") else None,
            "journal_volume": None,
            "root_path": source_path,
            "pdfs_dest_dir": pdfs_dest_dir,
            "attachments_dest_dir": attachments_dest_dir,
            "proceedings_pdf_src": proceedings_pdf_src,
            "proceedings_pdf_dest": proceedings_pdf_dest,
            "sig": None,
            "booktitle": meta.get("book_title"),
        }

    raise Exception(f"Unknown format: {format_}")


def iter_aclpub_papers(metadata: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """
    ACLPUB papers are read in from the cdrom/bib directory, which expects
    one paper per file. It parses this file to get paper information, and
    then finds the associated PDF in the cdrom/pdf directory. Attachments
    are read from the cdrom/additional directory.
    """
    collection_id = metadata["collection_id"]
    volume_name = metadata["volume_name"]
    root_path = Path(metadata["root_path"])
    pdfs_dest_dir = Path(metadata["pdfs_dest_dir"])
    attachments_map = _aclpub_attachment_map(
        root_path,
        metadata["year"],
        collection_id,
        volume_name,
        metadata["attachments_dest_dir"],
    )
    pdf_src_dir = root_path / "pdf"
    paper_entries: List[tuple[int, Path]] = []
    for pdf_path in pdf_src_dir.iterdir():
        if pdf_path.name.startswith("."):
            continue
        match = re.match(r".*?(\d+)\.pdf", pdf_path.name)
        if match is None:
            continue
        paper_entries.append((int(match[1]), pdf_path))

    for paper_num, pdf_path in sorted(paper_entries):
        anthology_id = f"{collection_id}-{volume_name}.{paper_num}"
        bib_path = root_path / "bib" / f"{pdf_path.stem}.bib"
        parsed = read_bib_entry(bib_path, paper_num)
        if parsed is None:
            continue
        pdf_src_path = pdf_path
        pdf_dest_path = pdfs_dest_dir / f"{anthology_id}.pdf"
        if paper_num == 0:
            yield {
                "id": "0",
                "type": PaperType.FRONTMATTER,
                "title": parsed.get("title") or metadata["title"],
                "authors": parsed["authors"],
                "editors": parsed["editors"],
                "pdf_src": pdf_src_path,
                "pdf_dest": pdf_dest_path,
                "anthology_id": anthology_id,
                "archival": True,
                "attachments": [],
            }
            continue
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
            "month": parsed.get("month"),
            "year": parsed.get("year"),
            "pdf_src": pdf_src_path,
            "pdf_dest": pdf_dest_path,
            "anthology_id": anthology_id,
            "archival": True,
            "attachments": attachments_map.get(paper_num, []),
        }


def iter_aclpub2_papers(metadata: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """
    The aclpub2 paper stream is read from the papers.yml file. Each entry
    contains a reference to the PDF file name, which is expected to be
    found in the watermarked_pdfs directory in the root folder.
    """
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
            frontmatter_src = path
            break
    frontmatter_dest = (
        Path(metadata["pdfs_dest_dir"]) / f"{collection_id}-{volume_name}.0.pdf"
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
            pdfs_src_dir / paper_name
            if (pdfs_src_dir / paper_name).exists()
            else pdfs_src_dir / f"{paper_id}.pdf"
        )
        pdf_dest_path = Path(metadata["pdfs_dest_dir"]) / f"{anthology_id}.pdf"
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
                    attach_src_path = p
                    break
            if attach_src_path is None:
                continue
            attach_src_extension = attach_src_path.suffix.lstrip(".")
            type_ = str(attachment["type"]).replace(" ", "")
            file_name = f"{collection_id}-{volume_name}.{paper_num}.{type_}.{attach_src_extension}"
            attach_dest_path = Path(metadata["attachments_dest_dir"]) / file_name
            attachments.append(
                {"src": attach_src_path, "dest": attach_dest_path, "type": type_}
            )
        abstract = paper.get("abstract")
        if abstract is not None:
            abstract = MarkupText.from_latex_maybe(abstract.replace("\n", ""))
        yield {
            "id": str(paper_num),
            "type": PaperType.PAPER,
            "title": normalize_latex(paper.get("title")),
            "authors": [
                namespec_from_author(author) for author in paper.get("authors", [])
            ],
            "editors": [],
            "abstract": abstract,
            "doi": paper.get("doi"),
            "pages": paper.get("pages"),
            "language": paper.get("language"),
            "month": paper.get("month"),
            "year": paper.get("year"),
            "pdf_src": pdf_src_path,
            "pdf_dest": pdf_dest_path,
            "anthology_id": anthology_id,
            "archival": True,
            "attachments": attachments,
        }


def iter_papers(metadata: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """
    Yields paper metadata dictionaries for the given volume, abstracting away the differences between ACLPUB and aclpub2 formats.
    """
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
    """
    Ingests the volume and its papers into the Anthology, agnostic to the underlying
    ingestion format.
    """
    volume_full_id = metadata["volume_full_id"]
    if volume_full_id in seen_volume_ids:
        raise Exception(f"Duplicate volume ID encountered: {volume_full_id}")
    seen_volume_ids.add(volume_full_id)

    collection = anthology.get_collection(metadata["collection_id"])
    if collection is None:
        collection = anthology.collections.create(metadata["collection_id"])
    if collection.get(metadata["volume_name"]) is not None:
        del collection[metadata["volume_name"]]

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
    volume_kwargs["journal_volume"] = metadata.get("journal_volume")
    volume_kwargs["journal_issue"] = metadata.get("journal_issue")
    volume_kwargs["isbn"] = metadata.get("isbn")
    if metadata.get("proceedings_pdf_src") and metadata.get("proceedings_pdf_dest"):
        maybe_copy(metadata["proceedings_pdf_src"], metadata["proceedings_pdf_dest"])
        volume_kwargs["pdf"] = PDFReference.from_file(
            str(metadata["proceedings_pdf_dest"])
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
            maybe_copy(paper["pdf_src"], paper["pdf_dest"], dry_run=args.dry_run)
            kwargs["pdf"] = PDFReference.from_file(str(paper["pdf_dest"]))
        for key in ("abstract", "doi", "pages"):
            value = paper.get(key)
            if value:
                kwargs[key] = value
        paper_month = paper.get("month")
        if paper_month and paper_month != metadata["month"]:
            kwargs["month"] = paper_month
        paper_year = paper.get("year")
        if paper_year and str(paper_year) != str(metadata["year"]):
            kwargs["year"] = str(paper_year)
        language = paper.get("language")
        if language:
            try:
                lang = iso639.languages.get(name=language)
                kwargs["language"] = lang.part3
            except KeyError:
                raise Exception(f"Can't find language '{language}'")
        attachment_refs = []
        for attachment in paper.get("attachments", []):
            # The copyright transfer forms are sometimes inclued as attachments,
            # but we don't want to publish them.
            if "copyright" in attachment["type"]:
                continue
            maybe_copy(attachment["src"], attachment["dest"], dry_run=args.dry_run)
            attachment_refs.append(
                (
                    attachment["type"],
                    AttachmentReference.from_file(str(attachment["dest"])),
                )
            )
        if attachment_refs:
            kwargs["attachments"] = attachment_refs
        volume_obj.create_paper(**kwargs)

    if metadata.get("sig"):
        register_volume_with_sig(
            anthology,
            metadata["sig"],
            volume_obj,
            metadata.get("booktitle"),
        )
    add_parent_event(anthology, args.parent_event, volume_full_id)


def maybe_copy(source_path: str, dest_path: str, dry_run: bool = False):
    """Copies the file if it's different from the target."""
    source = Path(source_path)
    dest = Path(dest_path)
    try:
        if dry_run:
            log.info(f"[dry-run] Skipping copy {source} -> {dest}")
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        if (
            not dest.exists()
            or PDFReference.from_file(str(source)).checksum
            != PDFReference.from_file(str(dest)).checksum
        ):
            log.info(f"Copying {source} -> {dest}")
            shutil.copyfile(source, dest)
    except Exception as e:
        log.error(f"Error copying {source} to {dest}: {e}")
        raise


def venue_slug_from_acronym(acronym: str) -> str:
    """Build a venue slug from an acronym (legacy-compatible behavior)."""
    slug = slugify(acronym.replace("-", ""))
    if re.match(r"^[a-z][a-z0-9]+$", slug) is None:
        raise Exception(f"Invalid venue slug '{slug}' derived from '{acronym}'")
    return slug


def normalize_latex(text: Optional[str], is_title: bool = True) -> Optional[MarkupText]:
    """Normalize and apply truelist-based fixed-case protection for (potentially) LaTeX
    text. If is_title is true, we also apply fixed-case protection. Used for both
    titles and abstracts."""
    if text is None:
        return None
    markup = MarkupText.from_latex_maybe(text)
    if is_title:
        elem = markup.to_xml()
        protect_fixedcase(elem)
        return MarkupText.from_xml(elem)
    else:
        return markup


def namespec_from_bib(person) -> NameSpecification:
    """Creates a NameSpecification from a pybtex Person object."""
    first_text = " ".join(person.first_names + person.middle_names)
    last_text = " ".join(person.prelast_names + person.last_names)

    if person.lineage_names:
        last_text += ", " + " ".join(person.lineage_names)

    if last_text.strip() in {"", "-"}:
        last_text = first_text
        first_text = ""

    first_text = first_text.strip()
    last_text = last_text.strip()

    return NameSpecification(name=Name(first_text, last_text))


def read_bib_entry(bibfilename: Path | str, paper_id: str) -> Optional[Dict[str, Any]]:
    """Parse a single-entry BibTeX file into structured metadata."""

    try:
        bibdata = pybtex.database.input.bibtex.Parser().parse_file(bibfilename)
    except pybtex.scanner.PybtexSyntaxError:
        log.error(f"error parsing {bibfilename}")
        raise

    if len(bibdata.entries) != 1:
        log.warning(f"more than one entry in {bibfilename}")

    bibentry = next(iter(bibdata.entries.values()))
    if len(bibentry.fields) == 0:
        log.error(f"parsing bib of paper {paper_id} failed")
        sys.exit(1)

    page_range = bibentry.fields.get("pages")
    if page_range is not None:
        page_range = page_range.replace("--", "-")

    return {
        "title": normalize_latex(bibentry.fields.get("title")),
        "booktitle": normalize_latex(bibentry.fields.get("booktitle")),
        "month": bibentry.fields.get("month"),
        "year": bibentry.fields.get("year"),
        "address": bibentry.fields.get("address"),
        "publisher": bibentry.fields.get("publisher"),
        "pages": page_range,
        "abstract": normalize_latex(bibentry.fields.get("abstract"), is_title=False),
        "doi": bibentry.fields.get("doi"),
        "language": bibentry.fields.get("language"),
        "authors": [
            namespec_from_bib(person) for person in bibentry.persons.get("author", [])
        ],
        "editors": [
            namespec_from_bib(person) for person in bibentry.persons.get("editor", [])
        ],
    }


def register_volume_with_sig(
    anthology: Anthology,
    sig_id: str,
    volume: Volume,
    booktitle: Optional[str] = None,
) -> None:
    """Register an ingested volume with a SIG if that SIG exists."""
    sig_key = sig_id.lower()
    if sig_key not in anthology.sigs:
        print(
            f"Warning: SIG '{sig_key}' not found; cannot register {volume.full_id}",
            file=sys.stderr,
        )
        return

    sig = anthology.sigs[sig_key]
    if volume.full_id not in sig.meetings:
        sig.meetings.append(volume.full_id)
    anthology.sigs.reverse[volume.full_id_tuple].add(sig_key)


def main(args):
    setup_rich_logging()
    anthology = Anthology.from_within_repo()

    anthology.load_all()

    seen_volume_ids: set[str] = set()
    for source in args.proceedings:
        format_ = detect_ingestion_format(source)
        log.info(f"Detected {format_} format for {source}")
        metadata = read_ingest_metadata(anthology, source, format_, args)
        ingest(
            anthology=anthology,
            metadata=metadata,
            paper_stream=iter_papers(metadata),
            seen_volume_ids=seen_volume_ids,
            args=args,
        )

    anthology.save_all()


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
    pdfs_path = Path.home() / "anthology-files" / "pdf"
    parser.add_argument(
        "--pdfs-dir", "-p", default=pdfs_path, help="Root path for placement of PDF files"
    )
    attachments_path = Path.home() / "anthology-files" / "attachments"
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run ingestion without copying paper/frontmatter PDFs and attachments.",
    )
    args = parser.parse_args()

    main(args)
