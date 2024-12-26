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

Usage: process_bulk_metadata.py [-v]

TODO:
- [X] Need raw abstract text to be passed through
- [X] Handle HTML tags in the title
- [ ] Find XML file, make edit
"""

import sys
import os
from datetime import datetime
from github import Github
import json
import xml.etree.ElementTree as ET
import re

from anthology.utils import deconstruct_anthology_id, indent


class AnthologyMetadataUpdater:
    def __init__(self, github_token):
        """Initialize with GitHub token."""
        self.g = Github(github_token)
        self.repo = self.g.get_repo("acl-org/acl-anthology")
        self.anthology_team_members = self._get_team_members()

    def _get_team_members(self):
        """Get all members of the anthology team."""
        try:
            # Get the anthology team - you'll need to adjust the team name/ID
            teams = self.repo.get_teams()
            anthology_team = next((team for team in teams if team.slug == "anthology"))

            members = set(member.login for member in anthology_team.get_members())
            print("MEMBERS", members)
            return members
        except Exception as e:
            print(f"Error getting team members: {e}")
            return set()

    def _is_approved_by_team_member(self, issue):
        """Check if issue has approval from anthology team member."""
        for reaction in issue.get_reactions():
            if (
                reaction.content == '+1'
                and reaction.user.login in self.anthology_team_members
            ):
                return True
        return False

    def _parse_metadata_changes(self, issue_body):
        """Parse the metadata changes from issue body."""
        # Expected format:
        # JSONN CODE BLOCK
        #
        # ```json
        # {
        #   "anthology_id": "..."
        #   "title": "...",
        #   "authors": [
        #     {
        #       "first": "Carolyn Jane",
        #       "last": "Anderson",
        #       "id": "carolyn-anderson",
        #       "affiliation": ""
        #     }
        #   ],
        #   "abstract": "..."
        # }
        # ```

        # why are these in there
        issue_body = issue_body.replace("\r", "")

        try:
            match = re.search(r"```json\n(.*?)\n```", issue_body, re.DOTALL)

            with open("test.json", "w") as f:
                f.write(issue_body)

            if match:
                # return the first match
                return json.loads(match[1])
        except Exception as e:
            print(f"Error parsing metadata changes: {e}", file=sys.stderr)

        return None

    def _apply_changes_to_xml(self, xml_path, anthology_id, changes):
        """Apply the specified changes to XML file."""
        try:
            print(f"Applying changes to XML file {xml_path}", file=sys.stderr)
            tree = ET.parse(xml_path)

            collection_id, volume_id, paper_id = deconstruct_anthology_id(anthology_id)

            paper_node = tree.getroot().find(f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']")
            if paper_node is None:
                print(f"-> Paper not found in XML file {xml_path}", file=sys.stderr)
                return None

            # Apply changes to XML
            if "title" in changes:
                title_node = paper_node.find("title")
                if title_node is None:
                    title_node = ET.SubElement(paper_node, "title")
                title_node.text = changes["title"]
                print(f"-> Changed title to {changes['title']}", file=sys.stderr)
            if "abstract" in changes:
                abstract_node = paper_node.find("abstract")
                if abstract_node is None:
                    abstract_node = ET.SubElement(paper_node, "abstract")
                abstract_node.text = changes["abstract"]
                print(f"-> Changed abstract to {changes['abstract']}", file=sys.stderr)
            if "authors" in changes:
                authors_node = paper_node.find("authors")
                if authors_node is None:
                    authors_node = ET.SubElement(paper_node, "authors")
                else:
                    authors_node.clear()
                for author in changes["authors"]:
                    attrib = {}
                    if "id" in author:
                        attrib["id"] = author["id"]
                    author_node = ET.SubElement(authors_node, "author", attrib=attrib)
                    if "first" in author:
                        first_node = ET.SubElement(author_node, "first")
                        first_node.text = author["first"]
                    if "last" in author:
                        last_node = ET.SubElement(author_node, "last")
                        last_node.text = author["last"]
                    if "affiliation" in author:
                        affiliation_node = ET.SubElement(author_node, "affiliation")
                        affiliation_node.text = author["affiliation"]
                    print(f"-> Added author {author['first']} {author['last']}", file=sys.stderr)
            return tree
        except Exception as e:
            print(f"Error applying changes to XML: {e}")
            return None

    def process_metadata_issues(self, ids=[], verbose=False, skip_validation=False):
        """Process all metadata issues and create PR with changes."""
        # Get all open issues with required labels
        issues = self.repo.get_issues(state='open', labels=['metadata', 'correction'])

        # Create new branch for changes
        base_branch = self.repo.get_branch("master")
        today = datetime.now().strftime("%Y-%m-%d")
        new_branch_name = f"bulk-corrections-{today}"

        if True:
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

            changes_made = False

            for issue in issues:
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
                    if verbose:
                        print("-> Skipping (no JSON block)", file=sys.stderr)
                    continue

                # Skip issues that are not approved by team member
                if not skip_validation and not self._is_approved_by_team_member(issue):
                    if verbose:
                        print("-> Skipping (not approved yet)", file=sys.stderr)
                    continue

                anthology_id = json_block.get("anthology_id")
                collection_id = anthology_id.split("-")[0]
                xml_path = f"data/xml/{collection_id}.xml"

                # Get current file content
                file_content = self.repo.get_contents(xml_path, ref=new_branch_name)

                # Apply changes to XML
                tree = self._apply_changes_to_xml(xml_path, anthology_id, json_block)

                if tree:
                    # Convert tree to string and encode
                    new_content = ET.tostring(
                        tree.getroot(), encoding='unicode', method='xml'
                    )

                    # Commit changes
                    self.repo.update_file(
                        xml_path,
                        f"Bulk metadata corrections from #{issue.number}",
                        new_content,
                        file_content.sha,
                        branch=new_branch_name,
                    )
                    changes_made = True

            if changes_made:
                # Create pull request
                pr = self.repo.create_pull(
                    title=f"Bulk metadata corrections {today}",
                    body="Automated PR for bulk metadata corrections.\n\n"
                    "This PR includes changes from the following issues:\n"
                    + "\n".join([f"#{issue.number}" for issue in issues]),
                    head=new_branch_name,
                    base="master",
                )
                print(f"Created PR: {pr.html_url}")
            else:
                # Clean up branch if no changes were made
                ref.delete()
                print("No changes to make - deleted branch")

        # except Exception as e:
        #     print(f"Error processing issues: {e}")


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
    parser.add_argument(
        "ids", nargs="*", type=int, help="Specific issue IDs to process"
    )
    args = parser.parse_args()

    if not github_token:
        raise ValueError("Please set GITHUB_TOKEN environment variable")

    updater = AnthologyMetadataUpdater(github_token)
    updater.process_metadata_issues(ids=args.ids, verbose=args.verbose, skip_validation=args.skip_validation)
