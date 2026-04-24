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
- a description that includes an ORCID URL (if the iD contains 'X' it must be uppercase)
  and "[x] Verification"; other author page request types must be unchecked
- are approved by at least one member of the Anthology group.
It then creates a new PR on a branch labeled bulk-verifications-YYYY-MM-DD,
where it makes a single PR from changes from all matching issues.

Usage: bulk_verify_all.py [-q] [--skip-validation] [--dry-run] [issue_ids...]

Options:
    -q, --quiet              Suppress output
    --skip-validation        Skip requirement of "approved" tag
    --dry-run                Dry run (do not create PRs)
    issue_ids                Specific issue IDs to process (default: all)
"""

import os
import warnings
import logging as log
from datetime import datetime

from github import Github
import git
import re

from acl_anthology.anthology import Anthology
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
        """
        issue_body = issue_body.replace("\r\n", "\n").replace("\r", "\n")
        m = re.search(
            r"### Author ORCID\n\nhttps://orcid.org/([0-9X-]{19})\n\n### Institution[^\n]+\n\n([^\n]+)\n",
            issue_body,
            re.MULTILINE,
        )
        if m is None:
            return None
        return {"orcid": m.group(1), "degree": m.group(2)}

    def load_anthology(self):
        log.info("Loading anthology")
        self.anthology = Anthology.from_within_repo()

    def process_verification_issues(
        self,
        issue_ids=[],
        verbose=False,
        skip_validation=False,
        dry_run=False,
        no_branch=False,
    ):
        """Process all simple verification issues and create PR with changes."""
        # Get all open issues with required labels
        issues = self.github_repo.get_issues(
            state="open", labels=["author-page", "correction"]
        )

        current_branch, new_branch_name, today = self.prepare_and_switch_branch(
            no_branch=no_branch
        )

        # record which issues were successfully processed and need closing
        closed_issues = []

        for issue in issues:
            if not issue.title.lower().endswith("/unverified"):
                continue

            if "[x] Verification:" not in issue.body:
                continue
            if "[ ] Split/disambiguate:" not in issue.body:
                continue
            if "[ ] Merge profiles:" not in issue.body:
                continue
            if "[ ] Name change:" not in issue.body:
                continue

            self.stats["visited_issues"] += 1
            try:
                if issue_ids and issue.number not in issue_ids:
                    continue
                opened_at = issue.created_at.strftime("%Y-%m-%d")
                if verbose:
                    log.info(
                        f"ISSUE {issue.number} ({opened_at}): {issue.title} {issue.html_url}"
                    )

                # Parse metadata changes from issue
                data = self._parse_verification_request(issue.body)
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
                xml_repo_path = "data/xml/"
                yaml_repo_path = "data/yaml/"
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
                    self.anthology.save_all()
                except Exception as e:
                    log.error(
                        f"Failed to apply changes to #{issue.number}: {e}",
                    )
                    log.exception(e)
                    self.stats["error_issues"] += 1
                    self.load_anthology()
                    continue

                # Commit changes
                self.local_repo.index.add(
                    [xml_repo_path + "/*.xml", yaml_repo_path + "/*.yaml"]
                )
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

    with warnings.catch_warnings(action="ignore"):  # NameSpecResolutionWarning
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
