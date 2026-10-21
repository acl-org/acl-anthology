---
name: revisions
description: "Process ACL Anthology paper revision and erratum requests from GitHub issues using bin/add_revision.py, one issue at a time. Use for handling the open revision queue, writing concise neutral revision descriptions, validating PDFs and metadata, committing each revision, and marking completed requests pending. Not for ingesting new proceedings or general author/metadata corrections."
---

# Processing paper revisions

Use [add_revision.py](../../../bin/add_revision.py) for revisions and errata.
Process requests **one at a time**, normally oldest first. Pause for the user
when a request is ambiguous or a substantive problem needs a decision.

## 1. Inspect the queue and working state

```bash
git --no-pager status --short
gh issue list --repo acl-org/acl-anthology --state open --label revision \
  --search='-label:pending sort:created-asc' --limit 100 \
  --json number,title,url,createdAt
uv run bin/add_revision.py --help
uv run pre-commit install
```

- Skip issues already labeled `pending`: they have been processed and await
  merging. Do not create another revision for them.
- Paginate if the queue exceeds the retrieval limit.
- Preserve unrelated working-tree and staged changes. Do not amend existing
  commits or include other work in revision commits.
- Read the current script before relying on its behavior. Its CLI uses named
  arguments, including `--anthology_id`; do not assume positional arguments
  from older usage examples work.

## 2. Inspect one request

```bash
gh issue view ISSUE --repo acl-org/acl-anthology \
  --json number,title,body,comments
```

Read the issue body, comments, and relevant linked reports. Identify:

- The clean Anthology ID, stripping any Markdown link or Anthology URL wrapper.
- Whether the attachment is a revision or an erratum.
- The actual PDF attachment or download URL, including updates in comments.
- What changed, and whether the authors report any effect on conclusions.

Use the public `acl_anthology` API to inspect authoritative metadata, never an
ad hoc XML/JSON parser:

```python
from acl_anthology import Anthology

anthology = Anthology.from_within_repo()
paper = anthology.get_paper("PAPER_ID")
if paper is None:
    raise ValueError("Paper not found")
print(paper.title)
print(paper.authors)
print(paper.pdf)
print(paper.revisions)
print(paper.errata)
print(paper.collection.path)
```

Record the original PDF checksum and existing history before processing.
Use `paper.collection.path` for the commit: a paper such as
`2026.findings-acl.1220` belongs to `data/xml/2026.findings.xml`, **not**
`data/xml/2026.findings-acl.xml`.

Download the supplied PDF into session scratch storage. Inspect it with
`pypdf.PdfReader`: check the title, authors, page count, and relevant corrected
passages. If the description is unclear, compare extracted text against the
existing PDF obtained through `paper.pdf.download(...)`.

### When to ask

- A request says **erratum**, but supplies a complete replacement paper.
  Revisions replace the paper; errata are separate documents and do not replace
  the canonical PDF. Ask before overriding the submitted type.
- Results or conclusions change substantially, results are withdrawn, or
  published results cannot be reproduced. Summarize the concern and propose a
  neutral description for approval; do not silently reject or accept it.
- The ID, attachment, requested change, or author identity is inconsistent,
  the PDF is inaccessible or invalid, or it duplicates existing history.
- Concurrent changes affect the same paper or collection.

Resolve ordinary technical problems yourself where possible. Do not ask the
user to approve every routine request or every description.

## 3. Write the revision description

**This is an editorial summary, not a copy of the submission.**

- Write **one or two concise sentences**, neutrally in the third person or
  impersonal style. Existing notes such as "Added a funding acknowledgment."
  are appropriate.
- State what changed. Remove first-person wording, apologies, justifications,
  long quotations, exhaustive value lists, and unnecessary implementation detail.
- Retain significant consequences, especially withdrawn results or changed
  conclusions. Say results or conclusions are unchanged only when supported
  by the request.
- Include section/table identifiers only when useful for locating the correction.
- Do not rewrite unrelated older revision notes.

Examples:

| Submitted information | Suitable description |
| --- | --- |
| A paragraph explaining an omitted funding statement | Added a funding acknowledgment. |
| A long list of corrected titles, authors, and arXiv IDs | Corrected bibliographic details in six references. |
| A drafting comment accidentally appeared in the published paper | Removed an inadvertently published drafting comment. |
| Incorrect baseline values and corresponding discussion; conclusions unchanged | Corrected baseline results and updated the related discussion. The conclusions are unchanged. |
| Unreproducible results replaced and translation results withdrawn | Replaced unreproducible evaluation results with held-out evaluations and withdrew the machine translation results. Updated the experimental details and conclusions accordingly. |

## 4. Run the script and commit separately

The manual-input mode allows a carefully edited description, an explicitly
confirmed change type, and a normal commit with hooks and attribution:

```bash
uv run bin/add_revision.py \
  --anthology_id PAPER_ID \
  --path /path/to/downloaded.pdf \
  --explanation "Concise neutral description." \
  --date YYYY-MM-DD
```

Use the processing date. Add `--erratum` for an actual erratum.
Do not use `--replace` merely to avoid creating revision history.

Important script behavior:

- `--issue ISSUE` prompts for the summary and automatically commits the
  collection using GitPython. Do not rely on that commit to run Git hooks or
  supply a co-author trailer; prefer manual-input mode and an explicit commit.
- Issue mode honors an issue's `Erratum` selection. For a user-approved
  erratum-to-revision correction, use manual-input mode.
- A first revision archives the original as `PAPER_IDv1.pdf`, creates
  `PAPER_IDv2.pdf`, and updates `PAPER_ID.pdf`. Subsequent revisions increment
  the version. Revision PDFs receive a first-page revision watermark.
- Errata use `PAPER_IDeN.pdf` without replacing the canonical paper.
  The current script does not store an erratum description in metadata;
  retain its concise explanation in the commit message.
- Frontmatter and whole-volume PDFs are automatically replaced in place,
  rather than given revision history. Treat these as a distinct workflow.
- Files go under `$ANTHOLOGY_FILES/pdf/`, defaulting to
  `~/anthology-files/pdf/`. Modern collection files are grouped by venue,
  e.g. `pdf/findings/`, not `pdf/findings-acl/`.

After successful validation, commit **only** the affected collection:

```bash
git add -- data/xml/COLLECTION.xml
git commit --only \
  -m "Add revision for PAPER_ID (closes #ISSUE)" \
  -m "Concise neutral description." \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>" \
  -- data/xml/COLLECTION.xml
gh issue edit ISSUE --repo acl-org/acl-anthology --add-label pending
```

Adjust the commit subject for an erratum. Label the issue `pending` **only after**
the request is processed, verified, and committed. Leave it open; the closing
reference takes effect when the commit reaches the default branch.

## 5. Validate before moving to the next issue

Reload the paper through the library to verify the saved state:

- Only the intended history entries were added: the original archive plus the
  new version for a first revision, or one entry otherwise. Check the version,
  processing date, checksum, and, for revisions, concise note.
- `PDFReference.from_file(path).checksum` matches metadata for every file
  created by this operation, including the original archive for a first revision.
- For an ordinary locally hosted revision, the canonical PDF and latest version
  are byte-identical and match the paper's updated checksum.
- The page count and extracted text match the supplied PDF, apart from the
  script's added watermark. Confirm the watermark's paper ID, version, and date.
- Existing history and unrelated metadata remain unchanged. Do not require
  older revision PDFs to exist in local staging.
- For errata, verify that the canonical PDF and revision history are unchanged.
  For externally hosted papers, preserve the external top-level URL as the
  script intends rather than imposing the local-PDF checksum rule.
- Ensure commit-time hooks, especially XML schema validation, pass.

If the script succeeded but a later validation or commit command failed,
inspect the saved state and resume from that point. Do not rerun the script
blindly and create an extra version.

After the queue, run `just check` as documented in the repository instructions.
If it fails only on unrelated pre-existing changes, report that accurately;
do not "fix" the user's unrelated work. Restore incidental tooling changes
introduced by this workflow, such as package-index-only lockfile rewrites.
`uv run --frozen` can avoid rewriting the lockfile during later checks.

Confirm every processed issue has `pending` and no unprocessed requests remain.

## 6. Sync and finish

PDF syncing and Git publication are separate from local processing:

- Do not silently push, open a PR, or upload files. Follow the user's requested
  publication scope and the repository's public-post attribution conventions.
- `make sync` uploads staging files and uses `--remove-source-files`; it may
  include unrelated staged assets. Confirm scope before using it.
- If verified local PDFs disappear, check whether a concurrent sync uploaded
  them before recreating files or rerunning the revision script. Download the
  versioned and canonical PDFs through their library references and verify
  checksums against saved metadata.
- Remove only scratch files created for this workflow. Preserve staged
  production PDFs until they are uploaded.
- Report the number processed, any approved exceptions or skipped requests,
  validation results, and whether commits and PDFs remain local or were published.
