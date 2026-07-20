---
name: ingest-proceedings
description: >-
  Ingest ACL Anthology proceedings (main conferences AND colocated workshops)
  from ACLPUB or aclpub2 tarballs using bin/ingest.py. USE WHEN ingesting one or
  more proceedings repos/tarballs into the Anthology — a standalone/main event
  (create its <event> block), or workshops colocated under a parent event
  (e.g. acl-2026). Covers locating the ingestion root, pre-flight venue/volume
  validation (venue IDs, joint venues, ordinal/year venue names, volume-name
  consistency), running the script with the right flags, committing per volume,
  and recovering from common errors. DO NOT USE for editing existing volumes,
  author/name corrections, or website builds.
---

# Ingesting Anthology proceedings

Templatized workflow for ingesting one or more proceedings (ACLPUB or aclpub2)
into the Anthology with `bin/ingest.py`, one volume at a time, committing each.
Works for **main/standalone events** and **colocated workshops** — the pre-flight
and venue rules are identical; only the run flags and event handling differ
(§3).

Fill in the template variables:

- `{{REPO}}` — the acl-anthology checkout (e.g. `/Users/you/code/acl-anthology`)
- `{{WS}}` — directory holding the proceedings tarballs/clones (e.g. `.../ws`)
- `{{PARENT_EVENT}}` — *workshops only*: parent event id to colocate under
  (e.g. `acl-2026`). Omit for a main/standalone event.
- `{{PY}}` — the project interpreter, usually `{{REPO}}/.venv/bin/python`
  (run `bin/ingest.py` with this; `fixedcase` is a local module under `bin/`)

## 0. Golden rules

- Only use the **public** `acl_anthology` API; never parse the XML by hand.
- **Never `git add`/commit unless the human asked.** (This task explicitly does.)
  When committing, stage **only `data/`** — a failed ingest can leave a stray
  `data/yaml/venues/*.yaml` that `git add -A`/`git add data` will otherwise sweep
  into the next commit. Verify `git status` after failures.
- Ingest **one volume per invocation** so each can be committed/reverted alone.
  `bin/ingest.py` calls `save_all()` only at the very end, so a failed run saves
  nothing — but PDFs may already be copied to `~/anthology-files` (harmless).

## 1. Find each ingestion root

The root is the directory passed to `bin/ingest.py`. Detection (`detect_ingestion_format`):
- **aclpub** = `meta` file + `cdrom/` dir
- **aclpub2** = (`conference_details.yml` or `inputs/conference_details.yml`)
  **and** (`papers.yml` or `inputs/papers.yml`)

The most reliable signal for an aclpub2 root is the `watermarked_pdfs/` directory.
Locate it and confirm `inputs/` sits beside it:

```bash
for d in {{WS}}/ws_*/; do
  find "$d" -type d -name watermarked_pdfs | while read wm; do
    root="${wm%/watermarked_pdfs}"
    echo "$d -> ROOT=$root  conf=$([ -e "$root/inputs/conference_details.yml" ] && echo y) papers=$([ -e "$root/inputs/papers.yml" ] && echo y)"
  done
done
```

Ignore `build/` matches (build artifacts). If `watermarked_pdfs` is **missing or
misnamed** (e.g. `watermarked_pdf`, or under `outputs/`), fix with a symlink in
the tarball (non-destructive), so the script finds `ROOT/watermarked_pdfs/` and
`ROOT/watermarked_pdfs/0.pdf` (frontmatter):

```bash
ln -sfn watermarked_pdf            {{WS}}/ws_x/watermarked_pdfs      # misnamed
ln -sfn outputs/watermarked_pdfs   {{WS}}/ws_y/watermarked_pdfs      # wrong dir
ln -sfn outputs/proceedings.pdf    {{WS}}/ws_y/proceedings.pdf       # book pdf
```

If the dir exists but **individual** PDFs are missing (often organizer-added
"Overview"/shared-task papers the watermarking step skipped), the watermarked
file simply was never produced. The un-watermarked source usually still exists
elsewhere in the tarball (e.g. `<repo>/.../papers/<id>.pdf`); copy it into
`ROOT/watermarked_pdfs/<id>.pdf` so the paper can be ingested:

```bash
# which paper ids in papers.yml have no watermarked PDF?
comm -23 <(grep -oE '^  id: [0-9]+' inputs/papers.yml | grep -oE '[0-9]+' | sort -nu) \
         <(ls watermarked_pdfs/*.pdf | xargs -n1 basename | sed 's/.pdf//' | sort -nu)
cp <repo>/.../papers/77.pdf ROOT/watermarked_pdfs/77.pdf   # supply the missing one
```

## 2. PRE-FLIGHT validation (do this BEFORE ingesting — organizers get these wrong)

Read each `conference_details.yml` and check `anthology_venue_id`, `volume_name`,
and `book_title`. Cross-reference `data/yaml/venues/*.yaml`.

### 2a. Venue id must be the workshop's OWN venue — not the parent conference
A common error is `anthology_venue_id: ACL` (the parent). That would ingest the
workshop into the `YYYY.acl` collection and **clobber** sibling workshops sharing
a volume name. Replace it with the workshop's real venue slug.

### 2b. Don't invent a new venue for an existing or joint venue
The venue slug = `slugify(anthology_venue_id.replace("-",""))` and **must match
`^[a-z][a-z0-9]+$` — letters and digits ONLY, no hyphens/`+`/spaces** (the
human-readable `acronym` may contain more). If a same-named venue already exists
under a **different** slug, the id is wrong — use the existing slug. Examples:
- `NLP+CSS` → slugifies to `nlp-css` (has a hyphen → invalid), and the venue is
  **`nlpcss`** → set id to `nlpcss`.
- `LT-EDI` → `ltedi` (hyphen stripped) — fine.
- A **joint** workshop (e.g. *CODI-CRAC*) must NOT create a merged `codicrac`
  venue. Ingest under the **primary** venue (`codi`) and add the secondary as an
  extra `<venue>` tag (`crac`). A volume may carry multiple `<venue>` tags
  (e.g. `codi` + `crac` + `ws`). Delete any merged venue file that leaked in.

### 2b-bis. Findings
The Findings volume (usually already ingested with the main conference) must use
`findings` as the **venue** and one of `acl`/`eacl`/`naacl` as the **volume name**
(e.g. `2026.findings-acl`, `2026.findings-eacl`). Verify this if present.

### 2c. New-venue names: strip ordinals, years, and conference prefixes
Venue `name:` in `data/yaml/venues/<slug>.yaml` must be the **timeless** name.
Remove all of these (organizers routinely add them):
- **ordinals**: "The 9th ...", "First/Second ..."
- **years** (2- or 4-digit): "... 2026", "... '26"
- **conference prefixes**: "ACL 2026 Workshop on ..."
- a trailing **acronym in parens**: "... (CDL)" / "... (EvalEval)"
- the literal venue name **`acl`** (or any parent-conference name) is never a
  valid workshop venue name

Examples:
- `The 1st Workshop on Computational Developmental Linguistics (CDL)` →
  `Workshop on Computational Developmental Linguistics`
- `ACL 2026 Workshop on Evaluating Evaluations (EvalEval)` →
  `Workshop on Evaluating Evaluations`
- `Proceedings of the 1st Workshop on X (X 2026)` → `Workshop on X`

### 2d. "Nth workshop" new venue → search before creating
If a *new* venue looks like "the 9th workshop on X", search the Anthology first:
- **(a) wrong venue id**: an existing venue already covers X under another slug →
  correct `anthology_venue_id` to that slug (don't create a new venue).
- **(b) prior instances under old-style IDs** (e.g. `W19-xxxx`) that were never
  `<venue>`-tagged → tag those old volumes with the venue, **and** still remove
  the ordinal from the new venue name.
Only if neither holds is it genuinely new (then just strip the ordinal, 2c).

```bash
# search for an existing venue / prior instances of "Event Extraction"
grep -rilE "event extraction" data/yaml/venues/
grep -rlE "Event Extraction" data/xml/ | tail
```

### 2e. Volume-name consistency
`1` or `main` is fine for a **single** volume. If a venue has **multiple**
volumes this year (e.g. a workshop + its shared task, often two repos sharing one
venue), they must be **consistently** named: either both numbers (`1`, `2`) or
both names — never a number mixed with a name. Also `volume_name` must match
`^[a-z0-9]+$` (lowercase): `Workshop` is invalid → use `1`/`main`/etc.

### 2f. Copyright forms must NOT become `<attachment>` tags
Organizers sometimes attach the signed copyright-transfer form as a paper
attachment. These must never be published as an `<attachment>`. `bin/ingest.py`
**already skips** any attachment whose `type` contains the **lowercase**
substring `copyright` (`if "copyright" in attachment["type"]`). The gap: that test
is **case-sensitive and type-based**, so a form typed `Copyright`/`CTA`/`License`,
or mislabeled (e.g. `Supplementary Material`), slips through. Pre-flight, scan the
attachment types/filenames and normalize anything that is really a copyright form:

```bash
grep -niE "copyright|transfer|cta\b|license" inputs/papers.yml
```

For each true copyright form, either drop the attachment entry from `papers.yml`
or set its `type:` to lowercase `copyright` so the built-in filter removes it.
Then confirm post-ingest (§4).

## 3. Ingest + commit, one at a time

Pick the mode based on what you're ingesting:

### 3a. Main / standalone event (e.g. the conference itself)
Do **not** pass `-w` or `--parent-event`.

```bash
cd {{REPO}}
{{PY}} bin/ingest.py "<ROOT>" \
  --event-title "64th Annual Meeting of the Association for Computational Linguistics" \
  --event-location "San Diego, California, United States" \
  --event-dates "July 2–7, 2026" \
  --event-website "https://2026.aclweb.org" \
  --event-handbook "/path/to/acl-2026-handbook.pdf"
git add data && git commit -m "Ingested <name>"     # only on success
```

The event options create or update the collection's **`<event>` block**, which
populates the event page and gives colocated workshops something to attach to.
`--event-handbook` copies the supplied PDF to
`~/anthology-files/handbooks/<venue>/<collection-id>.handbook.pdf` by default
and adds a handbook link; override the root with `--event-files-dir`. Colocated
workshops later append `<colocated>` entries without replacing the event
metadata.

### 3b. Colocated workshop
Pass `-w` (adds the `ws` venue tag) and `--parent-event` (colocates under the
parent's `<event>`).

```bash
cd {{REPO}}
{{PY}} bin/ingest.py "<ROOT>" -w --parent-event {{PARENT_EVENT}}
git add data && git commit -m "Ingested ws_<name>"  # only on success
```

`--parent-event` colocates the volume: the parent collection XML
(`data/xml/YYYY.<parent>.xml`) gains/extends an
`<event id="{{PARENT_EVENT}}"><colocated><volume-id>…</volume-id>` block. (If the
parent event isn't yet explicit, the script promotes it so the block is written.)

### Both modes
Stage **only `data/`**. A driver that ingests a list and commits each on success,
logging failures without committing (and `git clean -fdq data` to drop a stray
venue file from a failed run), is reproducible — but keep the pre-flight fixes
(§2) ahead of it.

## 4. Post-ingest fixes (MANDATORY — do not skip, and ACT, don't just inspect)

- **Joint venue tag**: add the secondary `<venue>` to the ingested volume's
  `<meta>` (e.g. add `crac` to the `2026.codi` volume) and delete the stray
  merged venue file. Set it via the public API
  (`volume.venue_ids = ("codi", "crac", "ws"); anthology.save_all()`) so order
  and validation are correct.
- **New venue name — trim EVERY new venue.** Each newly-created
  `data/yaml/venues/<slug>.yaml` must have its `name` stripped of: ordinals
  (`The 1st`, `The First`, `9th`), years/host prefixes (`ACL 2026`), and trailing
  acronym suffixes (`(EvalEval)`). e.g.
  `The First Workshop on X (X)` → `Workshop on X`. This is a per-batch loop, not
  an optional note — enumerate the new venue files and fix each one:

  ```bash
  base=$(git merge-base HEAD master)
  git diff --name-status "$base" HEAD -- data/yaml/venues/ | awk '/^A/{print $2}'
  # then edit each; finally CONFIRM none remain:
  grep -rnE "name:.*(The [0-9]|[0-9](st|nd|rd|th) |The (First|Second|Third)|ACL [0-9]{4}|\([A-Za-z0-9]+\) *$)" \
    $(git diff --name-status "$base" HEAD -- data/yaml/venues/ | awk '/^A/{print $2}')
  ```
  The grep must return **nothing** before you finish. (Only touch venues *this
  batch added* — leave pre-existing venues alone.)
- **No copyright attachments** (§2f): confirm no copyright/CTA form leaked into an
  `<attachment>` tag. The built-in filter only catches a lowercase `copyright`
  *type*, so verify and delete any that slipped through:

  ```bash
  grep -niE "<attachment[^>]*>.*(copyright|cta|transfer|license)" data/xml/YYYY.<venue>.xml
  ```
- Re-run the relevant per-volume validation / `make check` before finishing.

## 5. Common errors → fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid volume key 'Workshop'` | `volume_name` not `^[a-z0-9]+$` | lowercase it (`1`/`main`) |
| `'bool' object has no attribute …` in `add_parent_event` | walrus precedence bug | `(volume := get_volume(...)) is None` |
| parent colocation not saved | implicit event not serialized | promote to explicit event on its collection |
| `could not find paper ID … watermarked_pdfs` (whole dir) | PDF dir misnamed/misplaced | symlink `watermarked_pdfs` (step 1) |
| `could not find paper ID N` for one late/overview paper (others present) | that single watermarked PDF was never generated | copy the source `<repo>/.../papers/N.pdf` → `ROOT/watermarked_pdfs/N.pdf` (step 1) |
| new merged venue (`codicrac`) | joint venue ingested as one venue | primary venue + extra `<venue>` tag (2b) |
| sibling workshop overwritten | two repos, same venue+volume name | distinct, consistent volume names (2e) |
| `'bibkey' must match regex … ('-etal-2026-…' )` on a LATER ingest | an already-committed volume has a paper whose first author has an **empty/placeholder surname** (e.g. `last_name: .`, or a mononym) → bibkey starts with `-`; that volume now fails to load, blocking every subsequent ingest | fix the author in that volume's `papers.yml` — for a mononym put the single name in `last_name` (`<first/><last>Name</last>`), not a `.` placeholder — and **re-ingest that volume**, then resume the rest |

## 6. Wrap-up

- Cross-check against `.github/ingestion-review-checklist.md`.
- Report per-volume status (DONE / FAIL+reason) and every venue/volume/name
  decision you made, so a human can review.
