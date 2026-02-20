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
Creates bulk pull request with all approved metadata corrections applied to the XML data

Queries the Github API for all issues in the acl-org/acl-anthology repository.
It then goes through them, looking for ones that
- have metadata correction in the issue title,
- have both "metadata" and "correction" labels,
- a "JSON code block" in the description, and
- are approved by at least one member of the anthology group.
It then creates a new PR on a branch labeled bulk-corrections-YYYY-MM-DD,
where it makes a single PR from changes from all matching issues.

Usage: process_bulk_metadata.py [-q] [--skip-validation] [--dry-run] [--close-old-issues] [ids...]

Options:
    -q, --quiet              Suppress output
    --skip-validation        Skip requirement of "approved" tag
    --dry-run                Dry run (do not create PRs)
    --close-old-issues       Close old metadata requests with a comment (those without a JSON block)
    ids                      Specific issue IDs to process (default: all)

TODO:
- fix reordering bug
- use python library to do it
- ensure valid XML (e.g. "Buy&Hold")
"""

import sys
import os
import copy
from datetime import datetime
from typing import List

from github import Github
import git
import json
import lxml.etree as ET
import re


from anthology.utils import deconstruct_anthology_id, indent, make_simple_element

close_old_issue_comment = """### ⓘ Notice

The Anthology has implemented a new, semi-automated workflow to better handle metadata corrections. We are closing this issue, and invite you to resubmit your request using our new workflow. Please visit your paper page ([{anthology_id}]({url})) and click the yellow 'Fix data' button. This will guide you through the new process step by step."""


class AnthologyMetadataUpdater:
    def __init__(self, github_token):
        """Initialize with GitHub token."""
        self.github = Github(github_token)
        self.github_repo = self.github.get_repo("acl-org/acl-anthology")
        self.local_repo = git.Repo(os.path.join(os.path.dirname(__file__), ".."))
        self.stats = {
            "visited_issues": 0,
            "relevant_issues": 0,
            "approved_issues": 0,
            "unapproved_issues": 0,
        }

    def _is_approved(self, issue):
        """Check if issue has approval from anthology team member."""
        return "approved" in [label.name for label in issue.get_labels()]

    def _parse_metadata_changes(self, issue_body: str) -> None | dict:
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
              "id": "carolyn-anderson"
            }
          ],
          "abstract": "..."
        }
        ```
        """
        # For some reason, the issue body has \r\n line endings
        if issue_body is not None:
            issue_body = issue_body.replace("\r", "")

            if (
                match := re.search(r"```json\n(.*?)\n```", issue_body, re.DOTALL)
            ) is not None:
                return json.loads(match[1])

        return None

    def _apply_changes_to_xml(
        self, xml_repo_path: str, anthology_id: str, changes: dict, verbose: bool
    ) -> ET._ElementTree:
        """Apply the specified changes to XML file."""

        tree = ET.parse(xml_repo_path)
        # factored version
        # tree = ET.ElementTree(ET.fromstring(self.get_file_contents(xml_repo_path)))

        _, volume_id, paper_id = deconstruct_anthology_id(anthology_id)

        is_frontmatter = paper_id == "0"

        if is_frontmatter:
            paper_node = tree.getroot().find(f"./volume[@id='{volume_id}']/meta")
        else:
            paper_node = tree.getroot().find(
                f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']"
            )
        if paper_node is None:
            raise Exception(f"-> Paper not found in XML file: {xml_repo_path}")

        # Apply changes to XML
        if not is_frontmatter:
            # frontmatter has no title or abstract
            for key in ["title", "abstract"]:
                if key in changes:
                    node = paper_node.find(key)
                    if node is None:
                        node = make_simple_element(key, parent=paper_node)
                        # set the node to the structure of the new string
                    try:
                        new_node = ET.fromstring(f"<{key}>{changes[key]}</{key}>")
                    except ET.XMLSyntaxError as e:
                        raise e
                    # replace the current node with the new node in the tree
                    paper_node.replace(node, new_node)

        if "authors" in changes:
            if verbose and "authors_new" in changes:
                # Check that author changes provided as list and as string match: otherwise something might be wrong
                a_from_list = " | ".join(
                    [
                        author["first"] + "  " + author["last"]
                        for author in changes["authors"]
                    ]
                )
                a_new = changes["authors_new"]  #  First  Last | First F  Last Last
                if a_from_list != a_new:
                    print(
                        f"  !! Author information in list and string don't match: "
                        f"{anthology_id}: please check again !!",
                        file=sys.stderr,
                    )

            author_tag = "editor" if paper_id == "0" else "author"

            existing_nodes = list(paper_node.findall(author_tag))
            for author_node in existing_nodes:
                paper_node.remove(author_node)

            def match_existing(author_spec: dict) -> ET._Element | None:
                """
                Match existing XML node to author_spec derived from issue text

                Using heuristics: (1) explicit id match (2) explicit orcid match
                (3) explicit name match (exact match including split)
                If nothing matches, backup to next author node in XML
                """
                # todo: do smarter matching to fix reordering bug
                id_ = author_spec.get("id")
                if id_:
                    for node in existing_nodes:
                        if node.get("id") == id_:
                            existing_nodes.remove(node)
                            return node

                orcid = author_spec.get("orcid")
                if orcid:
                    for node in existing_nodes:
                        if node.get("orcid") == orcid:
                            existing_nodes.remove(node)
                            return node

                first = author_spec.get("first")
                last = author_spec.get("last")
                if first is not None or last is not None:
                    for node in existing_nodes:
                        if (
                            node.findtext("first") == first
                            and node.findtext("last") == last
                        ):
                            existing_nodes.remove(node)
                            return node

                if existing_nodes:
                    # Backup solution to use next available node can lead to errors:
                    if verbose:
                        # print a warning unless either first or last matches this node
                        backup_node = existing_nodes[0]
                        b_f = backup_node.findtext("first")
                        b_l = backup_node.findtext("last")
                        if b_f != first and b_l != last:
                            print(
                                f"  Potentially dangerous node selection for "
                                f"'{first}  {last}': '{b_f}  {b_l}'",
                                file=sys.stderr,
                            )

                    return existing_nodes.pop(0)
                return None

            def append_text_elements(
                tag: str, values: List[str] | str, parent: ET._Element
            ) -> None:
                if isinstance(values, list):
                    for value in values:
                        if value:
                            make_simple_element(tag, text=value, parent=parent)
                elif values:
                    make_simple_element(tag, text=values, parent=parent)

            if is_frontmatter:
                prev_sibling = paper_node.find("booktitle")
            else:
                prev_sibling = paper_node.find("title")

            for author in changes["authors"]:
                existing_node = match_existing(author)

                attrib = {}

                id_value = None
                if existing_node is not None and existing_node.get("id"):
                    # if xml had id: use it or if issue had it too, id from issue supersedes
                    id_value = existing_node.get("id")
                    if author.get("id"):
                        id_value = author["id"]
                elif author.get("id") and existing_node is None:
                    # no node found and id in issue found
                    id_value = author["id"]

                if id_value:
                    attrib["id"] = id_value
                    # todo no check performed whether id ever defined in name_variants.yaml?

                orcid_value = None
                if author.get("orcid"):
                    orcid_value = author["orcid"]
                elif existing_node is not None and existing_node.get("orcid"):
                    orcid_value = existing_node.get("orcid")

                if orcid_value:
                    attrib["orcid"] = orcid_value

                author_node = make_simple_element(
                    author_tag, attrib=attrib, parent=paper_node, sibling=prev_sibling
                )
                prev_sibling = author_node

                # below <author> add <first>,<last>,<affiliation>, <variant>
                # filled either from existing node or from issue data (author)
                first_value = author.get("first")
                if first_value is None and existing_node is not None:
                    first_value = existing_node.findtext("first")
                if first_value:
                    make_simple_element("first", text=first_value, parent=author_node)

                last_value = author.get("last")
                if last_value is None and existing_node is not None:
                    last_value = existing_node.findtext("last")
                if last_value:
                    make_simple_element("last", text=last_value, parent=author_node)

                if author.get("affiliation"):
                    # this will take an affiliation from the issue text and insert it...  potentially overwriting existing!!!
                    append_text_elements(
                        "affiliation", author["affiliation"], author_node
                    )
                elif existing_node is not None:
                    for elem in existing_node.findall("affiliation"):
                        author_node.append(copy.deepcopy(elem))

                if author.get("variant"):
                    append_text_elements("variant", author["variant"], author_node)
                elif existing_node is not None:
                    for elem in existing_node.findall("variant"):
                        author_node.append(copy.deepcopy(elem))

        return tree

    def get_file_contents(self, repo_path, ref="master"):
        """
        Github's repo.get_contents() method has a limit of 1MB for file size. For large files, we need to download from the raw URL. You'd think the API would just handle this transparently, but it doesn't; if the file is too big, it just returns an empty object, and you have to spend hours tracking down why it doesn't work.
        """
        # get the file contents from the repo from the specified ref
        tree = self.local_repo.refs[ref].commit.tree

        # Get file
        blob = tree / repo_path
        file_content = blob.data_stream.read()

        return file_content

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
        issues = self.github_repo.get_issues(
            state="open", labels=["metadata", "correction"]
        )

        current_branch, new_branch_name, today = self.prepare_and_switch_branch()

        # record which issues were successfully processed and need closing
        closed_issues = []

        for issue in issues:
            if "metadata correction" not in issue.title.lower():
                continue

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
                try:
                    json_block = self._parse_metadata_changes(issue.body)
                except json.decoder.JSONDecodeError as e:
                    print(
                        f"Failed to parse JSON block in #{issue.number}: {e}",
                        file=sys.stderr,
                    )
                    json_block = None

                if not json_block:
                    if close_old_issues:
                        self.add_comment_to_issue_without_json(
                            issue, dry_run=dry_run, verbose=verbose
                        )

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
                if verbose:
                    print("-> Applying changes to XML file", file=sys.stderr)

                try:
                    tree = self._apply_changes_to_xml(
                        xml_repo_path, anthology_id, json_block, verbose
                    )
                except Exception as e:
                    print(
                        f"Failed to apply changes to #{issue.number}: {e}",
                        file=sys.stderr,
                    )
                    continue

                if tree:
                    indent(tree.getroot())

                    # dump tree to file
                    tree.write(
                        xml_repo_path,
                        encoding="UTF-8",
                        xml_declaration=True,
                        with_tail=True,
                    )

                    # Commit changes
                    self.local_repo.index.add([xml_repo_path])
                    self.local_repo.index.commit(
                        f"Process metadata corrections for {anthology_id} (closes #{issue.number})"
                    )

                    closed_issues.append(issue)

            except Exception as e:
                print(f"Error processing issue {issue.number}: {type(e)}: {e}")
                e.print_stack_trace()
                continue

        if len(closed_issues) > 0:
            closed_issues_str = "\n".join(
                [f"- closes #{issue.number}" for issue in closed_issues]
            )

            # Create pull request
            if not dry_run:
                title = f"Bulk metadata corrections {today}"

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
                print(f"Created PR: {pr.html_url}", file=sys.stderr)

        # Switch back to original branch
        self.local_repo.head.reference = current_branch
        self.stats["closed_issues"] = len(closed_issues)

    def add_comment_to_issue_without_json(self, issue, dry_run: bool, verbose: bool):
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
                    close_old_issue_comment.format(anthology_id=anthology_id, url=url)
                )
                # close the issue as "not planned"
                issue.edit(state="closed", state_reason="not_planned")

            self.stats["closed_issues"] += 1

    def prepare_and_switch_branch(self):
        # Create new branch off "master"
        # base_branch = self.local_repo.head.reference
        base_branch = self.local_repo.heads.master

        today = datetime.now().strftime("%Y-%m-%d")
        new_branch_name = f"bulk-corrections-{today}"

        # If the branch exists, use it, else create it
        if new_branch_name in self.local_repo.heads:
            ref = self.local_repo.heads[new_branch_name]
            print(f"Using existing branch {new_branch_name}", file=sys.stderr)
        else:
            # Create new branch
            ref = self.local_repo.create_head(new_branch_name, base_branch)
            print(f"Created branch {new_branch_name} from {base_branch}", file=sys.stderr)

        # store the current branch
        current_branch = self.local_repo.head.reference

        # switch to that branch
        self.local_repo.head.reference = ref
        return current_branch, new_branch_name, today


if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")

    import argparse

    parser = argparse.ArgumentParser(description="Bulk metadata corrections")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress output")
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
        verbose=not args.quiet,
        skip_validation=args.skip_validation,
        dry_run=args.dry_run,
        close_old_issues=args.close_old_issues,
    )

    for stat in updater.stats:
        print(f"{stat}: {updater.stats[stat]}", file=sys.stderr)
