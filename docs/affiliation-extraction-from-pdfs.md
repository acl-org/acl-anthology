# Plan: extracting author affiliations from PDFs

**Status:** Extraction spike implemented; evaluation and integration pending
**Date:** 2026-07-18
**Related code:** [`bin/extract_pdf_metadata.py`](../bin/extract_pdf_metadata.py)

## Motivation

The `<affiliation>` field of `<author>` tags currently draws on **OpenReview
author profiles**, which has two consequences:

1. **It is a profile, not a byline.** OpenReview reports where the author is
   registered (their current / submission-time institution), which is not
   necessarily the affiliation printed on the paper — i.e. where the work was
   actually done. Interns, visitors, and authors who have since moved are all
   mislabelled.
2. **It only covers OpenReview-managed venues.** Roughly a quarter of author
   listings currently carry an affiliation at all, skewed to recent years.

The paper's own byline is the authoritative, paper-intrinsic source and exists
for essentially every PDF, historical ones included. Extracting it would make the
affiliation data both more accurate and far broader.

## Goal

For each paper, obtain `(author → affiliation string)` from the PDF byline,
normalize organization identities where possible, and use it to augment or
replace the OpenReview-derived affiliations — with clear provenance.

## Recommended approach: GROBID

Use [GROBID](https://github.com/kermitt2/grobid), a tool purpose-built to parse
scholarly-PDF headers into structured `author → affiliation → organization`
records. It is the realistic path because it solves the hard part that a
from-scratch parser does not: **associating each affiliation with the correct
author** (the superscript-marker problem). It also resolves organization names
and can emit ROR identifiers directly.

### Why not a DIY parser

- `pypdf` / `pdfminer` yield a flat text stream that destroys the multi-column
  layout and the superscript ↔ author linking that carry the affiliation
  structure.
- An LLM over the first page works per paper but is not offline, deterministic,
  or cheap across ~130k papers.

The linking problem — not the text extraction — is ~80% of the difficulty, and it
is exactly what GROBID is trained for.

## Architecture

The extraction spike uses an offline-batch → local-cache pipeline:

1. **Extract:** run GROBID (Docker service) over the PDF corpus → TEI XML.
2. **Parse:** retain lossless TEI and project useful fields into per-paper JSON
  shards in a local cache. Whether a curated result is later committed remains
  an integration decision.
3. **Normalize:** retain GROBID's structured organization output and ROR IDs
  where available; choose the final normalization policy during integration.
4. **Consume:** align extracted authors with Anthology `NameSpecification`s and
  augment or replace canonical affiliation metadata with clear provenance.

## Implemented extraction command

`bin/extract_pdf_metadata.py` implements the extraction and parsing spike. It
requires an explicit selection, so an accidental invocation cannot enqueue the
entire Anthology:

```console
# Pull and start the pinned GROBID service, then wait until it is ready
make grobid

# Every paper whose Anthology year is 2025
bin/extract_pdf_metadata.py 2025 -j 4

# A paper, a volume, and an event; overlapping papers are processed once
bin/extract_pdf_metadata.py \
  2025.acl-long.1 2025.acl-long acl-2025 -j 4
```

`make grobid` requires a running Docker daemon and starts a reusable named
container in the background at `http://localhost:8070`. It defaults to the
GROBID 0.9.0 full image because its header and affiliation models are more
accurate. The initial pull is approximately 10 GB. For a smaller, faster
CRF-only service, use:

```console
make grobid GROBID_IMAGE=grobid/grobid:0.9.0-crf
```

The target is idempotent: it reuses a healthy service, restarts its stopped
container, and replaces the managed container when `GROBID_IMAGE` changes.
Stop it with `docker stop acl-anthology-grobid`; a later `make grobid` restarts
it. The image is currently amd64-only, so the target explicitly enables Docker
emulation on Apple Silicon.

Selectors are positional and may be mixed freely. A four-digit selector is a
year; every other selector is resolved as a paper, volume, collection, or event
ID. An event selects both its own collection volumes and its colocated volumes.
Multiple selectors form a deduplicated union. Frontmatter is skipped unless
`--include-frontmatter` is given. Use `--dry-run` to inspect the selection and
`--limit N` for a bounded spike.

The script first looks for each PDF under `~/anthology-files/pdf` (overridable
with `--pdf-root`). If it is absent, the public `PDFReference` downloads it into
a run-scoped temporary directory. A downloaded PDF is deleted as soon as its
job finishes, including on failure; PDFs are not copied into the durable cache.

Results default to the platform-specific cache returned by
`PlatformDirs("acl-anthology")`, under its `grobid` directory. This is typically
`~/Library/Caches/acl-anthology/grobid` on macOS and
`~/.cache/acl-anthology/grobid` on Linux. `--cache-dir` overrides it. Each paper
has independent shards:

```text
papers/<collection>/<volume>/<paper>.json
papers/<collection>/<volume>/<paper>.tei.xml
```

The TEI is the lossless GROBID response. The JSON projection preserves ordered
authors; name parts; email, phone, and author identifiers; explicit
author-to-affiliation links; raw and structured affiliations; organization and
address fields; title, abstract, keywords, identifiers, dates, languages,
journal and publisher fields, meetings, funders, copyright, and GROBID version
metadata. It also records the corresponding Anthology paper and author metadata
for later alignment.

### Idempotence and retries

Each shard is written through an atomic temporary-file replacement, with JSON
written last as the completion marker. A normal rerun skips a result only when
its schema version, PDF reference/checksum, GROBID request options, and required
TEI file still match. Anthology metadata can be refreshed in-place without
calling GROBID. Stale JSON may be rebuilt from TEI only when the old completion
record proves that the TEI came from the same PDF and request options.

Connection failures and GROBID HTTP 503 responses are transient and retried;
they leave no completion marker after the final failure, so the next run tries
again. Permanent HTTP or malformed-TEI failures are cached. Use `--retry-errors`
to retry only those cached failures, or `--force` to run every selected paper
through GROBID again. `-j N` controls the bounded thread pool used for requests.

## The genuinely hard parts / risks

- **Author ↔ affiliation linking** on many-author papers is where GROBID's errors
  concentrate; it needs validation, not blind trust.
- **Aligning GROBID authors to our `NameSpecification`s** (by order + name) so the
  affiliation attaches to the right person in our data model.
- **Historical coverage:** modern PDFs parse well; pre-~2010 and scanned pages
  parse poorly. This is the *opposite* bias from OpenReview (recent-only), so the
  two sources are complementary rather than redundant.
- **Corpus access + compute:** a one-time batch over ~130k PDFs (parallelizable).
  Only a partial corpus is on any single dev machine; the full set lives on the
  server.
- **Reconciliation & provenance (a maintainer decision):** do PDF affiliations
  override the OpenReview ones or only fill gaps? The canonical home is the
  `<affiliation>` tag, so the source should be recorded either way.

## Phased plan

1. **Spike (decisive, small):** stand up GROBID; run it on ~100 recent + ~100
   older papers. Measure (a) affiliation precision/recall and (b) how often it
   agrees with / beats the OpenReview value, and how well author-linking holds.
   This establishes the real accuracy ceiling before any pipeline work.
2. **Batch pipeline (if the spike is promising):** GROBID service + TEI parser →
  per-paper-author affiliation cache; wire it into the chosen normalization and
  reconciliation pipeline.
3. **Reconciliation & surfacing:** decide the override/fill policy, record
  provenance, and expose it on author and paper pages.

## Open questions

- Override policy: PDF-first, OpenReview-first, or per-field confidence?
- Storage: write extracted affiliations back into `data/xml` `<affiliation>`
  tags (with a source attribute), or keep a separate derived cache?
- Do we keep a running GROBID step in ingestion, or re-run periodically over the
  whole corpus?

## References

- GROBID: <https://github.com/kermitt2/grobid>
- ROR (organization identity and metadata): <https://ror.org>
