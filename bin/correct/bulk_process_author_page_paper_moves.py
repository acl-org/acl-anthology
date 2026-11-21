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
Creates bulk pull request to process approved author page issues filed with the 02b-move-author-papers.yaml
template. This template corresponds to user actions Move and Remove.
- Move goes from an unverified author to a verified author.
- Remove goes from a verified author to an unverified author. It will fail if the
author ID is explicitly specified for a paper being moved.
   * The script will refuse to remove an explicit author ID from a paper.
   unlink_items.py should be used for such cases.
   * LIMITATION: Removing a name-matched paper from a legacy-verified author page
   is supported on the website but not in this script, because the utility function
   we call requires ORCID.

In detail:
Queries the Github API for all issues in the acl-org/acl-anthology repository.
It then goes through them, looking for ones that
- have both "move-paper" and "correction" labels,
- list the current author page URL, URLs of papers to move, and the destination URL
or "unverified"
- are approved by at least one member of the Anthology group.
  "Additional notes" are not read by this script, so the reviewer should check them
  before approving.
It then creates a new PR on a branch labeled bulk-moves-YYYY-MM-DD,
where it makes a single PR from changes from all matching issues.

Usage: bulk_process_simple_verifications.py [options] [<issue_id>...]

Arguments:
    <issue_id>               Specific issue IDs to process (default: all)

Options:
    -q, --quiet              Suppress output
    --skip-validation        Skip requirement of "approved" tag
    --dry-run                Dry run (do not create PRs)
    --no-branch              Stay on the current branch
    -h, --help               Show this help message
"""

from docopt import docopt
import os
import logging as log
from datetime import datetime

from github import Github
import git
import re

from acl_anthology.anthology import Anthology
from acl_anthology.collections import Paper
from acl_anthology.utils.logging import setup_rich_logging

from verify_author import verify_by_author_id, verify_by_paper


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

        ### Current author page

        <author page URL>

        ### Papers to move

        <list of paper URLs, one per line or "all">

        ### Destination

        <destination author page or "unverified">

        ...

        The issue body must already have "\n" line endings.
        """

        # Parse URLs, extract and return IDs
        data = {}
        current = self._form_field(issue_body, "Current author page")
        paper_urls = self._form_field(issue_body, "Papers to move")
        target = self._form_field(issue_body, "Destination")
        if not (current and paper_urls and target):
            return None

        m = re.match(
            r"^https://aclanthology.org/people/([A-Za-z0-9-]+(/unverified)?)/$", current
        )
        if m is None:
            return None
        data["current_author_id"] = m.group(1)
        if target == "unverified":  # verified -> unverified
            data["target_author_id"] = None
            assert "/unverified" not in data["current_author_id"]
        else:  # unverified -> verified
            assert "/unverified" in data["current_author_id"]
            m = re.match(r"^https://aclanthology.org/people/([A-Za-z0-9-]+)/$", target)
            if m is None:
                return None
            data["target_author_id"] = m.group(1)

        if paper_urls == "all":
            data["paper_ids"] = None
        else:
            data["paper_ids"] = []
            for paper_url in paper_urls.split():
                m = re.match(r"^https://aclanthology.org/([A-Za-z0-9\.-]+)/$", paper_url)
                if m is None:
                    return None
                data["paper_ids"].append(m.group(1))
                assert len(set(data["paper_ids"])) == len(data["paper_ids"]), (
                    "Listed paper IDs are not unique"
                )
            if not data["paper_ids"]:
                return None

        return data

    def _form_field(self, issue_body: str, heading: str) -> None | str:
        """Get the answer under a "### heading" in an issue form, or None if left empty."""
        m = re.search(
            rf"### {re.escape(heading)}\n\n(.*?)(?:\n\n###|\Z)", issue_body, re.DOTALL
        )
        if m is None or m.group(1).strip() in ("", "_No response_"):
            return None
        return m.group(1).strip()

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
            required_labels = ["author-page", "correction", "move-papers"]
            if not skip_validation:
                required_labels.append("approved")
            issues = self.github_repo.get_issues(state="open", labels=required_labels)

        current_branch, new_branch_name, today = self.prepare_and_switch_branch(
            no_branch=no_branch
        )

        # record which issues were successfully processed and need closing
        closed_issues = []

        for issue in issues:
            body = issue.body.replace("\r\n", "\n").replace("\r", "\n")

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

                self.stats["relevant_issues"] += 1

                # Skip issues that are not approved by team member
                if not skip_validation and not self._is_approved(issue):
                    if verbose:
                        log.info("-> Skipping (not approved yet)")
                    self.stats["unapproved_issues"] += 1
                    continue

                self.stats["approved_issues"] += 1

                current_author_id = data["current_author_id"]
                target_author_id = data["target_author_id"]
                verified_author_id = (
                    current_author_id if target_author_id is None else target_author_id
                )

                paper_ids = data["paper_ids"]  # None means 'all'

                # XML file path relative to repo root (for reading current state)
                data_repo_path = "data/"
                if verbose:
                    log.info("-> Applying changes to database")

                try:
                    # update the database!
                    person = self.anthology.get_person(verified_author_id)
                    if not person or not person.is_explicit:
                        raise ValueError(
                            f"{verified_author_id} must correspond to a verified author in the database"
                        )
                    if person.orcid is None:
                        raise ValueError(
                            f"Moving papers from/to legacy-verified author ({verified_author_id}) currently not supported"
                        )
                    orcid = person.orcid

                    if target_author_id is None:  # verified -> unverified
                        assert (
                            paper_ids is not None
                        )  # can't remove all papers from a verified page
                        for paper_id in paper_ids:
                            paper = self.anthology.get(paper_id)
                            if (
                                paper is None
                                or not isinstance(paper, Paper)
                                or paper.is_deleted
                            ):
                                raise ValueError(f"Bad paper ID: {paper_id}")
                            current_person = self.anthology.get_person(current_author_id)
                            assert current_person and current_person.is_explicit
                            ns = paper.get_namespec_for(current_person)
                            if ns.id is not None:
                                raise ValueError(
                                    f"Paper specifies explicit author ID: {paper_id}, {ns.id} (if this is an error use unlink_items.py)"
                                )
                        changes = verify_by_author_id(
                            orcid,
                            [verified_author_id],
                            except_paper_ids=paper_ids,
                            anthology=self.anthology,
                        )
                    else:  # unverified -> verified
                        papers_with_nameslug = []
                        if paper_ids is None:  # all papers on the page, i.e. merge
                            changes = verify_by_author_id(
                                orcid,
                                [verified_author_id, current_author_id],
                                anthology=self.anthology,
                            )
                        else:
                            for paper_id in paper_ids:
                                paper = self.anthology.get(paper_id)
                                if (
                                    paper is None
                                    or not isinstance(paper, Paper)
                                    or paper.is_deleted
                                ):
                                    raise ValueError(f"Bad paper ID: {paper_id}")
                                current_person = self.anthology.get_person(
                                    current_author_id
                                )
                                assert current_person and not current_person.is_explicit
                                ns = paper.get_namespec_for(current_person)
                                assert ns.id is None
                                slug = ns.name.slugify()
                                papers_with_nameslug.append(f"{paper_id}:{slug}")
                            changes = verify_by_paper(
                                orcid, papers_with_nameslug, anthology=self.anthology
                            )

                    if changes.startswith("No changes"):
                        log.warning(
                            f"No changes for #{issue.number} (was it already processed?)"
                        )
                        continue
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
                    f"Process move {len(paper_ids) if paper_ids is not None else 'all'} papers: {current_author_id} -> {target_author_id or 'unverified'} (closes #{issue.number})"
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
        new_branch_name = f"bulk-moves-{today}"

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

    assert __doc__ is not None
    args = docopt(__doc__)
    issue_ids = [int(issue_id) for issue_id in args["<issue_id>"]]

    log_level = log.DEBUG if not args["--quiet"] else log.INFO
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    if not github_token:
        raise ValueError("Please set GITHUB_TOKEN environment variable")

    updater = AnthologyMetadataUpdater(github_token)
    updater.process_verification_issues(
        issue_ids=issue_ids,
        verbose=not args["--quiet"],
        skip_validation=args["--skip-validation"],
        dry_run=args["--dry-run"],
        no_branch=args["--no-branch"],
    )

    for stat in updater.stats:
        log.info(f"{stat}: {updater.stats[stat]}")
