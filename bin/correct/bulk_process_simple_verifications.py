#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Nathan Schneider (@nschneid)
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
Creates bulk pull request to process approved author page issues that are simple verify-all
requests (i.e., they pertain to an unverified author page where there is no corresponding
verified author to merge with, and all papers on the page should be explicitly linked to the
newly verified author).

In detail:
Queries the Github API for all issues in the acl-org/acl-anthology repository.
It then goes through them, looking for ones that
- have an issue title ending in "/unverified"
- have both "author-page" and "correction" labels,
- a description that includes an ORCID URL (if the iD contains 'X' it must be uppercase) and
  either comes from the "Verify Author Page" form with no papers listed as not the author's,
  or from the legacy form with "[x] Verification" and other request types unchecked
- are approved by at least one member of the Anthology group.
  "Additional notes" are not read by this script, so the reviewer should check them
  before approving.
It then creates a new PR on a branch labeled bulk-verifications-YYYY-MM-DD,
where it makes a single PR from changes from all matching issues.

Usage: bulk_verify_all.py [-q] [--skip-validation] [--dry-run] [--no-branch] [issue_ids...]

Options:
    -q, --quiet              Suppress output
    --skip-validation        Skip requirement of "approved" tag
    --dry-run                Dry run (do not create PRs)
    --no-branch              Stay on the current branch
    issue_ids                Specific issue IDs to process (default: all)
"""

import os
import logging as log
from datetime import datetime

from github import Github
import git
import re

from acl_anthology.anthology import Anthology
from acl_anthology.people import Name
from acl_anthology.utils.logging import setup_rich_logging


class AnthologyMetadataUpdater:
    def __init__(self, github_token):
        """Initialize with GitHub token."""
        self.github = Github(github_token)
        self.github_repo = self.github.get_repo("acl-org/acl-anthology")
        self.local_repo = git.Repo(__file__, search_parent_directories=True)
        self.stats = {
            "visited_issues": 0,
            "relevant_issues": 0,
            "approved_issues": 0,
            "unapproved_issues": 0,
            "error_issues": 0,
        }
        self.load_anthology()

    def _is_approved(self, issue):
        """Check if issue has approval from anthology team member."""
        return "approved" in [label.name for label in issue.get_labels()]

    def _parse_verification_request(self, issue_body: str) -> None | dict:
        """Parse the metadata changes from issue body.

        Expected format:

        ...

        ### Author Pages

        <author page URL>

        ### Author ORCID

        https://orcid.org/<orcid>

        ### Institution of highest (anticipated) degree

        <name of university>

        ### Type of Author Metadata Correction

        - [x] Verification: The author wishes to add an ORCID iD to their author page.
        - [ ] Split/disambiguate: The author page includes papers from two or more different people.
        - [ ] Merge profiles: A single author has multiple profiles with different spellings or variants of their name.
        - [ ] Name change: This author has permanently changed their name.

        ...

        The "Verify Author Page" form may also have a "### Preferred author name"
        section; see _preferred_name().

        The issue body must already have "\n" line endings.
        """
        m = re.search(
            r"### Author ORCID\n\nhttps://orcid.org/([0-9X-]{19})\n\n### Institution[^\n]+\n\n([^\n]+)\n",
            issue_body,
            re.MULTILINE,
        )
        if m is None:
            return None
        return {"orcid": m.group(1), "degree": m.group(2)}

    @staticmethod
    def _form_field(issue_body: str, heading: str) -> None | str:
        """Get the answer under a "### heading" in an issue form, or None if left empty."""
        m = re.search(
            rf"### {re.escape(heading)}\n\n(.*?)(?:\n\n###|\Z)", issue_body, re.DOTALL
        )
        if m is None or m.group(1).strip() in ("", "_No response_"):
            return None
        return m.group(1).strip()

    @classmethod
    def _lists_papers_not_mine(cls, issue_body: str) -> bool:
        """Check if a "Verify Author Page" issue excludes any papers from the page."""
        return any(
            cls._form_field(issue_body, heading)
            for heading in (
                "Papers on this page that are not mine",
                "Papers on this page that are mine (if only some)",
            )
        )

    @classmethod
    def _requests_merge(cls, issue_body: str) -> bool:
        """Check if a "Verify Author Page" issue names another author page to merge with."""
        return cls._form_field(issue_body, "Merge with author page") is not None

    @classmethod
    def _preferred_name(cls, issue_body: str) -> None | Name:
        """Get the name chosen in a "Verify Author Page" issue to show on the page.

        The author correction panel sends it as "Last, First", or just "Last" for a
        person with a single name.
        """
        value = cls._form_field(issue_body, "Preferred author name")
        if value is None:
            return None
        last, _, first = value.partition(", ")
        return Name(first or None, last)

    def load_anthology(self):
        log.info("Loading anthology")
        self.anthology = Anthology.from_within_repo(
            suppress_warnings=("NameSpecResolutionWarning",)
        )

    def process_verification_issues(
        self,
        issue_ids: list[int] = [],
        verbose=False,
        skip_validation=False,
        dry_run=False,
        no_branch=False,
    ):
        """Process all simple verification issues and create PR with changes."""
        # Get all open issues with required labels
        if issue_ids and len(issue_ids) < 100:
            issues = [self.github_repo.get_issue(num) for num in issue_ids]
        else:
            issues = self.github_repo.get_issues(
                state="open", labels=["author-page", "correction"]
            )

        current_branch, new_branch_name, today = self.prepare_and_switch_branch(
            no_branch=no_branch
        )

        # record which issues were successfully processed and need closing
        closed_issues = []

        for issue in issues:
            # Flag non-simple issues that are not already labeled as such
            body = issue.body.replace("\r\n", "\n").replace("\r", "\n")
            issuetype = []
            issuelabels = [label.name for label in issue.get_labels()]
            if "[x] Split/disambiguate:" in body or self._lists_papers_not_mine(body):
                issuetype.append("SPLIT")
            if "[x] Merge profiles:" in body or self._requests_merge(body):
                issuetype.append("MERGE")
            if "[x] Name change:" in body:
                issuetype.append("NAMECHANGE")
            if "move-papers" in issuelabels:
                issuetype.append("MOVE")
            if issuetype and not any(lbl.startswith("meta:") for lbl in issuelabels):
                log.warning(
                    f"#{issue.number}: No meta:* label for issue type {'+'.join(issuetype)} {issue.html_url}"
                )
            elif (
                "[ ] Verification:" in body
                and "[ ] Split/disambiguate:" in body
                and "[ ] Merge profiles:" in body
                and "[ ] Name change:" in body
            ):
                log.warning(f"#{issue.number}: No issue type (empty checkboxes)")

            # Skip verification if non-simple
            if not issue.title.lower().endswith("/unverified"):
                continue

            if "verify-author" in issuelabels:
                # "Verify Author Page" form: simple if no papers are excluded
                if issuetype:
                    continue
            else:
                # Ensure we have a legacy "Correction to Author Page" form
                # with Verification as the only action.
                if not all(
                    box in body
                    for box in (
                        "[x] Verification:",
                        "[ ] Split/disambiguate:",
                        "[ ] Merge profiles:",
                        "[ ] Name change:",
                    )
                ):
                    continue

            # Process the issue if consistent with command line args
            self.stats["visited_issues"] += 1
            try:
                if issue_ids and issue.number not in issue_ids:
                    if self.stats["relevant_issues"] == len(issue_ids):
                        # we've already visited all the specified issues
                        break
                    else:
                        continue
                opened_at = issue.created_at.strftime("%Y-%m-%d")
                if verbose:
                    log.info(
                        f"ISSUE {issue.number} ({opened_at}): {issue.title} {issue.html_url}"
                    )

                # Parse metadata changes from issue
                data = self._parse_verification_request(body)
                if data is None:
                    log.error(f"Failed to parse verification data in #{issue.number}")
                    continue

                data["author_id"] = issue.title.split()[-1]

                self.stats["relevant_issues"] += 1

                # Skip issues that are not approved by team member
                if not skip_validation and not self._is_approved(issue):
                    if verbose:
                        log.info("-> Skipping (not approved yet)")
                    self.stats["unapproved_issues"] += 1
                    continue

                self.stats["approved_issues"] += 1

                author_id = data["author_id"]

                # XML file path relative to repo root (for reading current state)
                data_repo_path = "data/"
                if verbose:
                    log.info(f"-> Applying changes to database for author {author_id}")

                try:
                    # update the database!
                    person = self.anthology.get_person(author_id)
                    if person is None:
                        raise ValueError(
                            f"Author ID not found (was the verification already applied?): {author_id}"
                        )
                    if p2 := self.anthology.people.get_by_orcid(data["orcid"]):
                        raise ValueError(
                            f"Another author with this ORCID found (should be merge request?): {p2}"
                        )
                    if preferred_name := self._preferred_name(body):
                        if not person.has_name(preferred_name):
                            raise ValueError(
                                f"Preferred name is not one of this author's names: {preferred_name.as_last_first()}"
                            )
                        person.canonical_name = preferred_name
                        if verbose:
                            log.info(
                                f"-> Preferred name {preferred_name.as_first_last()}"
                            )
                    # The request form doesn't list retracted or removed papers, but
                    # they are verified along with the rest of the page.
                    deleted = [paper for paper in person.papers() if paper.is_deleted]
                    if deleted:
                        log.warning(
                            f"#{issue.number}: {author_id} includes papers not listed in the request form: "
                            + ", ".join(
                                f"{paper.full_id} ({paper.deletion.type.value})"
                                for paper in deleted
                            )
                        )
                    person.orcid = data["orcid"]
                    person.degree = data["degree"].strip()
                    new_author_id = author_id.replace("/unverified", "")
                    if verbose:
                        log.info(f"-> New ID {new_author_id}, ORCID {person.orcid}")
                    if not new_author_id:
                        raise ValueError("Author ID must be nonempty")
                    person.make_explicit()  # can fail if another person with this ID exists
                    assert person.id == new_author_id, (
                        f"Explicit ID is {person.id}, expected {new_author_id}"
                    )
                    self.anthology.save_all()  # Note: can be slow
                except Exception as e:
                    log.error(
                        f"Failed to apply changes to #{issue.number}: {e}",
                    )
                    log.exception(e)
                    self.stats["error_issues"] += 1
                    self.load_anthology()
                    continue

                # Commit changes
                self.local_repo.git.add(data_repo_path, update=True)
                self.local_repo.index.commit(
                    f"Process verification for {author_id} (closes #{issue.number})"
                )

                closed_issues.append(issue)

            except Exception as e:
                log.error(f"Error processing issue {issue.number}: {type(e)}: {e}")
                log.exception(e)
                self.stats["error_issues"] += 1
                self.load_anthology()
                continue

        if len(closed_issues) > 0:
            closed_issues_str = "\n".join(
                [f"- closes #{issue.number}" for issue in closed_issues]
            )

            # Create pull request
            if not dry_run:
                title = f"Bulk verifications {today}"

                # push the local branch to github
                self.local_repo.remotes.origin.push(
                    refspec=f"refs/heads/{new_branch_name}"
                )

                pr = self.github_repo.create_pull(
                    title=title,
                    body=closed_issues_str,
                    head=new_branch_name,
                    base="master",
                )
                log.info(f"Created PR: {pr.html_url}")

        # Switch back to original branch
        self.local_repo.head.reference = current_branch
        self.stats["closed_issues"] = len(closed_issues)

    def prepare_and_switch_branch(self, no_branch: bool = False):
        # Create new branch off "master"
        # base_branch = self.local_repo.head.reference
        base_branch = self.local_repo.heads.master

        today = datetime.now().strftime("%Y-%m-%d")
        new_branch_name = f"bulk-verifications-{today}"

        # store the current branch
        current_branch = self.local_repo.head.reference

        # If the branch exists, use it, else create it
        if no_branch:
            # Do not create or change to a new branch
            log.info(f"Staying on branch {current_branch}")
            new_branch_name = current_branch
        elif new_branch_name in self.local_repo.heads:
            ref = self.local_repo.heads[new_branch_name]
            log.info(f"Using existing branch {new_branch_name}")
            ref.checkout()
        else:
            # Create new branch
            log.info(f"Creating branch {new_branch_name} from {base_branch}")
            ref = current_branch.checkout(b=new_branch_name)

        return current_branch, new_branch_name, today


if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")

    import argparse

    parser = argparse.ArgumentParser(description="Bulk author verifications")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress output")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation of approval by Anthology team member",
    )
    parser.add_argument(
        "issue_ids", nargs="*", type=int, help="Specific issue IDs to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (do not create PRs)",
    )
    parser.add_argument(
        "--no-branch",
        action="store_true",
        help="Do not create a new branch or switch branches",
    )

    args = parser.parse_args()

    log_level = log.DEBUG if not args.quiet else log.INFO
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    if not github_token:
        raise ValueError("Please set GITHUB_TOKEN environment variable")

    updater = AnthologyMetadataUpdater(github_token)
    updater.process_verification_issues(
        issue_ids=args.issue_ids,
        verbose=not args.quiet,
        skip_validation=args.skip_validation,
        dry_run=args.dry_run,
        no_branch=args.no_branch,
    )

    for stat in updater.stats:
        log.info(f"{stat}: {updater.stats[stat]}")
