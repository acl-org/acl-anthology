#! /usr/bin/env python3
"""
Ingest MIT Press journal metadata (TACL/CL) into Anthology XML using DOI discovery
from Crossref.

This script is a single entrypoint for both discovery and ingestion:

1) Discover candidate DOIs from Crossref for a venue/year.
2) Resolve paper metadata from Crossref payloads.
3) Skip already-ingested DOIs in the target collection.
4) Ingest new papers into data/xml/<year>.<venue>.xml using the Python library.
5) Download PDFs via DOI URL and place them under anthology-files/pdf/<venue>/.

Example usage:

    bin/ingest_mitpress.py --venue tacl --year 2025 --volume 13 --dry-run
    bin/ingest_mitpress.py --venue cl --year 2025

Authors: David Stap (earlier versions: Arya D. McCarthy, Matt Post, Marcel Bollmann)
"""

import argparse
import html
import logging
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import requests
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import ArrayObject, DecodedStreamObject, NameObject

from acl_anthology import Anthology
from acl_anthology.files import PDFReference
from acl_anthology.people import Name, NameSpecification as NameSpec
from acl_anthology.text import MarkupText
from acl_anthology.utils import setup_rich_logging

from fixedcase.protect import protect
from anthology.utils import retrieve_url

__version__ = "0.7"

TACL = "tacl"
CL = "cl"

MONTHS = {
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    "10": "October",
    "11": "November",
    "12": "December",
}

VENUE_CONFIG = {
    TACL: {
        "journal_title": "Transactions of the Association for Computational Linguistics",
        "issn": ["2307-387X"],
        "booktitle_template": (
            "Transactions of the Association for Computational Linguistics, "
            "Volume {volume}"
        ),
        "default_issue_id": "1",
    },
    CL: {
        "journal_title": "Computational Linguistics",
        "issn": ["0891-2017", "1530-9312"],
        "booktitle_template": (
            "Computational Linguistics, Volume {volume}, Issue {issue} - {month} {year}"
        ),
        "default_issue_id": None,
    },
}

CROSSREF_API = "https://api.crossref.org/works"
PDF_URL_TEMPLATE = "https://www.mitpressjournals.org/doi/pdf/{doi}"
WATERMARK_MARKERS = (
    "Downloaded from http://direct.mit.edu",
    "Downloaded from https://direct.mit.edu",
    "Downloaded from http://www.mitpressjournals.org/doi/pdf/",
    "Downloaded from https://www.mitpressjournals.org/doi/pdf/",
)
PDF_DOWNLOAD_RETRIES = 5
PDF_DOWNLOAD_RETRY_BASE_DELAY_SEC = 2

# ACLPUB2 ingestion gets richer structured name fields (first/middle/last), but
# Crossref only gives us `given` + `family`. We therefore need a small heuristic
# patch layer for common particle splits that Crossref gets wrong.
TRAILING_SINGLE_TOKEN_PARTICLES = {
    "al",
    "bin",
    "bint",
    "da",
    "de",
    "del",
    "di",
    "dos",
    "du",
    "la",
    "le",
    "van",
    "von",
}
TRAILING_TWO_TOKEN_PARTICLES = {
    ("de", "la"),
    ("de", "las"),
    ("de", "los"),
    ("van", "den"),
    ("van", "der"),
}


def collapse_spaces(text: str) -> str:
    return " ".join(text.split())


def normalize_doi(value: str) -> str:
    doi = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi.strip()


def parse_crossref_abstract(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    text = strip_inline_markup(value)

    # Some JATS abstracts include a leading "Abstract" heading.
    text = text.strip()
    if text.lower().startswith("abstract "):
        text = text[9:]

    text = collapse_spaces(text)
    return text or None


def _decode_markup_text(value: str) -> str:
    text = value
    if "&lt;" in text or "&gt;" in text or "&amp;lt;" in text or "&amp;gt;" in text:
        import html

        for _ in range(3):
            decoded = html.unescape(text)
            if decoded == text:
                break
            text = decoded
    return text


def strip_inline_markup(value: str) -> str:
    text = _decode_markup_text(value)
    text = text.replace("<jats:", "<").replace("</jats:", "</")

    if "<" in text and ">" in text:
        try:
            from lxml import etree

            node = etree.fromstring(f"<root>{text}</root>".encode("utf-8"))
            text = " ".join(node.itertext())
        except Exception:
            text = re.sub(r"</?[A-Za-z0-9:_-]+(?:\s+[^<>]*)?>", " ", text)

    # One more pass for leftover escaped tags, then remove any raw tags.
    text = html.unescape(text)
    text = re.sub(r"&lt;\s*/?\s*[A-Za-z0-9:_-]+(?:\s+[^&<>]*)?&gt;", " ", text)
    text = re.sub(r"</?[A-Za-z0-9:_-]+(?:\s+[^<>]*)?>", " ", text)
    return collapse_spaces(text)


def _join_spaced_mixedcase_tokens(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(0)
        joined = token.replace(" ", "")
        if any(c.islower() for c in joined) and any(c.isupper() for c in joined):
            return joined
        return token

    return re.sub(r"\b(?:[A-Za-z]\s+){2,}[A-Za-z]\b", repl, text)


def parse_crossref_title(value: str) -> str:
    text = strip_inline_markup(value)

    text = collapse_spaces(text)
    text = _join_spaced_mixedcase_tokens(text)
    text = re.sub(r"\s+([:;,.!?])", r"\1", text)
    return text


def parse_month_from_crossref(item: dict[str, Any]) -> Optional[str]:
    for field in ("published-print", "published-online", "issued"):
        payload = item.get(field)
        if not isinstance(payload, dict):
            continue
        date_parts = payload.get("date-parts")
        if not date_parts or not date_parts[0]:
            continue
        first = date_parts[0]
        if len(first) < 2:
            continue
        month_num = f"{int(first[1]):02d}"
        return MONTHS.get(month_num)
    return None


def parse_year_from_crossref(item: dict[str, Any]) -> Optional[int]:
    for field in ("published-print", "published-online", "issued"):
        payload = item.get(field)
        if not isinstance(payload, dict):
            continue
        date_parts = payload.get("date-parts")
        if not date_parts or not date_parts[0]:
            continue
        first = date_parts[0]
        if not first:
            continue
        return int(first[0])
    return None


def parse_pages(page: Optional[str]) -> Optional[str]:
    if not page:
        return None
    page_text = collapse_spaces(page)
    if not page_text:
        return None

    if "-" in page_text and "–" not in page_text:
        parts = [p.strip() for p in page_text.split("-") if p.strip()]
        if len(parts) == 2:
            return f"{parts[0]}–{parts[1]}"
    return page_text


def start_page_for_sorting(page_text: Optional[str]) -> int:
    if not page_text:
        return 10**9
    head = page_text.split("–")[0].split("-")[0].strip()
    try:
        return int(head)
    except ValueError:
        return 10**9


def normalize_crossref_author_name_split(
    given: Optional[str], family: str
) -> tuple[Optional[str], str]:
    """
    Fix common Crossref split errors where a surname particle is attached to
    the end of given name, e.g., "Alejandro Sánchez de" + "Castro".

    Note:
    Unlike ACLPUB2 ingestion, we don't have separate middle-name metadata here;
    only `given` and `family` are provided by Crossref.
    """
    given_text = collapse_spaces(given) if given else None
    family_text = collapse_spaces(family)
    if not given_text:
        return None, family_text

    given_tokens = given_text.split()
    family_tokens = family_text.split()
    if len(given_tokens) < 2:
        return given_text, family_text

    moved_tokens: list[str] = []

    # Prefer two-token particles like "de la" and "van der".
    suffix2 = tuple(token.lower() for token in given_tokens[-2:])
    if suffix2 in TRAILING_TWO_TOKEN_PARTICLES:
        # Avoid duplicating particles already in the family field.
        if [t.lower() for t in family_tokens[:2]] != list(suffix2):
            moved_tokens = given_tokens[-2:]
            given_tokens = given_tokens[:-2]

    if not moved_tokens:
        suffix1 = given_tokens[-1].lower()
        if suffix1 in TRAILING_SINGLE_TOKEN_PARTICLES:
            if not family_tokens or family_tokens[0].lower() != suffix1:
                moved_tokens = [given_tokens[-1]]
                given_tokens = given_tokens[:-1]

    # Keep at least one token in given name.
    if moved_tokens and given_tokens:
        fixed_given = " ".join(given_tokens)
        fixed_family = " ".join(moved_tokens + family_tokens)
        logging.info(
            'Adjusted author name split: given="%s", family="%s" -> given="%s", family="%s"',
            given_text,
            family_text,
            fixed_given,
            fixed_family,
        )
        return fixed_given, fixed_family

    return given_text, family_text


def is_target_journal(item: dict[str, Any], venue: str) -> bool:
    config = VENUE_CONFIG[venue]
    expected_title = config["journal_title"].lower()

    container_titles = item.get("container-title") or []
    for title in container_titles:
        if isinstance(title, str) and title.strip().lower() == expected_title:
            return True

    issn_values = set(item.get("ISSN") or [])
    for issn in config["issn"]:
        if issn in issn_values:
            return True

    return False


def crossref_request_json(
    session: requests.Session,
    params: dict[str, Any],
    retries: int = 4,
    timeout_sec: int = 45,
) -> dict[str, Any]:
    headers = {
        "User-Agent": "acl-anthology-ingest-mitpress/0.7 (mailto:acl-anthology@aclweb.org)"
    }

    for attempt in range(1, retries + 1):
        try:
            response = session.get(
                CROSSREF_API,
                params=params,
                headers=headers,
                timeout=timeout_sec,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            wait_s = min(2**attempt, 10)
            logging.warning("Crossref request failed (%s). Retrying in %ss", exc, wait_s)
            time.sleep(wait_s)

    raise RuntimeError("Unreachable retry loop")


def discover_crossref_items(
    venue: str,
    year: int,
    volume: Optional[str],
) -> list[dict[str, Any]]:
    filters = [
        f"from-pub-date:{year}-01-01",
        f"until-pub-date:{year}-12-31",
        "prefix:10.1162",
        "type:journal-article",
    ]

    config = VENUE_CONFIG[venue]
    if config["issn"]:
        filters.append(f"issn:{config['issn'][0]}")

    rows = 200
    cursor = "*"
    seen_dois: set[str] = set()
    items: list[dict[str, Any]] = []

    session = requests.Session()

    while True:
        params = {
            "filter": ",".join(filters),
            "rows": rows,
            "cursor": cursor,
            "select": (
                "DOI,title,author,abstract,page,issue,volume,"
                "container-title,ISSN,published-print,published-online,issued,type"
            ),
        }
        payload = crossref_request_json(session, params)
        message = payload.get("message", {})
        batch = message.get("items", [])

        if not batch:
            break

        for item in batch:
            raw_doi = item.get("DOI")
            if not raw_doi:
                continue
            doi = normalize_doi(str(raw_doi))
            if doi in seen_dois:
                continue
            if not is_target_journal(item, venue):
                continue

            item["DOI"] = doi
            if parse_year_from_crossref(item) != year:
                continue
            if volume is not None and str(item.get("volume", "")).strip() != str(volume):
                continue

            seen_dois.add(doi)
            items.append(item)

        next_cursor = message.get("next-cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return items


def convert_crossref_item_to_paper(
    item: dict[str, Any], venue: str
) -> Optional[dict[str, Any]]:
    doi = item.get("DOI")
    if not doi:
        return None

    titles = item.get("title") or []
    if not titles:
        return None
    title = parse_crossref_title(str(titles[0]))

    authors = []
    for author in item.get("author") or []:
        given = author.get("given")
        family = author.get("family")
        if family:
            fixed_given, fixed_family = normalize_crossref_author_name_split(
                str(given) if given else None,
                str(family),
            )
            authors.append(
                {
                    "first": fixed_given,
                    "last": fixed_family,
                }
            )

    volume = item.get("volume")
    if not volume:
        return None

    issue = item.get("issue")
    month = parse_month_from_crossref(item)

    if venue == CL and not issue:
        # Keep behavior strict for CL where issue IDs map to volume IDs in XML.
        return None

    if venue == TACL:
        issue_id = VENUE_CONFIG[TACL]["default_issue_id"]
        issue_display = issue_id
    else:
        issue_id = str(issue)
        issue_display = issue_id

    if venue == TACL:
        booktitle = VENUE_CONFIG[TACL]["booktitle_template"].format(volume=volume)
    else:
        if not month:
            month = "January"
        year = parse_year_from_crossref(item)
        if year is None:
            return None
        booktitle = VENUE_CONFIG[CL]["booktitle_template"].format(
            volume=volume,
            issue=issue_display,
            month=month,
            year=year,
        )

    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "abstract": parse_crossref_abstract(item.get("abstract")),
        "pages": parse_pages(item.get("page")),
        "issue_id": issue_id,
        "journal_volume": str(volume),
        "journal_issue": issue_display if venue == CL else None,
        "month": month if venue == CL else None,
        "booktitle": booktitle,
    }


def maybe_download_pdf(
    doi: str, destination: Path, dry_run: bool
) -> tuple[bool, Optional[str]]:
    pdf_url = PDF_URL_TEMPLATE.format(doi=doi)
    if dry_run:
        return True, pdf_url

    for attempt in range(1, PDF_DOWNLOAD_RETRIES + 1):
        try:
            retrieve_url(pdf_url, str(destination))
            if destination.is_file() and destination.stat().st_size > 0:
                try:
                    removed = maybe_remove_mitpress_watermark(destination)
                    if removed > 0:
                        logging.info(
                            "Removed %s watermark content stream(s) from %s",
                            removed,
                            destination.name,
                        )
                except Exception as exc:
                    logging.warning(
                        "Watermark cleanup failed for DOI %s (%s), keeping original PDF",
                        doi,
                        exc,
                    )
                return True, pdf_url
            raise RuntimeError("downloaded file missing or empty")
        except Exception as exc:
            # Avoid keeping a partial file between retries.
            try:
                if destination.exists():
                    destination.unlink()
            except OSError:
                pass

            if attempt == PDF_DOWNLOAD_RETRIES:
                logging.warning("Failed to fetch PDF for DOI %s: %s", doi, exc)
                return False, pdf_url

            wait_s = min(PDF_DOWNLOAD_RETRY_BASE_DELAY_SEC * (2 ** (attempt - 1)), 30)
            logging.warning(
                "PDF fetch failed for DOI %s (attempt %s/%s): %s. Retrying in %ss",
                doi,
                attempt,
                PDF_DOWNLOAD_RETRIES,
                exc,
                wait_s,
            )
            time.sleep(wait_s)

    return False, pdf_url


def remove_margin_watermark_streams(
    src: Path,
    dst: Path,
    markers: tuple[str, ...] = WATERMARK_MARKERS,
    encoding_fallback: str = "latin-1",
) -> int:
    """
    Remove per-page content streams containing MIT's margin watermark text.

    Returns the number of removed content streams.
    """
    reader = PdfReader(str(src))
    writer = PdfWriter()
    removed = 0

    marker_bytes = [m.encode("utf-8", errors="ignore") for m in markers]

    for page in reader.pages:
        contents = page.get("/Contents")
        if contents is None:
            writer.add_page(page)
            continue

        if isinstance(contents, (list, ArrayObject)):
            streams = list(contents)
        else:
            streams = [contents]

        kept_streams = []
        page_removed = 0

        for stream in streams:
            obj = stream.get_object() if hasattr(stream, "get_object") else stream
            data = obj.get_data()
            has_marker = any(mb in data for mb in marker_bytes)
            if not has_marker:
                try:
                    decoded = data.decode("utf-8")
                except UnicodeDecodeError:
                    decoded = data.decode(encoding_fallback, errors="ignore")
                has_marker = any(marker in decoded for marker in markers)

            if has_marker:
                page_removed += 1
            else:
                kept_streams.append(stream)

        removed += page_removed

        if page_removed == 0:
            writer.add_page(page)
            continue

        if len(kept_streams) == 0:
            empty_stream = DecodedStreamObject()
            empty_stream.set_data(b"")
            page[NameObject("/Contents")] = empty_stream
        elif len(kept_streams) == 1:
            page[NameObject("/Contents")] = kept_streams[0]
        else:
            page[NameObject("/Contents")] = ArrayObject(kept_streams)

        writer.add_page(page)

    if removed > 0:
        with dst.open("wb") as out_f:
            writer.write(out_f)

    return removed


def maybe_remove_mitpress_watermark(path: Path) -> int:
    if not path.is_file() or path.stat().st_size == 0:
        return 0

    tmp = Path(
        tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f"{path.name}.", suffix=".tmp", delete=False
        ).name
    )
    try:
        removed = remove_margin_watermark_streams(path, tmp, markers=WATERMARK_MARKERS)
        if removed > 0:
            tmp.replace(path)
        else:
            tmp.unlink(missing_ok=True)
        return removed
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def existing_dois(collection) -> set[str]:
    return {paper.doi.lower() for paper in collection.papers() if paper.doi}


def normalize_author_specs(authors: list[dict[str, Any]]) -> list[NameSpec]:
    return [
        NameSpec(Name.from_dict(author))
        for author in authors
        if author.get("last")
    ]


def authors_equal(existing_authors: list[NameSpec], incoming_authors: list[NameSpec]) -> bool:
    if len(existing_authors) != len(incoming_authors):
        return False
    for old, new in zip(existing_authors, incoming_authors):
        if old.first != new.first or old.last != new.last:
            return False
    return True


def ensure_volume(
    collection,
    venue: str,
    year: int,
    issue_id: str,
    paper: dict[str, Any],
):
    if (volume := collection.get(issue_id)) is not None:
        return volume

    volume = collection.create_volume(
        issue_id,
        title=MarkupText.from_string(str(paper["booktitle"])),
        type="journal",
        year=str(year),
        month=paper.get("month"),
        publisher="MIT Press",
        address="Cambridge, MA",
        venue_ids=[venue],
        journal_volume=paper.get("journal_volume"),
        journal_issue=paper.get("journal_issue"),
    )
    return volume


def ingest_papers(args, papers: list[dict[str, Any]]) -> dict[str, Any]:
    anthology = Anthology(datadir=os.path.join(args.anthology_dir, "data"))

    collection_id = f"{args.year}.{args.venue}"
    if (collection := anthology.collections.get(collection_id)) is None:
        if args.dry_run:
            logging.info("Collection %s does not exist yet (dry-run mode)", collection_id)
        collection = anthology.collections.create(collection_id)

    report: dict[str, Any] = {
        "collection": collection_id,
        "venue": args.venue,
        "year": args.year,
        "discovered": len(papers),
        "new": 0,
        "existing": 0,
        "invalid": 0,
        "ingested": 0,
        "no_pdf": 0,
        "errors": [],
        "new_dois": [],
        "existing_dois": [],
        "no_pdf_dois": [],
        "existing_pdf_downloaded": 0,
        "existing_pdf_downloaded_dois": [],
        "existing_authors_updated": 0,
        "existing_authors_updated_dois": [],
    }

    doi_set = existing_dois(collection)
    existing_papers_by_doi = {
        paper.doi.lower(): paper for paper in collection.papers() if paper.doi
    }

    pdf_destination = Path(args.pdfs_dir) / "pdf" / args.venue
    if not args.dry_run:
        pdf_destination.mkdir(parents=True, exist_ok=True)

    valid_papers: list[dict[str, Any]] = []
    for paper in papers:
        doi = normalize_doi(str(paper.get("doi", "")))
        if not doi:
            report["invalid"] += 1
            report["errors"].append("paper without DOI")
            continue

        paper["doi"] = doi
        if doi in doi_set:
            report["existing"] += 1
            report["existing_dois"].append(doi)
            if not args.dry_run and (existing_paper := existing_papers_by_doi.get(doi)):
                incoming_authors = normalize_author_specs(paper.get("authors", []))
                if not authors_equal(existing_paper.authors, incoming_authors):
                    existing_paper.authors = incoming_authors
                    report["existing_authors_updated"] += 1
                    report["existing_authors_updated_dois"].append(doi)
                    logging.info(
                        "Updated author names for existing DOI %s (%s)",
                        doi,
                        existing_paper.full_id,
                    )
                destination = pdf_destination / f"{existing_paper.full_id}.pdf"
                if not destination.is_file() or destination.stat().st_size == 0:
                    logging.info(
                        "Existing DOI %s is missing local PDF; downloading %s",
                        doi,
                        destination.name,
                    )
                    ok, pdf_url = maybe_download_pdf(doi, destination, args.dry_run)
                    if not ok:
                        report["no_pdf"] += 1
                        report["no_pdf_dois"].append(doi)
                        if pdf_url:
                            report["errors"].append(
                                f"{doi}: PDF fetch failed ({pdf_url})"
                            )
                        raise RuntimeError(
                            f"PDF download failed for existing DOI {doi} ({pdf_url}); aborting ingestion."
                        )
                    report["existing_pdf_downloaded"] += 1
                    report["existing_pdf_downloaded_dois"].append(doi)
            continue

        required = ["title", "issue_id", "journal_volume", "booktitle"]
        missing = [field for field in required if not paper.get(field)]
        if missing:
            report["invalid"] += 1
            report["errors"].append(f"{doi}: missing {','.join(missing)}")
            continue

        valid_papers.append(paper)

    valid_papers.sort(
        key=lambda p: (
            str(p.get("issue_id")),
            start_page_for_sorting(p.get("pages")),
            p["doi"],
        )
    )

    for paper_data in valid_papers:
        volume = ensure_volume(
            collection,
            args.venue,
            args.year,
            str(paper_data["issue_id"]),
            paper_data,
        )

        paper_id = volume.generate_paper_id()
        anth_id = f"{volume.full_id}.{paper_id}"
        destination = pdf_destination / f"{anth_id}.pdf"
        ok, pdf_url = maybe_download_pdf(paper_data["doi"], destination, args.dry_run)
        if not ok:
            report["no_pdf"] += 1
            report["no_pdf_dois"].append(paper_data["doi"])
            if pdf_url:
                report["errors"].append(
                    f"{paper_data['doi']}: PDF fetch failed ({pdf_url})"
                )
            raise RuntimeError(
                f"PDF download failed for DOI {paper_data['doi']} ({pdf_url}); aborting ingestion."
            )

        create_kwargs: dict[str, Any] = {
            "id": paper_id,
            "title": MarkupText.from_latex_maybe(str(paper_data["title"])),
            "doi": paper_data["doi"],
            "authors": normalize_author_specs(paper_data.get("authors", [])),
        }
        if paper_data.get("abstract"):
            create_kwargs["abstract"] = MarkupText.from_latex_maybe(
                str(paper_data["abstract"])
            )
        if paper_data.get("pages"):
            create_kwargs["pages"] = str(paper_data["pages"])

        paper_obj = volume.create_paper(**create_kwargs)

        # Keep legacy title post-processing behavior.
        xml_title = paper_obj.title.to_xml("title")
        protect(xml_title)
        paper_obj.title = MarkupText.from_xml(xml_title)

        if not args.dry_run:
            paper_obj.pdf = PDFReference.from_file(destination)

        report["new"] += 1
        report["ingested"] += 1
        report["new_dois"].append(paper_data["doi"])

    if args.dry_run:
        logging.info("Dry-run mode: no XML changes written")
    else:
        collection.save()

    return report


def write_report(report: dict[str, Any]) -> None:
    summary = (
        "discovered={discovered} new={new} existing={existing} invalid={invalid} "
        "no_pdf={no_pdf}"
    ).format(**report)
    logging.info("Summary: %s", summary)


def discover_papers(args) -> list[dict[str, Any]]:
    items = discover_crossref_items(args.venue, args.year, args.volume)
    papers = []
    for item in items:
        paper = convert_crossref_item_to_paper(item, args.venue)
        if paper is None:
            continue
        papers.append(paper)

    papers.sort(key=lambda p: (str(p.get("issue_id")), p["doi"]))
    return papers


def main(args) -> None:
    papers = discover_papers(args)
    report = ingest_papers(args, papers)
    write_report(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    anthology_path = os.path.join(os.path.dirname(sys.argv[0]), "..")
    parser.add_argument(
        "--anthology-dir",
        "-r",
        default=anthology_path,
        help="Root path of ACL Anthology Github repo. Default: %(default)s.",
    )
    parser.add_argument(
        "--pdfs-dir",
        "-p",
        default=os.path.join(os.environ["HOME"], "anthology-files"),
        help="Root path for placement of PDF files",
    )
    parser.add_argument("--venue", choices=[TACL, CL], required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--volume", type=str, default=None)

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run full logic but do not write XML or PDFs.",
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose", action="store_const", const=logging.DEBUG, default=logging.INFO
    )
    verbosity.add_argument(
        "-q", "--quiet", dest="verbose", action="store_const", const=logging.WARNING
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s v{__version__}")

    args = parser.parse_args()

    setup_rich_logging(level=args.verbose)
    main(args)
