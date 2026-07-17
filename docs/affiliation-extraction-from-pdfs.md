# Plan: extracting author affiliations from PDFs

**Status:** Proposal / draft — not yet implemented
**Date:** 2026-07-17
**Related code:** [`bin/geocode_affiliations.py`](../bin/geocode_affiliations.py),
`export_affiliation_map()` in [`bin/create_hugo_data.py`](../bin/create_hugo_data.py),
[`data/geo/`](../data/geo/), the `/stats` "Where authors work" map.

## Motivation

The affiliation map on the statistics page draws on the `<affiliation>` field of
`<author>` tags. Today that data comes from **OpenReview author profiles**, which
has two consequences:

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
normalize it through the existing ROR matcher, and use it to augment or replace
the OpenReview-derived affiliations — with clear provenance.

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

This reuses the offline-batch → cache → normalize shape already established for
the affiliation map, so only the *source* of affiliation strings is new:

1. **Extract:** run GROBID (Docker service) over the PDF corpus → TEI XML.
2. **Parse:** convert TEI to `(paper_id, author_index) → raw affiliation string`,
   written to a committed cache (analogous to `data/geo/affiliation_geocache.json`).
3. **Normalize:** feed the strings through the **existing** ROR matcher in
   `bin/geocode_affiliations.py` — no new normalization/geocoding code needed.
4. **Consume:** `export_affiliation_map()` and any per-paper display read the
   richer cache.

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
   per-paper-author affiliation cache; wire it into the existing ROR
   normalization.
3. **Reconciliation & surfacing:** decide the override/fill policy, record
   provenance, and expose it (map + author/paper pages).

## Open questions

- Override policy: PDF-first, OpenReview-first, or per-field confidence?
- Storage: write extracted affiliations back into `data/xml` `<affiliation>`
  tags (with a source attribute), or keep a separate derived cache?
- Do we keep a running GROBID step in ingestion, or re-run periodically over the
  whole corpus?

## References

- GROBID: <https://github.com/kermitt2/grobid>
- ROR (already used for coordinates + org type): <https://ror.org>
- Current affiliation pipeline: `bin/geocode_affiliations.py`,
  `export_affiliation_map()` in `bin/create_hugo_data.py`.
