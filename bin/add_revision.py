#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Matt Post <post@cs.jhu.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This script processes paper revisions submitted to the ACL Anthology
using our "03-revision-or-errata.yml" template.
It can either process a GitHub issue directly (using the --issue flag)
or it can take the pieces (anthology_id, path to PDF, explanation) manually. When provided with a Github issue, it will parse out the
information, and prompt the user to summarize the explanation, since
these are often long or unwieldy.

The PDFs are then shuffled as follows:
- When a first revision is created, the original paper is archived to {anthology_id}v1.pdf
- The new revision is copied to {anthology_id}v2.pdf
- The new revision also overwrites the original one at {anthology_id}.pdf.
    This causes it to be returned by the anthology when the base paper format is queried.

A variant of this is applied for subsequent revisions (v3, v4, etc.).
For errata, we create a file {anthology_id}e1.pdf, {anthology_id}e2.pdf, etc., but do not overwrite the original paper, since errata are separate documents.

Usage:

    # Process information from the template and create a PR
    add_revision.py [-e] [-i GITHUB_ISSUE]

    # This variant lets you process pieces manually
    add_revision [-e] paper_id URL_OR_PATH.pdf "Short explanation".

`-e` denotes erratum instead of revision.

List of revisions: https://github.com/acl-org/acl-anthology/issues?q=is%3Aissue%20state%3Aopen%20label%3Arevision
"""

from __future__ import annotations

import argparse
import filetype
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from git.repo.base import Repo
from github import Github, GithubException

from acl_anthology import Anthology
from acl_anthology.collections.paper import PaperErratum, PaperRevision
from acl_anthology.files import PDFReference
from acl_anthology.utils.ids import parse_id

from anthology.utils import retrieve_url

DEFAULT_GITHUB_REPO = os.environ.get("ANTHOLOGY_GITHUB_REPO", "acl-org/acl-anthology")
GITHUB_TOKEN_ENV_VARS = ("GITHUB_TOKEN", "GH_TOKEN")
TRAILING_URL_CHARS = ').,]>"'
ANTHOLOGY_FILES_DIR = Path(
    os.environ.get("ANTHOLOGY_FILES", Path.home() / "anthology-files")
)


def _get_github_repo(repo_name):
    token = _get_github_token()
    if not token:
        print(
            "-> FATAL: set GITHUB_TOKEN or GH_TOKEN before using --issue",
            file=sys.stderr,
        )
        sys.exit(1)

    client = Github(token)
    try:
        return client.get_repo(repo_name)
    except GithubException as exc:
        print(
            f"-> FATAL: unable to access GitHub repo {repo_name}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


def _get_github_token():
    for env_var in GITHUB_TOKEN_ENV_VARS:
        token = os.environ.get(env_var)
        if token:
            return token
    return None


def _parse_issue_form_sections(body):
    sections = {}
    current_key = None
    for line in body.splitlines():
        if line.startswith("### "):
            current_key = line[4:].strip().lower()
            sections[current_key] = []
        elif current_key is not None:
            sections[current_key].append(line.rstrip())
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _extract_first_url(value):
    if not value:
        return None
    match = re.search(r"(https?://\S+)", value)
    if match:
        return match.group(1).rstrip(TRAILING_URL_CHARS)
    return None


def fetch_issue_revision_metadata(
    issue_number, repo_name=DEFAULT_GITHUB_REPO, github_repo=None
):
    """Fetch GitHub issue metadata and extract relevant revision fields."""
    repo = github_repo or _get_github_repo(repo_name)
    try:
        issue = repo.get_issue(number=issue_number)
    except GithubException as exc:
        print(
            f"-> FATAL: unable to fetch issue #{issue_number} from {repo_name}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    body = issue.body or ""
    sections = _parse_issue_form_sections(body)
    description = sections.get("brief description of changes", "").strip()
    metadata = {
        "anthology_id": sections.get("anthology id", "").strip() or None,
        "pdf_url": _extract_first_url(sections.get("pdf of the revision or erratum", "")),
        "description": description,
        "title": issue.title or "",
        "issue_url": issue.html_url,
        "raw_body": body,
    }

    return metadata


def validate_file_type(path: Path) -> None:
    """Ensure downloaded file mime type matches its extension (e.g., PDF)."""
    detected = filetype.guess(str(path))
    if detected is None or not detected.mime.endswith(detected.extension):
        mime_type = "UNKNOWN" if detected is None else detected.mime
        print(f"-> FATAL: file {path} has MIME type {mime_type}", file=sys.stderr)
        sys.exit(1)


def resolve_pdf_dir(anthology_id: str) -> Path:
    collection_id, _, _ = parse_id(anthology_id)
    base_dir = ANTHOLOGY_FILES_DIR / "pdf"
    if collection_id[0].isdigit():
        parts = collection_id.split(".", 1)
        venue = parts[1] if len(parts) == 2 else parts[0]
        return base_dir / venue
    return base_dir / collection_id[0] / collection_id


def copy_file(src: Path, dest: Path) -> None:
    print(f"-> Copying {src} -> {dest}", file=sys.stderr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    os.chmod(dest, 0o644)


def add_revision(
    anthology: Anthology,
    anth_id: str,
    pdf_path: Path,
    explanation: str,
    change_type: str = "revision",
    date: str | None = None,
) -> Path | None:
    if date is None:
        now = datetime.now()
        date = f"{now.year}-{now.month:02d}-{now.day:02d}"

    paper = anthology.get_paper(anth_id)
    if paper is None:
        print(f"-> FATAL: paper ID {anth_id} not found in the Anthology", file=sys.stderr)
        sys.exit(1)

    pdf_dir = resolve_pdf_dir(paper.full_id)
    canonical_pdf = pdf_dir / f"{paper.full_id}.pdf"
    change_letter = "e" if change_type == "erratum" else "v"
    history = paper.errata if change_type == "erratum" else paper.revisions
    needs_initial_revision = change_type == "revision" and not history

    if change_type == "revision" and paper.pdf is None:
        print(
            f"-> FATAL: paper {paper.full_id} has no PDF reference; cannot create revision",
            file=sys.stderr,
        )
        sys.exit(1)

    pdf_dir.mkdir(parents=True, exist_ok=True)

    if needs_initial_revision:
        v1_name = f"{paper.full_id}{change_letter}1"
        v1_path = pdf_dir / f"{v1_name}.pdf"
        retrieve_url(paper.pdf.url, v1_path)
        validate_file_type(v1_path)
        paper.revisions.append(
            PaperRevision(id="1", note=None, pdf=PDFReference.from_file(v1_path))
        )

    next_id = (
        int(history[-1].id) + 1 if history else (1 if change_type == "erratum" else 2)
    )
    version_name = f"{paper.full_id}{change_letter}{next_id}"
    version_path = pdf_dir / f"{version_name}.pdf"
    copy_file(pdf_path, version_path)
    reference = PDFReference.from_file(version_path)

    if change_type == "revision":
        note = explanation.strip() if explanation else None
        paper.revisions.append(
            PaperRevision(
                id=str(next_id),
                note=note,
                pdf=reference,
                date=date,
            )
        )
        copy_file(pdf_path, canonical_pdf)
        paper.pdf = PDFReference.from_file(canonical_pdf)
    else:
        paper.errata.append(
            PaperErratum(
                id=str(next_id),
                pdf=reference,
                date=date,
            )
        )

    paper.collection.save()
    print(
        f"-> Added {change_type} #{next_id} ({version_name}) to {paper.full_id}",
        file=sys.stderr,
    )
    return paper.collection.path


def main(args):
    change_type = "erratum" if args.erratum else "revision"
    repo_name = args.repo or DEFAULT_GITHUB_REPO
    anthology = Anthology.from_within_repo()

    github_repo = None
    if args.issue:
        github_repo = _get_github_repo(repo_name)
        issue_metadata = fetch_issue_revision_metadata(args.issue, repo_name, github_repo)
        anthology_id = issue_metadata.get("anthology_id")
        pdf_url = issue_metadata.get("pdf_url")

        print(
            f"-> Issue #{args.issue} description from {repo_name}:\n"
            f"   Anthology ID: {anthology_id or 'not provided'}\n"
            f"   PDF URL: {pdf_url or 'not provided'}\n"
        )

        description = issue_metadata.get("description") or ""
        if description:
            print("\nReported brief description:\n" + description + "\n")
        else:
            print("\nNo brief description found in the issue body.\n")

        user_summary = input(
            "Enter the summary to store in the Anthology (press Enter to reuse the description): "
        ).strip()
        explanation_text = user_summary or description
    else:
        if args.anthology_id is None or args.path is None or args.explanation is None:
            print(
                "-> FATAL: anthology_id, path, and explanation are required if not using --issue",
                file=sys.stderr,
            )
            sys.exit(1)
        anthology_id = args.anthology_id
        pdf_url = args.path
        explanation_text = args.explanation

    if not anthology_id:
        print("-> FATAL: Anthology ID not provided", file=sys.stderr)
        sys.exit(1)
    if not pdf_url:
        print("-> FATAL: PDF path or URL not provided", file=sys.stderr)
        sys.exit(1)

    pdf_path = None
    temp_path = None
    if pdf_url.lower().startswith("http"):
        _, temp_path_str = tempfile.mkstemp(suffix=".pdf")
        temp_path = pdf_path = Path(temp_path_str)
        retrieve_url(pdf_url, pdf_path)
    else:
        pdf_path = Path(pdf_url)
        if not pdf_path.is_file():
            print(f"-> FATAL: file {pdf_path} does not exist", file=sys.stderr)
            sys.exit(1)

    pdf_path = Path(pdf_path)
    validate_file_type(pdf_path)

    # build a list of the checksums of all revisions for the paper
    paper = anthology.get_paper(anthology_id)
    if paper is None:
        print(
            f"-> FATAL: paper ID {anthology_id} not found in the Anthology",
            file=sys.stderr,
        )
        sys.exit(1)

    existing_checksums = [rev.pdf.checksum for rev in paper.revisions + paper.errata]
    # make sure the new PDF is not a dupe
    if PDFReference.from_file(pdf_path).checksum in existing_checksums:
        print(
            f"-> FATAL: the provided PDF is identical to an existing revision/erratum for {paper.full_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    collection_path = add_revision(
        anthology,
        anthology_id,
        pdf_path,
        explanation_text,
        change_type=change_type,
        date=args.date,
    )

    # clean up
    if temp_path is not None and temp_path.exists():
        temp_path.unlink()

    """
    If a Github issue was passed as an argument, do the following.
    First ensure, that we are on a branch named "corrections-YYYY-MM".
    Then, create a commit with the message "Add revision for {anthology_id} (closes {issue})"
    Use the Github module to create the brnach (if not existing), change to it,
    and create the commit.
    """
    if args.issue and collection_path is not None:
        repo = Repo(".", search_parent_directories=True)
        branch_name = args.branch
        existing_heads = [h.name for h in repo.heads]
        base_branch = "master"
        if branch_name not in existing_heads:
            repo.create_head(branch_name, getattr(repo.heads, base_branch).commit)
        repo.git.checkout(branch_name)
        repo.git.add(str(collection_path))
        if repo.is_dirty(index=True, working_tree=True, untracked_files=True):
            repo.index.commit(
                f"Add {change_type} for {anthology_id} (closes #{args.issue})"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--anthology_id", help="The Anthology paper ID to revise (e.g., P18-1001)"
    )
    parser.add_argument(
        "--path", type=str, help="Path to the revised paper ID (can be URL)"
    )
    parser.add_argument("--explanation", help="Brief description of the changes.")
    parser.add_argument(
        "--issue",
        "-i",
        type=int,
        default=None,
        help="GitHub issue number associated with this revision.",
    )
    parser.add_argument(
        "--erratum",
        "-e",
        action="store_true",
        help="This is an erratum instead of a revision.",
    )
    now = datetime.now()
    today = f"{now.year}-{now.month:02d}-{now.day:02d}"
    parser.add_argument(
        "--date",
        "-d",
        type=str,
        default=today,
        help="The date of the revision (ISO 8601 format)",
    )
    parser.add_argument("--branch", "-b", default=None, help="Branch name.")
    parser.add_argument(
        "--repo",
        "-r",
        default=DEFAULT_GITHUB_REPO,
        help="GitHub repository (owner/name) to query for issues.",
    )

    args = parser.parse_args()

    if args.branch is None:
        args.branch = f"corrections-{args.date[:7]}"

    main(args)
