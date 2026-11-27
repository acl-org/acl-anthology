---
name: ingest-videos
description: >-
  Download and ingest ACL Anthology presentation videos from an Underline
  proceedings spreadsheet. Use for conference/workshop video batches: snapshot
  the sheet on the archive server, download and validate recordings, match using
  the public acl_anthology API and actual video evidence, move verified matches,
  retain unmatched sources, and save per-record TSVs and a report on the server.
  Not for proceedings/PDF ingestion, revisions, or deleting historical leftovers.
---

# Ingesting presentation videos

Use the bundled [server workflow](./scripts/server.py) and
[metadata workflow](./scripts/metadata.py). They share
[validation helpers](./scripts/common.py); optional
[macOS on-device OCR](./scripts/ocr_frames.swift) verifies actual frames.

## Confirm scope and preserve state

1. Confirm the spreadsheet URL/tab, SSH target, report directory, staging
   directory, and canonical video root. For the Anthology, the SSH target is
   normally `anth`; resolve `/home/anthologizer/files/` rather than assuming its
   backing mount. Use a **new, dedicated** report directory per batch.
2. Ask whether to include workshops and cross-presented papers (TACL/CL/other
   conferences), and whether matched files should actually **move** or remain as
   staging hardlinks. Unmatched/uncertain recordings always remain untouched.
3. Check the worktree, disk capacity, Python, and ffmpeg. Preserve unrelated
   changes; never rewrite a user's dirty lockfile. Use
   `UV_FROZEN=true UV_NO_SYNC=true` when reusing the existing environment.
4. Do not commit, push, deploy, delete historical sources, or post GitHub
   comments unless requested. Any generated GitHub comment must visibly say
   **Bot-generated**, with a one-sentence observation and optional collapsed
   evidence.

## Snapshot and discover

Save the Google sheet's CSV and TSV exports on the server, including their
SHA256s and original URL. Keep `spreadsheet.tsv` in both the batch staging
directory and its report directory. The public export URLs are:

```text
https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=TAB_ID
https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=tsv&gid=TAB_ID
```

Preserve the original matching snapshot if the sheet changes later; record
snapshot times and differences rather than silently replacing ingestion inputs.
Google TSV exports contain literal quote characters: compare their cells using
`csv.QUOTE_NONE`, not CSV quote handling. Keep the CSV snapshot as the matching input.

Copy `common.py` and `server.py` into a private `tooling/` subdirectory of the
report directory. CSV columns must include `Title`, `Paper number`, `video`, and
`Frontend URI`; only explicit `video=yes` rows are downloadable recordings.

```bash
python3 tooling/server.py catalog --report REPORT --workers 2
```

The public Underline API requires `Accept: application/vnd.api+json`. Request
only the **specific lecture ID**, not related/recommended lectures. The script
records titles, paper-link hints, author names, the released playlist, and its
highest-resolution rendition. It refuses non-free, encrypted, or
unfinished/live recordings; do not bypass access controls. Unpublished recordings
are skipped by default. With explicit user authorization, `catalog
--include-unpublished` downloads their free playlists **into retained staging
only**: `publication_allowed=false` is enforced during review, placement, metadata
annotation, and finalization, even if the paper identity is verified. Staged MP4s
are mode `0600`; held recordings are never made web-readable. Placement also
checks the original server-side download registry, so a manual review cannot
accidentally remove a publication hold.

Review catalog failures and total estimated bytes against free storage before
downloading. If highest-quality renditions will not fit, ask the user how to
proceed; do not silently downgrade quality or delete unrelated media.
Respect HTTP 429/`Retry-After`: the client throttles API requests, closes error
responses, cancels queued work on a rate limit, and records `rate-limit.json`.
Wait for the specified cooldown before retrying; reuse already verified catalog
receipts rather than repeatedly fetching the entire sheet.

## Download first

```bash
python3 tooling/server.py download --report REPORT --staging STAGING \
  --ffmpeg FFMPEG --workers 2
```

Use bounded workers (maximum four) on the shared server. The script downloads
the original HTTPS MPEG-TS segments with Python, then ffmpeg remuxes the local
HLS rendition into MP4 without re-encoding. This separates network transport
from ffmpeg (the previously installed static binary crashes on HTTPS input).
Each recording must fully
decode, preserve the original source's frame count and timing, and produce three
actual frames. Receipts contain SHA256, inode/size/mtime, decoded duration and
frame count. Completed downloads are reused only after fingerprint and checksum
validation; failed partial files are retained with explicit failure logs.
HLS `EXTINF` durations can be rounded: compare actual source timing and frame
counts, not an arbitrary tolerance against the rounded playlist. Coded packet
counts are a fast check, not necessarily decoded frame counts. If they differ,
fully decode the original HLS too and require its frame count/timing to match
the archived MP4; never simply allow a one-frame loss.
Only named temporary segment files are removed after the verified MP4 receipt
is durable; unmatched original MP4s are retained.

Failures are not successful ingestions. Retry only the failed work through the
same resumable commands; never download blindly over an existing source.
`download-job.json` records the PID, start time, progress, and outcome; each
completed recording has an individual durable receipt. The phase lock rejects
duplicate concurrent runs. Keep long-running jobs supervised, and verify their
PID/progress before reporting them as running.

## Match authoritative metadata and actual content

Copy the frozen spreadsheet, `catalog-results.json`, `download-results.json`,
and actual `frames/` into a local audit directory. From the repository:

```bash
uv run .github/skills/ingest-videos/scripts/metadata.py export --report LOCAL
```

All authoritative data access and edits use the **public** `acl_anthology`
library. Do not parse XML/people JSON directly. Matching preserves significant
digits and uses exact normalized titles, including unique title fallback when a
sheet paper link is stale. Export searches publication years referenced by the
sheet; expand the search through the library if an unmatched title might be
published in another year. Do not call an unsearched title nonexistent.

On macOS, compile the OCR helper outside the repository, feed it one actual
frame path per line, and save its JSONL output. Otherwise inspect actual frames
directly and use recording-bound manual decisions:

```bash
swiftc .github/skills/ingest-videos/scripts/ocr_frames.swift -o LOCAL/ocr-frames
LOCAL/ocr-frames < LOCAL/frame-paths.txt > LOCAL/ocr.jsonl
uv run .github/skills/ingest-videos/scripts/metadata.py review \
  --report LOCAL --ocr LOCAL/ocr.jsonl
```

An automatic match requires the **full title and a full author name in the same
actual video frame**. Provider labels and filenames alone are not identity
evidence. Other-paper matches are review flags: slides may legitimately cite
other papers. Never automatically reassign based on a citation or fuzzy title.

Inspect remaining cases using additional frames, narration, and primary-paper
or project evidence. Preserve meaningful short posters, demos, broader
coauthor talks, and uncertain associations; duration alone is not an error.
If a venue has a confirmed wrong assignment, inspect its whole batch.

For manual decisions, save an object keyed by lecture ID and use `--manual`:

```json
{
  "LECTURE_ID": {
    "verdict": "verified",
    "paper_id": "YEAR.VENUE-VOLUME.PAPER",
    "sha256": "FULL_DOWNLOADED_RECORDING_SHA256",
    "evidence": "Specific observed title, author, narration, or primary-source evidence."
  }
}
```

Other verdicts are `unmatched`, `unusable`, and `needs-review`. Never guess a
replacement paper. Existing `permission=false` references block publication.

## Place, annotate, validate, then move

Copy `reviewed.json` to the server. Stage verified canonicals without removing
sources yet:

```bash
python3 tooling/server.py place --report REPORT --staging STAGING --videos VIDEOS
```

The script reuses an already-linked identical recording only with full SHA256
proof. Otherwise it allocates an unoccupied canonical/numbered filename and
creates an exclusive hardlink. It never overwrites an existing recording.
Copy `placements.json` back locally:

```bash
uv run .github/skills/ingest-videos/scripts/metadata.py apply --report LOCAL
uv run .github/skills/ingest-videos/scripts/metadata.py apply --report LOCAL --write
uv run .github/skills/ingest-videos/scripts/metadata.py validate --report LOCAL
```

The dry run precedes saving. Saved/reloaded models must preserve non-video
metadata, original video order, and withholding; originals of affected XML
collections remain in the audit directory. `validate` records the exact
`UV_FROZEN=true UV_NO_SYNC=true just check` result and log checksum; movement
refuses a pending or failed check. Do not build the website unless
requested. Copy `metadata-validation.json` to the server **only after checks
pass**:

```bash
python3 tooling/server.py finalize --report REPORT --staging STAGING \
  --videos VIDEOS --placement move
```

Use `--placement hardlink-retain` if the user chose to retain matched staging
sources. Actual movement is **exclusive canonical hardlink creation followed by
guarded source unlinking**, after metadata and public HTTP/size/MIME checks.
Durable intents/receipts permit resuming only the same verified actions.
Unmatched originals are fingerprint-checked after finalization.

## Persist TSVs and report

Copy `finalized.json` back locally, generate reports, then copy them to the
server's report directory:

```bash
uv run .github/skills/ingest-videos/scripts/metadata.py report --report LOCAL
```

Persist:

- `videos.tsv`: every supplied recording and outcome.
- `videos-linked.tsv`: verified paper IDs, canonical paths, original paths,
  SHA256, metadata operation, and movement mode.
- `videos-unmatched.tsv`: retained/failed recordings and concrete reasons.
- `summary.json` and `report.md`: counts, validation, limitations, and deployment
  state.
- Catalog/download/placement/movement receipts, actual-frame evidence, failure
  logs, source snapshot, and metadata validation.

Read back server copies and verify SHA256/totals. Reconcile every listed
recording exactly once; report unavailable downloads and unresolved identities
separately. Record which requested metadata has been saved versus merged and
deployed. Never claim exhaustive correctness from a sample or mistake staging
leftovers for missing ingestion.
