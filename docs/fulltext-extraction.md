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

`hugo/static/.htaccess` serves them under the paper ID, alongside the existing
`.pdf` and `.bib` shortcuts:

```text
https://aclanthology.org/2025.acl-long.1.json
https://aclanthology.org/P17-1069.json
```

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

The instructions below are for the current server, Ubuntu 20.04 LTS.

### 1. Prerequisites

Ubuntu 20.04 ships Python 3.8, which is too old for `acl_anthology` (>3.11),
and it is past its standard support window. Neither is a blocker: `uv` provides
its own interpreter, and the job only needs Docker, `uv`, `git`, `curl`, and
`flock`.

```console
$ sudo apt update
$ sudo apt install git curl ca-certificates util-linux
```

Docker no longer lists 20.04 as a supported release, but its `apt` repository
still carries `focal` packages:

```console
$ sudo install -m 0755 -d /etc/apt/keyrings
$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
$ sudo chmod a+r /etc/apt/keyrings/docker.gpg
$ echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu focal stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list
$ sudo apt update && sudo apt install docker-ce docker-ce-cli containerd.io
$ sudo systemctl enable --now docker
```

The job must run Docker without `sudo`, so add its user to the `docker` group
and start a fresh login session:

```console
$ sudo usermod -aG docker anthology
$ newgrp docker && docker info >/dev/null && echo ok
```

Note that membership in `docker` is equivalent to root on the host.

Then install `uv` as the job's user:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | sh   # into ~/.local/bin
$ cd ~/acl-anthology && uv sync                     # fetches its own Python
$ uv run python -c "import acl_anthology; print(acl_anthology.__version__)"
```

Disk is the thing to check before starting: the GROBID image and the extraction
tree both want room. See [backfill](#4-backfill) below.

### 2. GROBID

The cron wrapper manages the container itself, so the only prerequisite is a
working Docker daemon for the user that runs the job. The wrapper creates the
container with `--restart unless-stopped`, so it survives reboots and later runs
reuse it.

Docker is not a hard requirement. The extractor only speaks HTTP to
`--grobid-url`, and the wrapper touches Docker only when nothing answers at
`GROBID_URL`. A GROBID [installed from
source](https://grobid.readthedocs.io/en/latest/Install-Grobid/), or running on
another host, works just as well — set `GROBID_URL` and Docker is never used.
The container is simply the path of least resistance here: upstream calls it the
standard deployment, the image bundles the JVM, the `pdfalto` binary and the
models, none of which then have to be maintained on a host whose Java and
Python are both too old, and the version stays pinned to the same image the
`make grobid` target uses on developer machines.

The default image is `grobid/grobid:0.9.0-full`, whose header and affiliation
models are the more accurate ones, but it is the wrong trade for this job: it is
about 8 GB because it carries TensorFlow and pre-loaded embeddings, and without
a GPU its deep-learning models are considerably slower. Upstream recommends the
lightweight CRF-only image (about 500 MB) precisely for full-text extraction
feeding search, so set it here:

```console
$ GROBID_IMAGE=grobid/grobid:0.9.0-crf bin/aclanthology.org/grobid-cronjob.sh
```

The image is only read when the container is *created* — `docker rm -f
acl-anthology-grobid` first if you are switching.

The port is published on `127.0.0.1` only — the service must not be reachable
from the outside. To check on it by hand:

```console
$ docker ps --filter name=acl-anthology-grobid
$ curl -s localhost:8070/api/version
$ docker logs --tail 50 acl-anthology-grobid
```

### 3. Cron entry

```cron
PATH=/home/anthology/.local/bin:/usr/local/bin:/usr/bin:/bin
20 3 * * * /home/anthology/acl-anthology/bin/aclanthology.org/grobid-cronjob.sh >> /var/log/anthology/grobid.log 2>&1
```

The `PATH` line matters: cron's default `PATH` does not include `~/.local/bin`,
so `uv` would not be found. The wrapper says so explicitly if that happens; the
alternative is to set `UV=/home/anthology/.local/bin/uv`.

Create the log directory first (`sudo install -d -o anthology /var/log/anthology`)
and add a `logrotate` entry for it.

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
| `UV` | `uv` | Path to the `uv` binary |

`GROBID_GIT_PULL` matters only if nothing else updates the checkout: papers
ingested since the last run are invisible until the XML is current.

Before trusting the schedule, run the wrapper once by hand with a small cap:

```console
$ GROBID_LIMIT=5 bin/aclanthology.org/grobid-cronjob.sh
```

### 4. Backfill

The first run has the whole corpus to process. Set `GROBID_LIMIT` to a
manageable number of papers so each nightly run does a bounded amount of work
and the backfill proceeds over successive nights; remove it once the corpus is
covered. Every run is resumable — an interrupted paper simply has no output file
and is picked up next time.

Budget disk accordingly: the JSON for a paper is roughly the size of its text,
so the full corpus adds up to tens of gigabytes. The files compress very well;
serve them with on-the-fly gzip if they are ever exposed.

### 5. Throughput

Extraction is already parallel: `--jobs N` (`GROBID_JOBS`) runs N concurrent
GROBID requests from a bounded thread pool. The default when calling the script
directly is 1, which is why an unadorned run looks serial; the cron wrapper
passes 4. Every hundred papers the run prints its rate, which is the number to
extrapolate from:

```text
Extracted 400/1603 scheduled papers (2.7/s).
```

The ceiling is the service, not the client. GROBID processes requests from a
pool sized by `concurrency` in `grobid-home/config/grobid.yaml`, default 10;
beyond that it answers HTTP 503, which this script treats as transient and
retries with backoff. So raising `--jobs` past 10 buys nothing until that
configuration changes, and environment variables can no longer be used for it —
the file has to be mounted into the container:

```console
$ docker run ... -v /path/to/grobid.yaml:/opt/grobid/grobid-home/config/grobid.yaml:ro ...
```

Upstream advises setting `concurrency` slightly above the host's thread count.
A good starting point is therefore `--jobs` ≈ `nproc`, capped at 10 until the
config is mounted. Watch memory as well: GROBID wants roughly 4 GB for
full-text processing and 6–8 GB under parallel batch load.

On the current server — 8 CPUs, also serving aclanthology.org — use half the
machine and enforce it in the container rather than trusting the client:

```console
$ docker run --detach --name acl-anthology-grobid \
    --restart unless-stopped --init --ulimit core=0 \
    --cpus 4 --publish 127.0.0.1:8070:8070 \
    grobid/grobid:0.9.0-crf

$ GROBID_JOBS=4 GROBID_LIMIT=2000 bin/aclanthology.org/grobid-cronjob.sh
```

Each concurrent request keeps roughly one core busy, so `--cpus 4` leaves four
for the web server and the system, and the cap covers the `pdfalto` child
processes too. Setting `--jobs` above the cap only queues work inside GROBID
and raises its memory use, so keep the two numbers equal. The client itself is
almost idle — it waits on HTTP — apart from the one-off Anthology load at
startup.

Watch `docker stats acl-anthology-grobid` and site latency during the first
capped run before changing anything. If the site is unaffected, `--cpus 6` is
the next step; the backfill runs at night, when traffic is lowest.

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

### Testing a single PDF

`--pdf FILE` reads one PDF from anywhere instead of from the tree. It needs a
selector matching exactly one paper — that paper supplies the `metadata` block
and determines where the output lands — and it implies `--force`, so repeated
test runs always re-extract:

```console
make grobid    # once, to have a service running

bin/grobid/extract_pdf_fulltext.py 2025.acl-long.1 \
    --pdf ~/Downloads/paper.pdf \
    --output-root /tmp/grobid-test

jq . /tmp/grobid-test/acl/2025.acl-long.1.json
```

Point `--output-root` at a scratch directory so the test never touches the real
extraction tree. To test a PDF that is already in the tree, drop `--pdf` and
pass `--force` instead.

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
