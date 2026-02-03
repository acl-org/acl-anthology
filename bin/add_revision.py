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
This script process paper revisions submitted to the ACL Anthology
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
"""

import argparse
import filetype
import os
import re
import shutil
import sys
import tempfile

from git.repo.base import Repo
from github import Github, GithubException

from anthology.utils import (
    deconstruct_anthology_id,
    make_simple_element,
    indent,
    compute_hash_from_file,
    infer_url,
    retrieve_url,
    get_pdf_dir,
    get_xml_file,
)

import lxml.etree as ET

from datetime import datetime

DEFAULT_GITHUB_REPO = os.environ.get("ANTHOLOGY_GITHUB_REPO", "acl-org/acl-anthology")
GITHUB_TOKEN_ENV_VARS = ("GITHUB_TOKEN", "GH_TOKEN")
TRAILING_URL_CHARS = ').,]>"'


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


def validate_file_type(path):
    """Ensure downloaded file mime type matches its extension (e.g., PDF)"""
    detected = filetype.guess(path)
    if detected is None or not detected.mime.endswith(detected.extension):
        mime_type = "UNKNOWN" if detected is None else detected.mime
        print(
            f"FATAL: file {path} has MIME type {mime_type}",
            file=sys.stderr,
        )
        sys.exit(1)


def add_revision(
    anth_id, pdf_path, explanation, change_type="revision", dry_run=True, date=None
):
    """
    Takes an Anthology ID. It then adds a revision to the Anthology XML,
    updating and writing the XML file, and copies the PDFs into place.
    For PDFs, the revised PDF is saved to {anth_id}.pdf and {anth_id}v{version}.pdf.
    For the first revision, we first copy {anth_id}.pdf to {anth_id}v1.pdf.
    """
    if date is None:
        now = datetime.now()
        date = f"{now.year}-{now.month:02d}-{now.day:02d}"

    def maybe_copy(file_from, file_to):
        if not dry_run:
            print("-> Copying from {} -> {}".format(file_from, file_to), file=sys.stderr)
            shutil.copy(file_from, file_to)
            os.chmod(file_to, 0o644)
        else:
            print(
                "-> DRY RUN: Copying from {} -> {}".format(file_from, file_to),
                file=sys.stderr,
            )

    # The new version
    revno = None

    change_letter = "e" if change_type == "erratum" else "v"

    checksum = compute_hash_from_file(pdf_path)

    # Files for old-style IDs are stored under anthology-files/pdf/P/P19/*
    # Files for new-style IDs are stored under anthology-files/pdf/2020.acl/*
    output_dir = get_pdf_dir(anth_id)

    # Make sure directory exists
    if not os.path.exists(output_dir):
        print(f"-> Creating directory {output_dir}", file=sys.stderr)
        os.makedirs(output_dir)

    canonical_path = os.path.join(output_dir, f"{anth_id}.pdf")

    # Update XML
    xml_file = get_xml_file(anth_id)
    collection_id, volume_id, paper_id = deconstruct_anthology_id(anth_id)
    tree = ET.parse(xml_file)
    if paper_id == "0":
        paper = tree.getroot().find(f"./volume[@id='{volume_id}']/frontmatter")
    else:
        paper = tree.getroot().find(
            f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']"
        )
    if paper is not None:
        revisions = paper.findall(change_type)
        revno = 1 if change_type == "erratum" else 2
        for revision in revisions:
            revno = int(revision.attrib["id"]) + 1

        if not dry_run:
            # Update the URL hash on the <url> tag
            if change_type != "erratum":
                url = paper.find("./url")
                if url is not None:
                    url.attrib["hash"] = checksum

            if change_type == "revision" and revno == 2:
                if paper.find("./url") is not None:
                    current_version_url = infer_url(paper.find("./url").text) + ".pdf"

                # Download original file
                # There are no versioned files the first time around, so create the first one
                # (essentially backing up the original version)
                revised_file_v1_path = os.path.join(
                    output_dir, f"{anth_id}{change_letter}1.pdf"
                )

                retrieve_url(current_version_url, revised_file_v1_path)
                validate_file_type(revised_file_v1_path)

                old_checksum = compute_hash_from_file(revised_file_v1_path)

                # First revision requires making the original version explicit
                revision = make_simple_element(
                    change_type,
                    None,
                    attrib={
                        "id": "1",
                        "href": f"{anth_id}{change_letter}1",
                        "hash": old_checksum,
                    },
                    parent=paper,
                )

            revision = make_simple_element(
                change_type,
                explanation,
                attrib={
                    "id": str(revno),
                    "href": f"{anth_id}{change_letter}{revno}",
                    "hash": checksum,
                    "date": date,
                },
                parent=paper,
            )
            indent(tree.getroot())

            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            print(
                f'-> Added {change_type} node "{revision.text}" to XML', file=sys.stderr
            )

    else:
        print(
            f"-> FATAL: paper ID {anth_id} not found in the Anthology",
            file=sys.stderr,
        )
        sys.exit(1)

    revised_file_versioned_path = os.path.join(
        output_dir, f"{anth_id}{change_letter}{revno}.pdf"
    )

    # Copy the file to the versioned path
    maybe_copy(pdf_path, revised_file_versioned_path)

    # Copy it over the canonical path
    if change_type == "revision":
        maybe_copy(pdf_path, canonical_path)


def main(args):
    change_type = "erratum" if args.erratum else "revision"

    repo_name = args.repo or DEFAULT_GITHUB_REPO

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
        # make sure anthology_id, explanation, and path are provided
        if args.anthology_id is None or args.path is None or args.explanation is None:
            print(
                "-> FATAL: anthology_id, path, and explanation are required if not using --issue",
                file=sys.stderr,
            )
            sys.exit(1)

        anthology_id = args.anthology_id
        pdf_url = args.path
        explanation_text = args.explanation

    # TODO: make sure path exists, or download URL to temp file
    if pdf_url.startswith("http"):
        _, input_file_path = tempfile.mkstemp()
        retrieve_url(pdf_url, input_file_path)
    else:
        input_file_path = pdf_url

    validate_file_type(input_file_path)

    add_revision(
        anthology_id,
        input_file_path,
        explanation_text,
        change_type=change_type,
        dry_run=args.dry_run,
    )

    if pdf_url.startswith("http"):
        os.remove(input_file_path)

    """
    If a Github issue was passed as an argument, do the following.
    First ensure, that we are on a branch named "corrections-YYYY-MM".
    Then, create a commit with the message "Add revision for {anthology_id} (closes {issue})"
    Use the Github module to create the brnach (if not existing), change to it,
    and create the commit.
    """
    if args.issue:
        repo = Repo(".", search_parent_directories=True)
        # Create the branch if it doesn't exist, based off main (or master)
        branch_name = args.branch
        existing_heads = [h.name for h in repo.heads]
        base_branch = "master"
        if branch_name not in existing_heads:
            repo.create_head(branch_name, getattr(repo.heads, base_branch).commit)
        # Change to the new branch
        repo.git.checkout(branch_name)
        # Stage changed files
        repo.git.add(get_xml_file(anthology_id))
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
    parser.add_argument(
        "--dry-run", "-n", action="store_true", default=False, help="Just a dry run."
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
