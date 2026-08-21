# Full-text extraction from PDFs with GROBID

**Related code:** [`bin/grobid/extract_pdf_fulltext.py`](../bin/grobid/extract_pdf_fulltext.py),
[`bin/aclanthology.org/grobid-cronjob.sh`](../bin/aclanthology.org/grobid-cronjob.sh)

## What this does

A GROBID service runs continuously on the server. A cron job wakes up
periodically, finds every PDF that has no up-to-date extraction, and writes one
JSON file into a `grobid` tree that mirrors the PDF tree exactly:

```text
anthology-files/pdf/acl/2025.acl-long.1.pdf  ->  anthology-files/grobid/acl/2025.acl-long.1.json
anthology-files/pdf/W/W00/W00-1323.pdf       ->  anthology-files/grobid/W/W00/W00-1323.json
```

Both PDF layouts are mirrored as-is: `pdf/{venue_id}/` for new-style IDs and
`pdf/{oldstyle_letter}/{collection_id}/` for old-style ones. Keeping the
extractions in a parallel tree leaves the PDF tree untouched, so the two can be
synced, served, or discarded independently. Override the roots with
`--pdf-root` and `--output-root`.

The motivating use is custom full-text search: each file carries both the
Anthology's own metadata and GROBID's document structure, so an indexer can
build one document per paper with separate fields — authors, venue names,
title, abstract, body sections, references — and report *which* field a query
matched. This document describes the extraction; the index itself is a separate
component.

This is distinct from [affiliation extraction](affiliation-extraction-from-pdfs.md),
which calls GROBID's header endpoint and writes to a developer cache. This job
calls `processFulltextDocument` and writes to the file tree.

## Server setup

### 1. GROBID

The cron wrapper manages the container itself, so the only prerequisite is a
working Docker daemon for the user that runs the job. The wrapper creates the
container with `--restart unless-stopped`, so it survives reboots and later runs
reuse it.

The default image is `grobid/grobid:0.9.0-full`, whose header and affiliation
models are the more accurate ones. The image is large (approximately 10 GB) and
the service is memory hungry; for a smaller, faster CRF-only service set
`GROBID_IMAGE=grobid/grobid:0.9.0-crf`. The port is published on `127.0.0.1`
only — the service must not be reachable from the outside.

### 2. Cron entry

```cron
20 3 * * * /home/anthology/acl-anthology/bin/aclanthology.org/grobid-cronjob.sh >> /var/log/anthology/grobid.log 2>&1
```

The wrapper serializes runs with `flock`, so a long run is never overlapped by
the next scheduled one; a blocked run logs a line and exits successfully.

It is configured entirely through the environment:

| Variable | Default | Purpose |
| --- | --- | --- |
| `GITDIR` | the checkout containing the script | Repository whose XML is scanned |
| `ANTHOLOGYFILES` | `~/anthology-files` | Root holding the `pdf/` and `grobid/` trees |
| `GROBID_GIT_PULL` | `false` | Fast-forward `GITDIR` before scanning |
| `GROBID_IMAGE` | `grobid/grobid:0.9.0-full` | Image to run |
| `GROBID_CONTAINER` | `acl-anthology-grobid` | Container name |
| `GROBID_PORT` | `8070` | Localhost port for the service |
| `GROBID_JOBS` | `4` | Concurrent extraction requests |
| `GROBID_LIMIT` | unset | Cap on papers sent to GROBID per run |
| `GROBID_LOCKFILE` | `/tmp/acl-anthology-grobid-fulltext.lock` | Run lock |

`GROBID_GIT_PULL` matters only if nothing else updates the checkout: papers
ingested since the last run are invisible until the XML is current.

### 3. Backfill

The first run has the whole corpus to process. Set `GROBID_LIMIT` to a
manageable number of papers so each nightly run does a bounded amount of work
and the backfill proceeds over successive nights; remove it once the corpus is
covered. Every run is resumable — an interrupted paper simply has no output file
and is picked up next time.

Budget disk accordingly: the JSON for a paper is roughly the size of its text,
so the full corpus adds up to tens of gigabytes. The files compress very well;
serve them with on-the-fly gzip if they are ever exposed.

## Running it by hand

```console
# everything new or stale, using the Makefile's managed container
make fulltext GROBID_JOBS=8 ANTHOLOGYFILES=~/anthology-files

# or directly, with the default ~/anthology-files roots
bin/grobid/extract_pdf_fulltext.py --all -j 8

# a bounded selection: papers, volumes, collections, events, or a year
bin/grobid/extract_pdf_fulltext.py 2025.acl-long.1 acl-2025
```

`--dry-run` reports what a run would do without contacting GROBID. `--limit N`
bounds the work. `--force` re-extracts current papers, and `--retry-errors`
retries only those whose recorded status is a permanent GROBID or TEI error.

Papers whose PDF is not in the local tree are counted as `missing-pdf` and
skipped; unlike the header-extraction spike, this job never downloads PDFs,
because it is meant to run where the canonical files already are.

## Incremental behavior

A paper is sent to GROBID when any of the following holds:

- it has no JSON file in the extraction tree;
- the recorded PDF `checksum` (from the XML) or `size` no longer matches;
- the recorded `schema_version` or GROBID request options are out of date;
- `--force`, or `--retry-errors` for a recorded error.

Notably, an unchanged PDF is *never* re-read from disk, so a scan over the whole
corpus costs one `stat` and one small JSON read per paper. When only the
Anthology metadata changed — a corrected title, a new author ID — the `metadata`
block is rewritten in place and GROBID is not called.

Writes are atomic: the JSON file is replaced only once it is complete, and any
existing file is removed before a request begins, so an interrupted run leaves
no half-written or stale-but-plausible output.

## Output schema

```jsonc
{
  "schema_version": 1,
  "status": "success",            // or "no-content", "error"
  "paper_id": "2025.acl-long.1",
  "extracted": "2026-08-21T03:24:11Z",
  "source": { "reference": "2025.acl-long.1", "checksum": "…", "size": 481203 },
  "extractor": {
    "name": "GROBID processFulltextDocument",
    "version": "0.9.0",
    "service_url": "http://localhost:8070",
    "options": { "consolidateHeader": "0", "…": "…" }
  },
  "metadata": {                   // from the Anthology XML
    "title": "…", "abstract": "…",
    "authors": ["…"], "editors": ["…"],
    "venues": [{ "id": "acl", "acronym": "ACL", "name": "…" }],
    "events": ["acl-2025"], "sigs": ["…"],
    "year": "2025", "month": "…",
    "volume_id": "2025.acl-long", "volume_title": "…",
    "bibkey": "…", "doi": "…", "language": "…", "url": "…", "awards": ["…"]
  },
  "fulltext": {                   // from the PDF, absent unless status is "success"
    "title": "…",
    "authors": [{ "name": "…", "affiliations": ["…"], "email": "…", "orcid": "…" }],
    "abstract": "…",
    "keywords": ["…"],
    "sections": [{ "n": "1", "head": "Introduction", "paragraphs": ["…"] }],
    "back_sections": [{ "type": "acknowledgement", "head": "…", "paragraphs": ["…"] }],
    "references": [{ "title": "…", "authors": ["…"], "venue": "…", "year": "…", "doi": "…" }],
    "stats": { "sections": 8, "paragraphs": 63, "references": 41, "body_characters": 38210 }
  }
}
```

Two rules keep the schema predictable: empty values are omitted rather than
written as `null` or `[]`, and document order is preserved everywhere — authors,
sections, paragraphs, and references. Bump `SCHEMA_VERSION` in the script when
the projection changes; the next run then re-extracts everything.

`status` distinguishes the three durable outcomes: `success` (a `fulltext`
block is present), `no-content` (GROBID returned HTTP 204 for a PDF it could not
parse, typically a scan), and `error` (a permanent HTTP or malformed-TEI
failure, with an `error` block explaining it). Transient failures — connection
errors, a busy service — deliberately leave no file behind so the next run
retries them.

## Notes for the search index

- The `metadata` and `fulltext` blocks are deliberately parallel: `metadata` is
  authoritative and clean, `fulltext` is PDF-intrinsic and noisier. Index them
  as separate fields so a hit can be attributed to a source, and prefer
  `metadata` when the two disagree.
- Section heads and paragraph boundaries survive extraction, so a body hit can
  be reported as "matched in *Section 3, Method*" and snippets can be cut at
  paragraph boundaries.
- Historical coverage is uneven. Modern PDFs parse well; pre-2010 and scanned
  pages parse poorly or return `no-content`. The index should treat a missing or
  empty `fulltext` block as normal and fall back to `metadata` alone.
- References are extracted too, which makes citation-text search possible, but
  they are the noisiest part of the output.

## References

- GROBID: <https://github.com/kermitt2/grobid>
- GROBID REST API: <https://grobid.readthedocs.io/en/latest/Grobid-service/>
