#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 Matt Post <post@cs.jhu.edu>
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
Queries the Github API for all issues in the acl-org/acl-anthology repository.
It then goes through them, looking for ones that have both "metadata" and "correction"
labels, a "JSON code block" in the description, and are approved by at least one member
of the anthology group. It then creates a new PR on a branch labeled bulk-corrections-YYYY-MM-DD,
where it makes a single PR from changes from all matching issues.

Usage: process_bulk_metadata.py [-v] [--skip-validation] [--dry-run] [--close-old-issues] [ids...]

Options:
    -v, --verbose            Verbose output
    --skip-validation        Skip requirement of "approved" tag
    --dry-run                Dry run (do not create PRs)
    --close-old-issues       Close old metadata requests with a comment (those without a JSON block)
    ids                      Specific issue IDs to process (default: all)
"""

import sys
import os
from datetime import datetime
from github import Github
import json
import lxml.etree as ET
import re

from anthology.utils import deconstruct_anthology_id, indent, make_simple_element

close_old_issue_comment = """### ⓘ Notice

The Anthology has implemented a new, semi-automated workflow to better handle metadata corrections. We are closing this issue, and invite you to resubmit your request using our new workflow. Please visit your paper page ([{anthology_id}]({url})) and click the yellow 'Fix data' button. This will guide you through the new process step by step."""


class AnthologyMetadataUpdater:
    def __init__(self, github_token):
        """Initialize with GitHub token."""
        self.g = Github(github_token)
        self.repo = self.g.get_repo("acl-org/acl-anthology")
        self.stats = {
            "closed_issues": 0,
            "visited_issues": 0,
            "relevant_issues": 0,
            "approved_issues": 0,
            "merged_issues": 0,
            "unapproved_issues": 0,
        }

    def _is_approved(self, issue):
        """Check if issue has approval from anthology team member."""
        return "approved" in [label.name for label in issue.get_labels()]

    def _parse_metadata_changes(self, issue_body):
        """Parse the metadata changes from issue body.

        Expected format:
        JSON CODE BLOCK

        ```json
        {
          "anthology_id": "..."
          "title": "...",
          "authors": [
            {
              "first": "Carolyn Jane",
              "last": "Anderson",
              "id": "carolyn-anderson",
              "affiliation": ""
            }
          ],
          "abstract": "..."
        }
        ```
        """
        # For some reason, the issue body has \r\n line endings
        issue_body = issue_body.replace("\r", "")

        try:
            if (
                match := re.search(r"```json\n(.*?)\n```", issue_body, re.DOTALL)
            ) is not None:
                return json.loads(match[1])
        except Exception as e:
            print(f"Error parsing metadata changes: {e}", file=sys.stderr)

        return None

    def _apply_changes_to_xml(self, xml_path, anthology_id, changes):
        """Apply the specified changes to XML file."""
        try:
            print(f"-> Applying changes to XML file {xml_path}", file=sys.stderr)
            tree = ET.parse(xml_path)

            _, volume_id, paper_id = deconstruct_anthology_id(anthology_id)

            paper_node = tree.getroot().find(
                f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']"
            )
            if paper_node is None:
                print(f"-> Paper not found in XML file {xml_path}", file=sys.stderr)
                return None

            # Apply changes to XML
            for key in ["title", "abstract"]:
                if key in changes:
                    node = paper_node.find(key)
                    if node is None:
                        node = make_simple_element(key, parent=paper_node)
                    # set the node to the structure of the new string
                    new_node = ET.fromstring(f"<{key}>{changes[key]}</{key}>")
                    # replace the current node with the new node in the tree
                    paper_node.replace(node, new_node)
            if "authors" in changes:
                """
                Every author has an id, but for a small subset, these ids are explicit, since they're used for disambiguation. To distinguish these, we need to find the subset of the authors in the current XML that have explicit ID attributes. We then use this below to set the ID.
                """
                real_ids = set()
                for author in changes["authors"]:
                    id_ = author.get("id", None)
                    if id_:
                        existing_author = paper_node.find(f"author[@id='{id_}']")
                        if existing_author is not None:
                            real_ids.add(id_)

                # remove existing author nodes
                for author_node in paper_node.findall("author"):
                    paper_node.remove(author_node)

                prev_sibling = paper_node.find("title")

                for author in changes["authors"]:
                    attrib = {}
                    if "id" in real_ids:
                        # if the ID was explicitly represented, preserve it
                        attrib["id"] = author["id"]
                    # create author_node and add as sibling after insertion_point
                    author_node = make_simple_element(
                        "author", attrib=attrib, parent=paper_node, sibling=prev_sibling
                    )
                    prev_sibling = author_node
                    if "first" in author:
                        first_node = make_simple_element("first", parent=author_node)
                        first_node.text = author["first"]
                    if "last" in author:
                        last_node = make_simple_element("last", parent=author_node)
                        last_node.text = author["last"]
                    if "affiliation" in author and author["affiliation"]:
                        affiliation_node = make_simple_element(
                            "affiliation", parent=author_node
                        )
                        affiliation_node.text = author["affiliation"]

            return tree
        except Exception as e:
            print(f"Error applying changes to XML: {e}", file=sys.stderr)
            return None

    def process_metadata_issues(
        self,
        ids=[],
        verbose=False,
        skip_validation=False,
        dry_run=False,
        close_old_issues=False,
    ):
        """Process all metadata issues and create PR with changes."""
        # Get all open issues with required labels
        issues = self.repo.get_issues(state='open', labels=['metadata', 'correction'])

        # Create new branch for changes
        base_branch = self.repo.get_branch("master")
        today = datetime.now().strftime("%Y-%m-%d")
        new_branch_name = f"bulk-corrections-{today}"

        # Check if branch already exists
        existing_branch = next(
            (
                ref
                for ref in self.repo.get_git_refs()
                if ref.ref == f"refs/heads/{new_branch_name}"
            ),
            None,
        )
        if existing_branch:
            print(f"Deleting existing branch {new_branch_name}")
            existing_branch.delete()

        # Create new branch
        ref = self.repo.create_git_ref(
            ref=f"refs/heads/{new_branch_name}", sha=base_branch.commit.sha
        )

        # record which issues were successfully processed and need closing
        closed_issues = []

        for issue in issues:
            self.stats["visited_issues"] += 1
            try:
                if ids and issue.number not in ids:
                    continue
                opened_at = issue.created_at.strftime("%Y-%m-%d")
                if verbose:
                    print(
                        f"ISSUE {issue.number} ({opened_at}): {issue.title} {issue.html_url}",
                        file=sys.stderr,
                    )

                # Parse metadata changes from issue
                json_block = self._parse_metadata_changes(issue.body)
                if not json_block:
                    if close_old_issues:
                        # for old issues, filed without a JSON block, we append a comment
                        # alerting them to how to file a new issue using the new format.
                        # If possible, we first parse the Anthology ID out of the title:
                        # Metadata correction for {anthology_id}. We can then use this to
                        # post a link to the original paper so they can go through the
                        # automated process.
                        anthology_id = None
                        match = re.search(r"Paper Metadata: [\{]?(.*)[\}]?", issue.title)
                        if match:
                            anthology_id = match[1]
                        if anthology_id:
                            if verbose:
                                print(
                                    f"-> Closing issue {issue.number} with a link to the new process",
                                    file=sys.stderr,
                                )
                            if not dry_run:
                                url = f"https://aclanthology.org/{anthology_id}"
                                issue.create_comment(
                                    close_old_issue_comment.format(
                                        anthology_id=anthology_id, url=url
                                    )
                                )
                                # close the issue as "not planned"
                                issue.edit(state="closed", state_reason="not_planned")

                            self.stats["closed_issues"] += 1
                            continue
                    else:
                        if verbose:
                            print("-> Skipping (no JSON block)", file=sys.stderr)
                    continue

                self.stats["relevant_issues"] += 1
                # Skip issues that are not approved by team member
                if not skip_validation and not self._is_approved(issue):
                    if verbose:
                        print("-> Skipping (not approved yet)", file=sys.stderr)
                    self.stats["unapproved_issues"] += 1
                    continue

                self.stats["approved_issues"] += 1
                anthology_id = json_block.get("anthology_id")
                collection_id, _, _ = deconstruct_anthology_id(anthology_id)

                # XML file path relative to repo root (for reading current state)
                xml_repo_path = f"data/xml/{collection_id}.xml"
                file_content = self.repo.get_contents(xml_repo_path, ref=new_branch_name)

                # XML file path on file system (for writing changes)
                scriptdir = os.path.dirname(os.path.abspath(__file__))
                xml_file_path = f"{scriptdir}/../data/xml/{collection_id}.xml"
                tree = self._apply_changes_to_xml(xml_file_path, anthology_id, json_block)

                if tree:
                    indent(tree.getroot())

                    # write to string
                    new_content = ET.tostring(
                        tree.getroot(), encoding="UTF-8", xml_declaration=True
                    )

                    # Commit changes
                    self.repo.update_file(
                        xml_repo_path,
                        f"Processed metadata corrections for #{issue.number}",
                        new_content,
                        file_content.sha,
                        branch=new_branch_name,
                    )
                    closed_issues.append(issue)
                    self.stats["merged_issues"] += 1

        if len(closed_issues) > 0:
            closed_issues_str = "\n".join(
                [f"- closes #{issue.number}" for issue in closed_issues]
            )

            # Create pull request
            if not dry_run:
                pr = self.repo.create_pull(
                    title=f"Bulk metadata corrections {today}",
                    body="Automated PR for bulk metadata corrections.\n\n"
                    + closed_issues_str,
                    head=new_branch_name,
                    base="master",
                )
                print(f"Created PR: {pr.html_url}")
        else:
            # Clean up branch if no changes were made
            ref.delete()
            print("No changes to make, deleted branch")


if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")

    import argparse

    parser = argparse.ArgumentParser(description="Bulk metadata corrections")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation of approval by Anthology team member",
    )
    parser.add_argument("ids", nargs="*", type=int, help="Specific issue IDs to process")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (do not create PRs)",
    )
    parser.add_argument(
        "--close-old-issues",
        action="store_true",
        help="Close old metadata requests with a comment (those without a JSON block)",
    )

    args = parser.parse_args()

    if not github_token:
        raise ValueError("Please set GITHUB_TOKEN environment variable")

    updater = AnthologyMetadataUpdater(github_token)
    updater.process_metadata_issues(
        ids=args.ids,
        verbose=args.verbose,
        skip_validation=args.skip_validation,
        dry_run=args.dry_run,
        close_old_issues=args.close_old_issues,
    )

    for stat in updater.stats:
        print(f"{stat}: {updater.stats[stat]}", file=sys.stderr)
