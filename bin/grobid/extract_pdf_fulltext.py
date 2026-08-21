#!/usr/bin/env python3

"""Extract full text from Anthology PDFs with GROBID into a parallel tree.

This is the server-side companion to `extract_pdf_metadata.py`. Where that
script extracts paper headers into a developer cache, this one walks the
canonical `anthology-files/pdf` tree and writes one JSON document per PDF into a
`grobid` tree that mirrors it exactly:

    pdf/acl/2025.acl-long.1.pdf  ->  grobid/acl/2025.acl-long.1.json
    pdf/W/W00/W00-1323.pdf       ->  grobid/W/W00/W00-1323.json

Each JSON document combines the Anthology's own metadata (title, authors,
venues, event, year) with GROBID's `processFulltextDocument` output (abstract,
sections, body paragraphs, references). A search indexer can therefore attribute
every hit to a field -- author, venue name, title, abstract, body, or reference
-- from a single file.

Runs are incremental: a paper is sent to GROBID only when it has no extraction,
when the recorded PDF checksum or size no longer matches, or when the schema or
GROBID request options have changed. Anthology metadata changes are refreshed
in place without contacting GROBID. This makes repeated cron invocations cheap:

    # everything that is new or stale (the routine server job)
    bin/grobid/extract_pdf_fulltext.py --all -j 8

    # a bounded selection, for spot checks
    bin/grobid/extract_pdf_fulltext.py 2025.acl-long.1 acl-2025 -j 4

Selectors are positional and may be mixed. A four-digit selector is a year;
every other selector is resolved as a paper, volume, collection, or event ID.
`--all` selects the entire Anthology and may not be combined with selectors.
PDFs are never downloaded: papers whose PDF is not in the local tree are
reported and skipped.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

import requests
from lxml import etree

from acl_anthology import Anthology
from acl_anthology.collections.paper import Paper


DEFAULT_ANTHOLOGY_FILES = Path(
    os.environ.get("ANTHOLOGYFILES") or Path.home() / "anthology-files"
)
DEFAULT_PDF_ROOT = DEFAULT_ANTHOLOGY_FILES / "pdf"
DEFAULT_OUTPUT_ROOT = DEFAULT_ANTHOLOGY_FILES / "grobid"
DEFAULT_GROBID_URL = os.environ.get("GROBID_URL") or "http://localhost:8070"
OUTPUT_SUFFIX = ".json"

SCHEMA_VERSION = 1
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NAMESPACE}
GROBID_REQUEST_OPTIONS = {
    # Keep the extraction PDF-intrinsic; do not inject Crossref metadata.
    "consolidateHeader": "0",
    "consolidateCitations": "0",
    "consolidateFunders": "0",
    "includeRawAffiliations": "1",
    "segmentSentences": "0",
}
CACHEABLE_STATUSES = {"success", "no-content", "error"}


@dataclass(frozen=True)
class PaperJob:
    paper_id: str
    pdf_path: Path
    json_path: Path
    metadata: dict[str, Any]
    source: dict[str, Any]
    grobid_url: str
    grobid_version: str | None
    timeout: float
    retries: int


@dataclass(frozen=True)
class WorkResult:
    paper_id: str
    status: str
    detail: str | None = None


def normalize_text(element: etree._Element | None) -> str | None:
    """Return whitespace-normalized descendant text, or None when empty."""
    if element is None:
        return None
    value = " ".join("".join(element.itertext()).split())
    return value or None


def text_of(scope: etree._Element, xpath: str) -> str | None:
    return normalize_text(next(iter(scope.xpath(xpath, namespaces=NS)), None))


def paragraphs_of(scope: etree._Element, xpath: str = "./tei:p") -> list[str]:
    return [
        text
        for paragraph in scope.xpath(xpath, namespaces=NS)
        if (text := normalize_text(paragraph))
    ]


def parse_tei_person(element: etree._Element) -> dict[str, Any]:
    """Parse one TEI author or editor into a flat, search-friendly record."""
    affiliations = []
    for affiliation in element.xpath(".//tei:affiliation", namespaces=NS):
        raw = text_of(affiliation, ".//tei:note[@type='raw_affiliation']")
        text = raw or normalize_text(affiliation)
        if text and text not in affiliations:
            affiliations.append(text)
    result: dict[str, Any] = {
        "name": text_of(element, "./tei:persName") or normalize_text(element),
        "affiliations": affiliations,
        "email": text_of(element, ".//tei:email"),
        "orcid": text_of(element, ".//tei:idno[@type='ORCID']"),
    }
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def parse_tei_reference(element: etree._Element) -> dict[str, Any]:
    """Parse one TEI `biblStruct` from the reference list."""
    result: dict[str, Any] = {
        "title": text_of(element, ".//tei:title[@level='a']")
        or text_of(element, ".//tei:title[@level='m']"),
        "authors": [
            name
            for author in element.xpath(".//tei:author", namespaces=NS)
            if (name := text_of(author, "./tei:persName"))
        ],
        "venue": text_of(element, "./tei:monogr/tei:title[@level='j']")
        or text_of(element, "./tei:monogr/tei:title[@level='m']"),
        "year": text_of(element, ".//tei:date[@type='published']")
        or text_of(element, ".//tei:date"),
        "doi": text_of(element, ".//tei:idno[@type='DOI']"),
    }
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def parse_tei_sections(
    divisions: list[etree._Element], type_: str | None = None
) -> list[dict[str, Any]]:
    """Parse TEI `div` elements into ordered `{n, head, paragraphs}` records."""
    sections = []
    for division in divisions:
        head = next(iter(division.xpath("./tei:head", namespaces=NS)), None)
        paragraphs = paragraphs_of(division)
        if head is None and not paragraphs:
            continue
        section: dict[str, Any] = {
            "n": head.get("n") if head is not None else None,
            "head": normalize_text(head),
            "type": type_ or division.get("type"),
            "paragraphs": paragraphs,
        }
        sections.append(
            {key: value for key, value in section.items() if value not in (None, [], {})}
        )
    return sections


def parse_tei_back_sections(root: etree._Element) -> list[dict[str, Any]]:
    """Parse acknowledgements and annexes, which GROBID wraps in an outer div."""
    sections = []
    for outer in root.xpath(
        ".//tei:text/tei:back/tei:div[@type='acknowledgement' or @type='annex']",
        namespaces=NS,
    ):
        inner = outer.xpath("./tei:div", namespaces=NS) or [outer]
        sections.extend(parse_tei_sections(inner, outer.get("type")))
    return sections


def parse_fulltext_tei(tei: bytes | str) -> dict[str, Any]:
    """Project a GROBID full-text TEI response into search-oriented JSON.

    The projection keeps document order and section structure so an indexer can
    report *where* a match occurred, and drops TEI machinery (coordinates,
    figure markup, inline reference pointers) that search does not use.
    """
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(tei.encode() if isinstance(tei, str) else tei, parser)

    bibl = next(
        iter(
            root.xpath(
                ".//tei:teiHeader/tei:fileDesc/tei:sourceDesc//tei:biblStruct[1]",
                namespaces=NS,
            )
        ),
        None,
    )
    abstract = next(
        iter(
            root.xpath(".//tei:teiHeader/tei:profileDesc/tei:abstract[1]", namespaces=NS)
        ),
        None,
    )
    application = next(
        iter(
            root.xpath(
                ".//tei:teiHeader/tei:encodingDesc//tei:application[1]", namespaces=NS
            )
        ),
        None,
    )

    sections = parse_tei_sections(
        root.xpath(".//tei:text/tei:body/tei:div", namespaces=NS)
    )
    back_sections = parse_tei_back_sections(root)
    references = [
        parsed
        for entry in root.xpath(
            ".//tei:text/tei:back//tei:listBibl/tei:biblStruct", namespaces=NS
        )
        if (parsed := parse_tei_reference(entry))
    ]

    body_characters = sum(
        len(paragraph)
        for section in sections + back_sections
        for paragraph in section.get("paragraphs", [])
    )
    result: dict[str, Any] = {
        "title": text_of(
            root, ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='main']"
        ),
        "authors": [
            parsed
            for author in (
                bibl.xpath("./tei:analytic/tei:author", namespaces=NS)
                if bibl is not None
                else []
            )
            if (parsed := parse_tei_person(author))
        ],
        "abstract": " ".join(paragraphs_of(abstract, ".//tei:p"))
        if abstract is not None
        else None,
        "keywords": [
            text
            for term in root.xpath(
                ".//tei:teiHeader/tei:profileDesc/tei:textClass//tei:term", namespaces=NS
            )
            if (text := normalize_text(term))
        ],
        "sections": sections,
        "back_sections": back_sections,
        "references": references,
        "stats": {
            "sections": len(sections) + len(back_sections),
            "paragraphs": sum(
                len(section.get("paragraphs", [])) for section in sections + back_sections
            ),
            "references": len(references),
            "body_characters": body_characters,
        },
        "grobid_version": application.get("version") if application is not None else None,
    }
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def anthology_metadata(paper: Paper) -> dict[str, Any]:
    """Collect the Anthology-side fields a search index needs to attribute hits."""
    volume = paper.parent
    result: dict[str, Any] = {
        "title": str(paper.title),
        "abstract": str(paper.abstract) if paper.abstract is not None else None,
        "authors": [author.name.as_full() for author in paper.authors],
        "editors": [editor.name.as_full() for editor in volume.editors],
        "venues": [
            {"id": venue.id, "acronym": venue.acronym, "name": venue.name}
            for venue in volume.venues()
        ],
        "events": [event.id for event in volume.get_events()],
        "sigs": [sig.acronym for sig in volume.get_sigs()],
        "year": paper.year,
        "month": paper.month,
        "volume_id": volume.full_id,
        "volume_title": str(volume.title),
        "bibkey": paper.bibkey,
        "doi": paper.doi,
        "language": paper.language,
        "url": paper.web_url,
        "awards": list(paper.awards),
    }
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def canonical_pdf_path(pdf_root: Path, paper: Paper) -> Path:
    """Resolve a paper's canonical path in the anthology-files PDF tree."""
    if paper.pdf is None:
        raise ValueError(f"Paper {paper.full_id} has no PDF reference")
    filename = Path(paper.pdf.name).name
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    collection_id = paper.collection_id
    if collection_id[0].isdigit():
        venue = collection_id.split(".", 1)[-1]
        return pdf_root / venue / filename
    return pdf_root / collection_id[0] / collection_id / filename


def output_path(pdf_path: Path, pdf_root: Path, output_root: Path) -> Path:
    """Mirror a PDF's position in the parallel extraction tree."""
    relative = pdf_path.relative_to(pdf_root)
    return output_root / relative.with_suffix(OUTPUT_SUFFIX)


def source_metadata(paper: Paper, pdf_path: Path) -> dict[str, Any]:
    """Describe the PDF cheaply enough to re-check every paper on every run."""
    if paper.pdf is None:
        raise ValueError(f"Paper {paper.full_id} has no PDF reference")
    return {
        "reference": paper.pdf.name,
        "checksum": paper.pdf.checksum,
        "size": pdf_path.stat().st_size,
    }


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically replace a JSON file with fully flushed content."""
    payload = (
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def result_is_current(result: dict[str, Any], source: dict[str, Any]) -> bool:
    """Return whether an existing extraction still describes this PDF."""
    if result.get("schema_version") != SCHEMA_VERSION:
        return False
    if result.get("status") not in CACHEABLE_STATUSES:
        return False
    if result.get("extractor", {}).get("options") != GROBID_REQUEST_OPTIONS:
        return False
    existing = result.get("source", {})
    return all(
        existing.get(key) == source.get(key) for key in ("reference", "checksum", "size")
    )


def grobid_endpoint(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/processFulltextDocument"


def check_grobid(base_url: str, timeout: float) -> str:
    """Check GROBID readiness and return its reported version."""
    base_url = base_url.rstrip("/")
    alive = requests.get(f"{base_url}/api/isalive", timeout=(5, timeout))
    alive.raise_for_status()
    if alive.text.strip().lower() != "true":
        raise RuntimeError(f"GROBID at {base_url} is not ready: {alive.text.strip()}")
    version = requests.get(f"{base_url}/api/version", timeout=(5, timeout))
    version.raise_for_status()
    return version.text.strip() or "unknown"


def request_grobid(
    pdf_path: Path,
    base_url: str,
    timeout: float,
    retries: int,
    *,
    session: requests.Session | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> requests.Response:
    """Call GROBID, retrying transient connection failures and HTTP 503."""
    client = session or requests.Session()
    last_exception: requests.RequestException | None = None
    for attempt in range(retries + 1):
        try:
            with pdf_path.open("rb") as stream:
                response = client.post(
                    grobid_endpoint(base_url),
                    files={"input": (pdf_path.name, stream, "application/pdf")},
                    data=GROBID_REQUEST_OPTIONS,
                    headers={"Accept": "application/xml"},
                    timeout=(10, timeout),
                )
        except requests.RequestException as exception:
            last_exception = exception
            if attempt == retries:
                raise
            sleep(2 * (attempt + 1))
            continue
        if response.status_code != 503 or attempt == retries:
            return response
        sleep(2 * (attempt + 1))
    if last_exception is not None:  # pragma: no cover - loop always raises first
        raise last_exception
    raise RuntimeError("GROBID request retry loop ended unexpectedly")  # pragma: no cover


def base_result(job: PaperJob, status: str, version: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "paper_id": job.paper_id,
        "extracted": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": job.source,
        "metadata": job.metadata,
        "extractor": {
            "name": "GROBID processFulltextDocument",
            "service_url": job.grobid_url,
            "version": version or job.grobid_version or "unknown",
            "options": GROBID_REQUEST_OPTIONS,
        },
    }


def process_job(job: PaperJob) -> WorkResult:
    """Extract one paper and atomically persist its JSON extraction."""
    try:
        # A request supersedes any old result: if this attempt is interrupted or
        # fails transiently, the next run must see the paper as outstanding.
        job.json_path.unlink(missing_ok=True)
        response = request_grobid(job.pdf_path, job.grobid_url, job.timeout, job.retries)
        if response.status_code == 204:
            atomic_write_json(job.json_path, base_result(job, "no-content"))
            return WorkResult(job.paper_id, "no-content")
        if response.status_code == 503:
            return WorkResult(
                job.paper_id,
                "transient-error",
                "GROBID remained busy (HTTP 503) after retries",
            )
        if response.status_code != 200:
            result = base_result(job, "error")
            result["error"] = {
                "kind": "grobid-http",
                "status_code": response.status_code,
                "message": response.text[:2000],
            }
            atomic_write_json(job.json_path, result)
            return WorkResult(job.paper_id, "error", f"HTTP {response.status_code}")

        try:
            fulltext = parse_fulltext_tei(response.content)
        except etree.XMLSyntaxError as exception:
            result = base_result(job, "error")
            result["error"] = {"kind": "invalid-tei", "message": str(exception)}
            atomic_write_json(job.json_path, result)
            return WorkResult(job.paper_id, "error", "invalid TEI")

        result = base_result(job, "success", fulltext.get("grobid_version"))
        result["fulltext"] = fulltext
        atomic_write_json(job.json_path, result)
        return WorkResult(job.paper_id, "success")
    except (OSError, requests.RequestException, RuntimeError, ValueError) as exception:
        # No result is written for transient failures, so a rerun retries.
        return WorkResult(job.paper_id, "transient-error", str(exception))


def event_papers(anthology: Anthology, event_id: str) -> Iterator[Paper]:
    """Iterate papers in an event's own collection and colocated volumes."""
    event = anthology.get_event(event_id)
    if event is None:
        raise ValueError(f"Event {event_id!r} was not found in the Anthology")
    seen_volumes = set()
    for volumes in (event.collection.volumes(), event.volumes()):
        for volume in volumes:
            if volume.full_id_tuple in seen_volumes:
                continue
            seen_volumes.add(volume.full_id_tuple)
            yield from volume.papers()


def select_papers(anthology: Anthology, selectors: list[str]) -> Iterator[Paper]:
    """Resolve year and publication/event selectors without duplicates."""
    if not selectors:
        return anthology.papers()

    selected: dict[str, Paper] = {}
    requested_years = {
        int(selector)
        for selector in selectors
        if len(selector) == 4 and selector.isdecimal()
    }
    matched_years: set[int] = set()
    if requested_years:
        for paper in anthology.papers():
            if int(paper.year) in requested_years:
                selected.setdefault(paper.full_id, paper)
                matched_years.add(int(paper.year))
        if missing_years := requested_years - matched_years:
            values = ", ".join(str(year) for year in sorted(missing_years))
            raise ValueError(f"No Anthology papers were found for year(s): {values}")

    # Resolve every non-year selector before yielding work, so a typo cannot
    # leave a partially processed selection.
    resolved: list[Iterator[Paper]] = []
    for anthology_id in selectors:
        if len(anthology_id) == 4 and anthology_id.isdecimal():
            continue
        try:
            publication = anthology.get(anthology_id)
        except ValueError:
            publication = None
        if publication is not None:
            resolved.append(anthology.papers(anthology_id))
        elif anthology.get_event(anthology_id) is not None:
            resolved.append(event_papers(anthology, anthology_id))
        else:
            raise ValueError(f"Anthology ID or event {anthology_id!r} was not found")
    for papers in resolved:
        for paper in papers:
            selected.setdefault(paper.full_id, paper)
    return iter(selected.values())


def make_job(paper: Paper, args: argparse.Namespace) -> tuple[str, PaperJob | None]:
    """Classify a paper as up to date, unusable, or needing GROBID."""
    if paper.is_deleted:
        return "deleted", None
    if paper.pdf is None:
        return "no-pdf-reference", None
    if not paper.pdf.is_local:
        return "external-pdf", None
    if paper.is_frontmatter and not args.include_frontmatter:
        return "frontmatter", None

    pdf_path = canonical_pdf_path(args.pdf_root, paper)
    try:
        source = source_metadata(paper, pdf_path)
    except OSError:
        return "missing-pdf", None

    json_path = output_path(pdf_path, args.pdf_root, args.output_root)
    metadata = anthology_metadata(paper)
    existing = load_json(json_path)
    if (
        not args.force
        and existing is not None
        and result_is_current(existing, source)
        and not (args.retry_errors and existing.get("status") == "error")
    ):
        if existing.get("metadata") != metadata and not args.dry_run:
            existing["metadata"] = metadata
            atomic_write_json(json_path, existing)
            return "metadata-updated", None
        return "current", None

    return "request", PaperJob(
        paper_id=paper.full_id,
        pdf_path=pdf_path,
        json_path=json_path,
        metadata=metadata,
        source=source,
        grobid_url=args.grobid_url,
        grobid_version=None,
        timeout=args.timeout,
        retries=args.retries,
    )


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def nonnegative_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "selectors",
        nargs="*",
        metavar="SELECTOR",
        help=(
            "Four-digit year or Anthology paper, volume, collection, or event ID; "
            "may be combined. Omit and pass --all to scan the whole Anthology."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan every paper in the Anthology; required when no selector is given.",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=positive_integer,
        default=1,
        help="Number of concurrent GROBID requests (default: %(default)s).",
    )
    parser.add_argument(
        "--grobid-url",
        default=DEFAULT_GROBID_URL,
        help="Base URL of the GROBID service (default: %(default)s).",
    )
    parser.add_argument(
        "--pdf-root",
        type=Path,
        default=DEFAULT_PDF_ROOT,
        help="Root of the anthology-files PDF tree (default: %(default)s).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=(
            "Root of the extraction tree, which mirrors the PDF tree "
            "(default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--limit",
        type=positive_integer,
        default=None,
        help="Send at most this many papers to GROBID.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300,
        help="Per-request read timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--retries",
        type=nonnegative_integer,
        default=3,
        help="Retries for connection failures and HTTP 503 (default: %(default)s).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract papers even when their extraction is current.",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Retry papers whose extraction records a permanent GROBID/TEI error.",
    )
    parser.add_argument(
        "--include-frontmatter",
        action="store_true",
        help="Also process volume frontmatter records.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report work without contacting GROBID or writing output.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_intermixed_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.all and args.selectors:
        parser.error("--all cannot be combined with selectors")
    if not args.all and not args.selectors:
        parser.error("give at least one selector, or --all to scan the whole Anthology")
    if not args.pdf_root.is_dir():
        parser.error(f"PDF root {args.pdf_root} does not exist")

    anthology = Anthology.from_within_repo()
    try:
        papers = select_papers(anthology, args.selectors)
    except ValueError as exception:
        parser.error(str(exception))
    counts: Counter[str] = Counter()
    scheduled = 0
    completed = 0
    started = time.monotonic()
    grobid_version: str | None = None
    pending: set[concurrent.futures.Future[WorkResult]] = set()

    def report(future: concurrent.futures.Future[WorkResult]) -> None:
        nonlocal completed
        completed += 1
        try:
            result = future.result()
        except Exception as exception:  # pragma: no cover - worker catches its errors
            counts["internal-error"] += 1
            print(f"Internal worker error: {exception}", file=sys.stderr)
            return
        counts[result.status] += 1
        if result.status != "success":
            detail = f": {result.detail}" if result.detail else ""
            print(f"{result.paper_id}: {result.status}{detail}", file=sys.stderr)
        if completed % 100 == 0:
            elapsed = time.monotonic() - started
            print(
                f"Extracted {completed}/{scheduled} scheduled papers "
                f"({completed / elapsed:.1f}/s).",
                file=sys.stderr,
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        for paper in papers:
            disposition, job = make_job(paper, args)
            if job is None:
                counts[disposition] += 1
                continue
            if args.limit is not None and scheduled >= args.limit:
                break
            scheduled += 1
            if args.dry_run:
                print(f"{paper.full_id}: {disposition}")
                continue
            if grobid_version is None:
                try:
                    grobid_version = check_grobid(args.grobid_url, args.timeout)
                except (requests.RequestException, RuntimeError) as exception:
                    print(f"Could not connect to GROBID: {exception}", file=sys.stderr)
                    return 2
                print(
                    f"Using GROBID {grobid_version} at {args.grobid_url}.",
                    file=sys.stderr,
                )
            pending.add(
                executor.submit(process_job, replace(job, grobid_version=grobid_version))
            )
            if len(pending) >= max(2, args.jobs * 2):
                done, pending = concurrent.futures.wait(
                    pending, return_when=concurrent.futures.FIRST_COMPLETED
                )
                for future in done:
                    report(future)

        for future in concurrent.futures.as_completed(pending):
            report(future)

    summary = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    print(f"Scanned papers; scheduled={scheduled}. {summary}", file=sys.stderr)
    return 1 if counts["transient-error"] or counts["internal-error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
