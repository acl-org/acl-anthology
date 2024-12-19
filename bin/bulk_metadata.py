#!/usr/bin/env python3

"""
Queries the Github API for all issues in the acl-org/acl-anthology repository. It then goes through them, looking for ones that have both "metadata" and "correction" labels, a "JSON code block" in the description, and are approved by at least one member of the anthology group. It then creates a new PR on a branch labeled bulk-corrections-YYYY-MM-DD, where it makes a single PR from changes from all matching issues.

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
                print("Got a match", match)
                # return the first match
                return json.loads(match[1])
        except Exception as e:
            print(f"Error parsing metadata changes: {e}", file=sys.stderr)

        return None

    def _apply_changes_to_xml(self, xml_path, changes):
        """Apply the specified changes to XML file."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for change in changes:
                elements = root.findall(change['xpath'])
                for element in elements:
                    if 'new_value' in change:
                        element.text = change['new_value']
                    elif 'new_attributes' in change:
                        for attr, value in change['new_attributes'].items():
                            element.set(attr, value)

            return tree
        except Exception as e:
            print(f"Error applying changes to XML: {e}")
            return None

    def process_metadata_issues(self, verbose=False):
        """Process all metadata issues and create PR with changes."""
        # Get all open issues with required labels
        issues = self.repo.get_issues(state='open', labels=['metadata', 'correction'])

        # Create new branch for changes
        base_branch = self.repo.get_branch("master")
        today = datetime.now().strftime("%Y-%m-%d")
        new_branch_name = f"bulk-corrections-{today}"

        try:
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
                # if not self._is_approved_by_team_member(issue):
                #     if verbose:
                #         print("-> Skipping (not approved yet)", file=sys.stderr)
                #     continue

                anthology_id = json_block.get("anthology_id")
                collection_id = anthology_id.split("-")[0]
                xml_path = f"data/xml/{collection_id}.xml"

                # Get current file content
                file_content = self.repo.get_contents(xml_path, ref=new_branch_name)

                # Apply changes to XML
                tree = self._apply_changes_to_xml(xml_path, None)

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

        except Exception as e:
            print(f"Error processing issues: {e}")


if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")

    import argparse

    parser = argparse.ArgumentParser(description="Bulk metadata corrections")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if not github_token:
        raise ValueError("Please set GITHUB_TOKEN environment variable")

    updater = AnthologyMetadataUpdater(github_token)
    updater.process_metadata_issues(args.verbose)
