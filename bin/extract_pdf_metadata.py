#!/usr/bin/env python3

"""Extract paper-header metadata from Anthology PDFs with GROBID.

The script iterates over papers through the public ``acl_anthology`` API and
sends PDFs to GROBID's ``processHeaderDocument`` endpoint. Each paper gets a
lossless TEI response and a parsed JSON record under the output directory.
Writes are atomic, and the JSON file is written last as the completion marker,
so interrupted runs can be resumed safely:

    bin/extract_pdf_metadata.py 2025 -j 4
    bin/extract_pdf_metadata.py 2025.acl-main acl-2025 -j 4

At least one selector is required. Four-digit selectors are treated as years;
all others are Anthology IDs identifying papers, volumes, collections, or
events. PDFs are read from
``~/anthology-files/pdf`` when available; missing PDFs are downloaded to
temporary storage and removed after extraction. Durable results are stored in
the platform-specific ACL Anthology cache. Existing current results are
skipped; use ``--force`` to extract them again or ``--retry-errors`` to retry
cached permanent errors.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Iterator

import requests
from lxml import etree

from acl_anthology import Anthology
from acl_anthology.collections.paper import Paper
from acl_anthology.config import dirs
from acl_anthology.files import PDFReference


DEFAULT_CACHE_DIR = dirs.user_cache_path / "grobid"
DEFAULT_PDF_ROOT = Path.home() / "anthology-files" / "pdf"
DEFAULT_GROBID_URL = "http://localhost:8070"

SCHEMA_VERSION = 1
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
NS = {"tei": TEI_NAMESPACE}
GROBID_REQUEST_OPTIONS = {
    # Keep extracted metadata PDF-intrinsic; do not inject Crossref metadata.
    "consolidateHeader": "0",
    "includeRawAffiliations": "1",
    "includeRawCopyrights": "1",
}
CACHEABLE_STATUSES = {"success", "no-content", "error"}


@dataclass(frozen=True)
class PaperJob:
    paper_id: str
    pdf: PDFReference
    pdf_path: Path
    json_path: Path
    tei_path: Path
    anthology_metadata: dict[str, Any]
    source_metadata: dict[str, Any]
    action: str
    temporary_pdf: bool
    save_tei: bool
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


def element_attributes(element: etree._Element) -> dict[str, str]:
    """Return XML attributes using local names instead of namespace notation."""
    return {etree.QName(name).localname: value for name, value in element.attrib.items()}


def parsed_elements(
    scope: etree._Element, xpath: str, *, include_attributes: bool = True
) -> list[dict[str, Any]]:
    """Parse text-bearing TEI elements selected by an XPath expression."""
    values = []
    for element in scope.xpath(xpath, namespaces=NS):
        text = normalize_text(element)
        if not text:
            continue
        value: dict[str, Any] = {"text": text}
        if include_attributes and element.attrib:
            value["attributes"] = element_attributes(element)
        values.append(value)
    return values


def parse_affiliation(element: etree._Element) -> dict[str, Any]:
    """Parse one GROBID TEI affiliation into a JSON-compatible dictionary."""
    organizations = []
    for organization in element.xpath(".//tei:orgName", namespaces=NS):
        name = normalize_text(organization)
        if not name:
            continue
        item: dict[str, Any] = {"name": name}
        item.update(element_attributes(organization))
        organizations.append(item)

    address: dict[str, Any] = {}
    address_element = next(iter(element.xpath("./tei:address", namespaces=NS)), None)
    if address_element is not None:
        for child in address_element:
            name = etree.QName(child).localname.replace("postCode", "post_code")
            text = normalize_text(child)
            if not text:
                continue
            value: Any = text
            if child.attrib:
                value = {"text": text, **element_attributes(child)}
            if name in address:
                if not isinstance(address[name], list):
                    address[name] = [address[name]]
                address[name].append(value)
            else:
                address[name] = value

    result: dict[str, Any] = {
        "text": normalize_text(element),
        "organizations": organizations,
    }
    if element.attrib:
        result["attributes"] = element_attributes(element)
    if address:
        result["address"] = address
    if marker := normalize_text(
        next(iter(element.xpath("./tei:marker", namespaces=NS)), None)
    ):
        result["marker"] = marker
    if raw := normalize_text(
        next(
            iter(element.xpath(".//tei:note[@type='raw_affiliation']", namespaces=NS)),
            None,
        )
    ):
        result["raw"] = raw
    identifiers = parsed_elements(element, ".//tei:idno")
    if identifiers:
        result["identifiers"] = identifiers
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def parse_grobid_tei(tei: bytes | str) -> dict[str, Any]:
    """Project GROBID header TEI into useful, stable JSON fields.

    The raw TEI remains the lossless source. This projection intentionally keeps
    author order and explicit author-to-affiliation links; it does not attempt
    to align extracted authors to Anthology ``NameSpecification`` objects.
    """
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(tei.encode() if isinstance(tei, str) else tei, parser)
    bibl_nodes = root.xpath(
        ".//tei:teiHeader/tei:fileDesc/tei:sourceDesc//tei:biblStruct[1]",
        namespaces=NS,
    )
    bibl = bibl_nodes[0] if bibl_nodes else root

    affiliation_targets: dict[str, etree._Element] = {}
    for affiliation in bibl.xpath(".//tei:affiliation", namespaces=NS):
        for key in (
            affiliation.get("key"),
            affiliation.get(f"{{{XML_NAMESPACE}}}id"),
        ):
            if key:
                affiliation_targets[key.lstrip("#")] = affiliation

    affiliations: list[dict[str, Any]] = []
    affiliation_ids_by_signature: dict[str, str] = {}
    affiliation_ids_by_key: dict[str, str] = {}

    def register_affiliation(element: etree._Element) -> str | None:
        references = (element.get("ref") or "").split()
        if references and not normalize_text(element):
            target = affiliation_targets.get(references[0].lstrip("#"))
            return register_affiliation(target) if target is not None else None

        parsed = parse_affiliation(element)
        if not parsed:
            return None
        key = element.get("key") or element.get(f"{{{XML_NAMESPACE}}}id")
        normalized_key = key.lstrip("#") if key else None
        if normalized_key and normalized_key in affiliation_ids_by_key:
            return affiliation_ids_by_key[normalized_key]
        signature = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
        if signature in affiliation_ids_by_signature:
            affiliation_id = affiliation_ids_by_signature[signature]
        else:
            candidate = normalized_key or f"affiliation-{len(affiliations) + 1}"
            affiliation_id = candidate
            while any(item["id"] == affiliation_id for item in affiliations):
                affiliation_id = f"affiliation-{len(affiliations) + 1}"
            affiliations.append({"id": affiliation_id, **parsed})
            affiliation_ids_by_signature[signature] = affiliation_id
        if normalized_key:
            affiliation_ids_by_key[normalized_key] = affiliation_id
        return affiliation_id

    authors = []
    author_nodes = bibl.xpath("./tei:analytic/tei:author", namespaces=NS)
    if not author_nodes:
        author_nodes = bibl.xpath(".//tei:author", namespaces=NS)
    for index, author in enumerate(author_nodes):
        person_name = next(iter(author.xpath("./tei:persName", namespaces=NS)), None)
        forenames = []
        if person_name is not None:
            for forename in person_name.xpath("./tei:forename", namespaces=NS):
                text = normalize_text(forename)
                if text:
                    forenames.append({"text": text, **element_attributes(forename)})
        surnames = (
            [
                text
                for surname in person_name.xpath("./tei:surname", namespaces=NS)
                if (text := normalize_text(surname))
            ]
            if person_name is not None
            else []
        )
        affiliation_ids = []
        for affiliation in author.xpath(
            "./tei:affiliation | ./tei:persName/tei:affiliation", namespaces=NS
        ):
            references = (affiliation.get("ref") or "").split()
            if references and not normalize_text(affiliation):
                for reference in references:
                    target = affiliation_targets.get(reference.lstrip("#"))
                    affiliation_id = (
                        register_affiliation(target) if target is not None else None
                    )
                    if affiliation_id and affiliation_id not in affiliation_ids:
                        affiliation_ids.append(affiliation_id)
                continue
            affiliation_id = register_affiliation(affiliation)
            if affiliation_id and affiliation_id not in affiliation_ids:
                affiliation_ids.append(affiliation_id)

        identifiers = parsed_elements(author, ".//tei:idno")
        emails = [
            text
            for email in author.xpath(".//tei:email", namespaces=NS)
            if (text := normalize_text(email))
        ]
        phones = [
            text
            for phone in author.xpath(".//tei:phone", namespaces=NS)
            if (text := normalize_text(phone))
        ]
        author_data: dict[str, Any] = {
            "index": index,
            "name": normalize_text(person_name),
            "forenames": forenames,
            "surnames": surnames,
            "identifiers": identifiers,
            "emails": emails,
            "phones": phones,
            "affiliation_ids": affiliation_ids,
        }
        if author.attrib:
            author_data["attributes"] = element_attributes(author)
        authors.append(
            {
                key: value
                for key, value in author_data.items()
                if value not in (None, [], {})
            }
        )

    # Retain affiliations extracted by GROBID even if no author link was found.
    for affiliation in bibl.xpath(".//tei:affiliation", namespaces=NS):
        if normalize_text(affiliation):
            register_affiliation(affiliation)

    titles = parsed_elements(bibl, ".//tei:title")
    title = next(
        (
            item["text"]
            for item in titles
            if item.get("attributes", {}).get("level") == "a"
            and item.get("attributes", {}).get("type") in (None, "main")
        ),
        None,
    )
    if title is None:
        title_nodes = root.xpath(
            ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='main'][1]",
            namespaces=NS,
        )
        title = normalize_text(title_nodes[0]) if title_nodes else None

    abstract_nodes = root.xpath(
        ".//tei:teiHeader/tei:profileDesc/tei:abstract[1]", namespaces=NS
    )
    application_nodes = root.xpath(
        ".//tei:teiHeader/tei:encodingDesc//tei:application[1]", namespaces=NS
    )
    application = element_attributes(application_nodes[0]) if application_nodes else {}
    languages = parsed_elements(
        root, ".//tei:teiHeader/tei:profileDesc/tei:langUsage/tei:language"
    )
    root_language = root.get(f"{{{XML_NAMESPACE}}}lang")
    if root_language and not any(
        item.get("attributes", {}).get("ident") == root_language for item in languages
    ):
        languages.insert(
            0, {"text": root_language, "attributes": {"ident": root_language}}
        )

    result: dict[str, Any] = {
        "title": title,
        "titles": titles,
        "authors": authors,
        "affiliations": affiliations,
        "abstract": normalize_text(abstract_nodes[0]) if abstract_nodes else None,
        "keywords": [
            text
            for term in root.xpath(
                ".//tei:teiHeader/tei:profileDesc/tei:textClass//tei:term",
                namespaces=NS,
            )
            if (text := normalize_text(term))
        ],
        "identifiers": parsed_elements(bibl, ".//tei:idno[not(ancestor::tei:author)]"),
        "dates": parsed_elements(bibl, ".//tei:date"),
        "languages": languages,
        "journal_titles": parsed_elements(bibl, "./tei:monogr/tei:title"),
        "publishers": parsed_elements(bibl, ".//tei:publisher"),
        "meetings": parsed_elements(bibl, ".//tei:meeting"),
        "funders": parsed_elements(bibl, ".//tei:funder"),
        "copyright": parsed_elements(
            root,
            ".//tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:availability"
            " | .//tei:note[@type='raw_copyright']",
        ),
        "document_type": bibl.get("type"),
        "grobid_application": application,
    }
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def namespec_metadata(namespec: Any, index: int) -> dict[str, Any]:
    """Serialize public NameSpecification metadata needed for later alignment."""
    result: dict[str, Any] = {
        "index": index,
        "name": namespec.name.as_full(),
        "first": namespec.first,
        "last": namespec.last,
        "id": namespec.id,
        "orcid": namespec.orcid,
        "openreview": namespec.openreview,
        "affiliation": namespec.affiliation,
        "variants": [
            {
                "name": variant.as_full(),
                "first": variant.first,
                "last": variant.last,
                "script": variant.script,
            }
            for variant in namespec.variants
        ],
    }
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def anthology_paper_metadata(paper: Paper) -> dict[str, Any]:
    """Collect useful paper metadata through the public Anthology API."""
    result: dict[str, Any] = {
        "paper_id": paper.full_id,
        "bibkey": paper.bibkey,
        "title": str(paper.title),
        "abstract": str(paper.abstract) if paper.abstract is not None else None,
        "authors": [
            namespec_metadata(author, index) for index, author in enumerate(paper.authors)
        ],
        "editors": [
            namespec_metadata(editor, index) for index, editor in enumerate(paper.editors)
        ],
        "doi": paper.doi,
        "year": paper.year,
        "month": paper.month,
        "pages": paper.pages,
        "language": paper.language,
        "publisher": paper.publisher,
        "publisher_address": paper.address,
        "journal_title": paper.journal_title,
        "journal_volume": paper.journal_volume,
        "journal_issue": paper.journal_issue,
        "venue_ids": list(paper.venue_ids),
        "volume_id": paper.parent.full_id,
        "volume_title": str(paper.parent.title),
        "paper_type": paper.type.value,
        "web_url": paper.web_url,
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


def paper_output_paths(output_dir: Path, paper: Paper) -> tuple[Path, Path]:
    """Return sharded JSON and TEI paths for a paper."""
    collection_id, volume_id, paper_id = paper.full_id_tuple
    directory = output_dir / "papers" / collection_id / str(volume_id)
    return directory / f"{paper_id}.json", directory / f"{paper_id}.tei.xml"


def download_cache_path(download_dir: Path, paper: Paper) -> Path:
    collection_id, volume_id, paper_id = paper.full_id_tuple
    return download_dir / collection_id / str(volume_id) / f"{paper_id}.pdf"


def source_metadata(paper: Paper) -> dict[str, Any]:
    if paper.pdf is None:
        raise ValueError(f"Paper {paper.full_id} has no PDF reference")
    return {
        "reference": paper.pdf.name,
        "url": paper.pdf.url,
        "checksum": paper.pdf.checksum,
    }


def atomic_write(path: Path, content: bytes) -> None:
    """Atomically replace a file with fully flushed content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    atomic_write(path, payload)


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def cached_result_is_current(
    result: dict[str, Any], source: dict[str, Any], *, save_tei: bool, tei_path: Path
) -> bool:
    """Return whether a cached result can be reused for this PDF and schema."""
    if result.get("schema_version") != SCHEMA_VERSION:
        return False
    if result.get("status") not in CACHEABLE_STATUSES:
        return False
    cached_source = result.get("source", {})
    if any(
        cached_source.get(key) != source.get(key) for key in ("reference", "checksum")
    ):
        return False
    if result.get("extractor", {}).get("options") != GROBID_REQUEST_OPTIONS:
        return False
    return not (save_tei and result.get("status") == "success" and not tei_path.is_file())


def cached_tei_is_current(
    result: dict[str, Any] | None,
    source: dict[str, Any],
    tei_path: Path,
) -> bool:
    """Return whether raw TEI is known to describe the selected PDF/options."""
    if result is None or result.get("status") != "success" or not tei_path.is_file():
        return False
    cached_source = result.get("source", {})
    if any(
        cached_source.get(key) != source.get(key) for key in ("reference", "checksum")
    ):
        return False
    return result.get("extractor", {}).get("options") == GROBID_REQUEST_OPTIONS


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def grobid_endpoint(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/processHeaderDocument"


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


def extractor_metadata(
    job: PaperJob, parsed: dict[str, Any] | None = None
) -> dict[str, Any]:
    application = (parsed or {}).get("grobid_application", {})
    version = job.grobid_version or application.get("version") or "unknown"
    return {
        "name": "GROBID processHeaderDocument",
        "service_url": job.grobid_url,
        "version": version,
        "options": GROBID_REQUEST_OPTIONS,
    }


def base_result(
    job: PaperJob, status: str, *, pdf_details: dict[str, Any] | None = None
) -> dict[str, Any]:
    source = dict(job.source_metadata)
    if pdf_details:
        source.update(pdf_details)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "paper_id": job.paper_id,
        "source": source,
        "anthology": job.anthology_metadata,
        "extractor": extractor_metadata(job),
    }


def process_job(job: PaperJob) -> WorkResult:
    """Extract or reparse one paper and atomically persist its result."""
    try:
        if job.action == "reparse":
            tei = job.tei_path.read_bytes()
            parsed = parse_grobid_tei(tei)
            result = base_result(job, "success")
            result["extractor"] = extractor_metadata(job, parsed)
            result["grobid"] = parsed
            atomic_write_json(job.json_path, result)
            return WorkResult(job.paper_id, "reparsed")

        # A request supersedes any old completion marker. If this attempt is
        # interrupted or transiently fails, a normal rerun must try it again.
        job.json_path.unlink(missing_ok=True)
        if job.temporary_pdf:
            job.pdf_path.parent.mkdir(parents=True, exist_ok=True)
            job.pdf.download(job.pdf_path, timeout=job.timeout)
        elif not job.pdf_path.is_file():
            return WorkResult(job.paper_id, "transient-error", "local PDF disappeared")

        pdf_details = {
            "size": job.pdf_path.stat().st_size,
            "sha256": sha256_file(job.pdf_path),
        }
        response = request_grobid(
            job.pdf_path,
            job.grobid_url,
            job.timeout,
            job.retries,
        )
        if response.status_code == 204:
            job.tei_path.unlink(missing_ok=True)
            atomic_write_json(
                job.json_path,
                base_result(job, "no-content", pdf_details=pdf_details),
            )
            return WorkResult(job.paper_id, "no-content")
        if response.status_code == 503:
            return WorkResult(
                job.paper_id,
                "transient-error",
                "GROBID remained busy (HTTP 503) after retries",
            )
        if response.status_code != 200:
            result = base_result(job, "error", pdf_details=pdf_details)
            result["error"] = {
                "kind": "grobid-http",
                "status_code": response.status_code,
                "message": response.text[:2000],
            }
            job.tei_path.unlink(missing_ok=True)
            atomic_write_json(job.json_path, result)
            return WorkResult(job.paper_id, "error", f"HTTP {response.status_code}")

        tei = response.content
        if job.save_tei:
            atomic_write(job.tei_path, tei)
        else:
            job.tei_path.unlink(missing_ok=True)
        try:
            parsed = parse_grobid_tei(tei)
        except etree.XMLSyntaxError as exception:
            result = base_result(job, "error", pdf_details=pdf_details)
            result["error"] = {"kind": "invalid-tei", "message": str(exception)}
            atomic_write_json(job.json_path, result)
            return WorkResult(job.paper_id, "error", "invalid TEI")

        result = base_result(job, "success", pdf_details=pdf_details)
        result["extractor"] = extractor_metadata(job, parsed)
        result["grobid"] = parsed
        atomic_write_json(job.json_path, result)
        return WorkResult(job.paper_id, "success")
    except (OSError, requests.RequestException, RuntimeError, ValueError) as exception:
        # No completion marker is written for transient/local failures, so a
        # normal rerun tries the paper again.
        return WorkResult(job.paper_id, "transient-error", str(exception))
    finally:
        if job.temporary_pdf:
            try:
                job.pdf_path.unlink(missing_ok=True)
            except OSError:
                pass


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


def select_papers(
    anthology: Anthology,
    selectors: list[str],
) -> list[Paper]:
    """Resolve inferred year and publication/event selectors without duplicates."""
    selected: dict[str, Paper] = {}
    requested_years = {
        int(selector)
        for selector in selectors
        if len(selector) == 4 and selector.isdecimal()
    }
    matched_years: set[int] = set()
    if requested_years:
        for paper in anthology.papers():
            paper_year = int(paper.year)
            if paper_year in requested_years:
                selected.setdefault(paper.full_id, paper)
                matched_years.add(paper_year)
        if missing_years := requested_years - matched_years:
            values = ", ".join(str(year) for year in sorted(missing_years))
            raise ValueError(f"No Anthology papers were found for year(s): {values}")

    # Resolve every non-year selector before returning any work, so a typo
    # cannot leave a partially processed selection.
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
    return list(selected.values())


def make_job(
    paper: Paper,
    args: argparse.Namespace,
    temporary_dir: Path,
) -> tuple[str, PaperJob | None]:
    """Classify a paper as cached, reparsable, or needing GROBID."""
    if paper.pdf is None:
        return "no-pdf-reference", None
    if paper.is_deleted:
        return "deleted", None
    if paper.is_frontmatter and not args.include_frontmatter:
        return "frontmatter", None

    json_path, tei_path = paper_output_paths(args.cache_dir, paper)
    source = source_metadata(paper)
    anthology_metadata = anthology_paper_metadata(paper)
    existing = load_json(json_path)
    if (
        not args.force
        and existing is not None
        and cached_result_is_current(
            existing, source, save_tei=args.save_tei, tei_path=tei_path
        )
        and not (args.retry_errors and existing.get("status") == "error")
    ):
        if existing.get("anthology") != anthology_metadata and not args.dry_run:
            existing["anthology"] = anthology_metadata
            atomic_write_json(json_path, existing)
            return "metadata-updated", None
        return "cached", None

    action = "request"
    if not args.force and cached_tei_is_current(existing, source, tei_path):
        action = "reparse"
    local_path = canonical_pdf_path(args.pdf_root, paper)
    temporary_pdf = action == "request" and not local_path.is_file()
    pdf_path = download_cache_path(temporary_dir, paper) if temporary_pdf else local_path
    return action, PaperJob(
        paper_id=paper.full_id,
        pdf=paper.pdf,
        pdf_path=pdf_path,
        json_path=json_path,
        tei_path=tei_path,
        anthology_metadata=anthology_metadata,
        source_metadata=source,
        action=action,
        temporary_pdf=temporary_pdf,
        save_tei=args.save_tei,
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
        nargs="+",
        metavar="SELECTOR",
        help=(
            "Four-digit year or Anthology paper, volume, collection, or event ID; "
            "may be combined."
        ),
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
        help="Root of the local anthology-files PDF tree (default: %(default)s).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Directory for durable JSON and TEI cache shards (default: %(default)s).",
    )
    parser.add_argument(
        "--limit",
        type=positive_integer,
        default=None,
        help="Process at most this many uncached papers.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120,
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
        help="Re-extract papers even when a current cached result exists.",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Retry cached permanent GROBID/TEI errors.",
    )
    parser.add_argument(
        "--include-frontmatter",
        action="store_true",
        help="Also process volume frontmatter records.",
    )
    parser.add_argument(
        "--no-tei",
        dest="save_tei",
        action="store_false",
        help="Do not retain the raw GROBID TEI response.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report work without contacting GROBID or writing output.",
    )
    parser.set_defaults(save_tei=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_intermixed_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")

    anthology = Anthology.from_within_repo()
    try:
        papers = select_papers(anthology, args.selectors)
    except ValueError as exception:
        parser.error(str(exception))
    counts: Counter[str] = Counter()
    scheduled = 0
    completed = 0
    grobid_version: str | None = None
    pending: set[concurrent.futures.Future[WorkResult]] = set()

    def report(future: concurrent.futures.Future[WorkResult]) -> None:
        nonlocal completed
        completed += 1
        try:
            result = future.result()
        except (
            Exception
        ) as exception:  # pragma: no cover - worker catches expected errors
            counts["internal-error"] += 1
            print(f"Internal worker error: {exception}", file=sys.stderr)
            return
        counts[result.status] += 1
        if result.detail:
            print(f"{result.paper_id}: {result.status}: {result.detail}", file=sys.stderr)
        elif result.status not in {"success", "reparsed"}:
            print(f"{result.paper_id}: {result.status}", file=sys.stderr)
        if completed % 100 == 0:
            print(f"Completed {completed}/{scheduled} scheduled papers.", file=sys.stderr)

    with (
        tempfile.TemporaryDirectory(prefix="acl-anthology-grobid-") as temporary,
        concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor,
    ):
        temporary_dir = Path(temporary)
        for paper in papers:
            disposition, job = make_job(paper, args, temporary_dir)
            if job is None:
                counts[disposition] += 1
                continue
            if args.limit is not None and scheduled >= args.limit:
                break
            scheduled += 1
            counts[f"scheduled-{disposition}"] += 1
            if args.dry_run:
                print(f"{paper.full_id}: {disposition}")
                continue
            if disposition == "request" and grobid_version is None:
                try:
                    grobid_version = check_grobid(args.grobid_url, args.timeout)
                except (requests.RequestException, RuntimeError) as exception:
                    print(f"Could not connect to GROBID: {exception}", file=sys.stderr)
                    if args.grobid_url.rstrip("/") == DEFAULT_GROBID_URL:
                        print(
                            "Start the local service with 'make grobid', then retry.",
                            file=sys.stderr,
                        )
                    return 2
                print(
                    f"Using GROBID {grobid_version} at {args.grobid_url}.",
                    file=sys.stderr,
                )
            if grobid_version is not None:
                job = replace(job, grobid_version=grobid_version)
            pending.add(executor.submit(process_job, job))
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
