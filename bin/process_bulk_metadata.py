#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024 Matt Post <post@cs.jhu.edu>, 2026 weissenh
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
+ have "metadata correction" in the issue title,
+ have both "metadata" and "correction" labels,
+ a "JSON code block" in the description, and
+ are approved by at least one member of the Anthology group ("approved" label).
It then creates a new PR on a branch labeled bulk-corrections-YYYY-MM-DD,
where it makes a single PR from changes from all matching issues.
Note: if you have non-staged changes, the script will try to stash them before switching
to the other branch.

Usage:
  process_bulk_metadata.py [-q] [--skip-validation] [--dry-run] [--close-old-issues] [ <issueid>... ]

Options:
    -h, --help               Show this help message
    -q, --quiet              Suppress output
    --skip-validation        Skip requirement of "approved" tag
    --dry-run                Dry run (do not create PRs or add issue comments)
    --close-old-issues       Close old metadata requests with a comment (those without a JSON block)
    <issueid>                Specific issue IDs to process (default: all)

TODO:
- fix reordering bug, improve name matching
- detect duplicate issues
- allow specifying own branch name
"""

import os
import warnings
from datetime import datetime
from typing import List, Optional, Tuple, Dict
import logging as log
from docopt import docopt
import jsonschema
from jsonschema import validate

from github import Github
from github.Issue import Issue
import git
import json
import re
import lxml.etree as etree

from acl_anthology import Anthology
from acl_anthology.collections import Paper
from acl_anthology.people import NameSpecification, Name, Person
from acl_anthology.text import MarkupText
from acl_anthology.utils.ids import is_verified_person_id

close_old_issue_comment = """### ⓘ Notice

The Anthology has implemented a new, semi-automated workflow to better handle metadata corrections. We are closing this issue, and invite you to resubmit your request using our new workflow. Please visit your paper page ([{anthology_id}]({url})) and click the yellow 'Fix data' button. This will guide you through the new process step by step."""

# specify the schema for the JSON provided in the issue. developed with https://www.jsonschemavalidator.net/
AUTHORS = "authors"
AUTHOR_ID, AUTHOR_LAST, AUTHOR_FIRST = "id", "last", "first"
ABSTRACT = "abstract"
TITLE = "title"
ANTHOLOGY_ID = "anthology_id"
NEW_AUTHORS, OLD_AUTHORS = "authors_new", "authors_old"
AUTHOR_ADDED = "##ADDED##"
DELETED_AUTHORS = "deleted_authors"
METADATA_JSON_SCHEMA = {
    "type": "object",
    "required": [ANTHOLOGY_ID],
    "anyOf": [
        {"required": [AUTHORS, OLD_AUTHORS, NEW_AUTHORS]},
        {"required": [TITLE]},
        {"required": [ABSTRACT]},
    ],
    "properties": {
        "anthology_id": {
            "type": "string",
            "pattern": "^([.a-z0-9-]+\\.[0-9]+|[A-Z][0-9][0-9]-[0-9]+)$",
        },
        AUTHORS: {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [AUTHOR_FIRST, AUTHOR_LAST, AUTHOR_ID],
                "properties": {
                    AUTHOR_LAST: {"type": "string", "pattern": "^\\S+( \\S+)*$"},
                    AUTHOR_FIRST: {"type": "string", "pattern": "^(\\S+( \\S+)*)?$"},
                    AUTHOR_ID: {
                        "type": "string",
                        "pattern": "^([a-z0-9]+(-[a-z0-9]+)*(/unverified)?|"
                        + AUTHOR_ADDED
                        + ")$",
                    },
                },
                "additionalProperties": False,
            },
        },
        DELETED_AUTHORS: {
            "type": "array",
            "items": {
                "type": "object",
                "required": [AUTHOR_FIRST, AUTHOR_LAST, AUTHOR_ID],
                "properties": {
                    AUTHOR_LAST: {"type": "string", "pattern": "^\\S+( \\S+)*$"},
                    AUTHOR_FIRST: {"type": "string", "pattern": "^(\\S+( \\S+)*)?$"},
                    AUTHOR_ID: {
                        "type": "string",
                        "pattern": "^[a-z0-9]+(-[a-z0-9]+)*(/unverified)?$",
                    },
                },
                "additionalProperties": False,
            },
        },
        OLD_AUTHORS: {"type": "string"},
        NEW_AUTHORS: {"type": "string"},
        TITLE: {"type": "string", "pattern": "^\\S+( \\S+)*$"},
        ABSTRACT: {"type": "string"},
    },
    "additionalProperties": False,
}


class AnthologyMetadataUpdater:
    def __init__(self, github_token, verbose: bool = False):
        """Initialize with GitHub token."""
        self.github = Github(github_token)
        self.github_repo = self.github.get_repo("acl-org/acl-anthology")
        self.local_repo = git.Repo(
            os.path.join(os.path.dirname(__file__), "..")
        )  # todo make this more flexible
        self.stats = {
            "visited_issues": 0,
            "relevant_issues": 0,
            "approved_issues": 0,
            "unapproved_issues": 0,
        }
        self.verbose = verbose

        # don't load the anthology here because we may be switching to another
        # branch with a different version of the database

    def load_anthology(self):
        self.anthology = Anthology.from_within_repo(verbose=self.verbose)
        self.anthology.load_all()  # not needed to load_all?

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

    def _has_expected_json_structure(self, json_block: dict) -> bool:
        """Checks presence of required keys/structure"""

        # check against the schema. raises if the validation fails
        try:
            validate(json_block, METADATA_JSON_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            log.exception(e)
            return False

        # warn if author list contradicts info in authors_new
        # or fails to match the length of authors_old
        if AUTHORS in json_block:
            # Check that author changes provided as list and as string match:
            # otherwise something might be wrong
            a_from_list = " | ".join(
                [
                    author[AUTHOR_FIRST] + "  " + author[AUTHOR_LAST]
                    for author in json_block[AUTHORS]
                ]
            )
            a_new = json_block[NEW_AUTHORS]  # First  Last | First F  Last Last
            if a_from_list != a_new:
                log.warning(
                    f"--> Author information in '{AUTHORS}' and '{NEW_AUTHORS}' "
                    f"don't match: please check again.",
                )
                return False

            num_retained = sum(
                1 for author in json_block[AUTHORS] if author[AUTHOR_ID] != AUTHOR_ADDED
            )
            num_deleted = len(json_block.get(DELETED_AUTHORS, []))
            a_old = json_block[OLD_AUTHORS]
            if len(a_old.split(" | ")) != num_retained + num_deleted:
                log.warning(
                    f"--> Number of authors in '{AUTHORS}' and '{DELETED_AUTHORS}' "
                    f"doesn't match '{OLD_AUTHORS}': please check again.",
                )
                return False

        return True

    def _is_sensible_request(self, json_block: dict) -> bool:
        """Checks whether request from JSON makes sense"""
        has_expected_json_structure = self._has_expected_json_structure(json_block)
        if not has_expected_json_structure:
            return False

        # more semantic checks
        # - Paper needs to be known to anthology
        anthology_id = json_block[ANTHOLOGY_ID]
        if self.anthology.get_paper(anthology_id) is None:
            log.warning(f"-> Paper not found: {anthology_id}")
            return False

        # - XML needs to match schema
        for key in [TITLE, ABSTRACT]:
            if key not in json_block:
                continue
            ex = json_block[key]
            bigtree = etree.fromstring(
                f'<collection id="dummy"><volume id="1" type="proceedings"><meta><booktitle>{ex}</booktitle><venue>acl</venue><year>2000</year></meta></volume></collection>'
            )
            is_valid = self.anthology.relaxng.validate(bigtree)
            if not is_valid:
                log.warning(f"-> Value for {key} is not valid XML according to schema")
                return False

        return True

    def evaluate_issue(
        self,
        issue: Issue,
        ids: List[int] = [],
        dry_run: bool = True,
        skip_validation: bool = False,
        close_old_issues: bool = False,
    ) -> Optional[Tuple[Paper, Dict[str, str]]]:
        """
        Filters issues if eligible, retrieves Paper and change request on the way

        returns respective paper and changes asked for in case of success, None otherwise
        """

        def is_approved(issue: Issue):
            return "approved" in [label.name for label in issue.get_labels()]

        if "metadata correction" not in issue.title.lower():
            return None
        self.stats["visited_issues"] += 1

        if ids and issue.number not in ids:
            return None

        opened_at = issue.created_at.strftime("%Y-%m-%d")
        log.info(f"ISSUE {issue.number} ({opened_at}): {issue.title} {issue.html_url}")

        # Parse metadata changes from issue
        try:
            json_block = self._parse_metadata_changes(issue.body)
        except json.decoder.JSONDecodeError as e:
            log.warning(f"-> Failed to parse JSON block in #{issue.number}: {e}")
            json_block = None

        if not json_block:
            if close_old_issues:
                self.add_comment_to_issue_without_json(issue, dry_run=dry_run)
            return None
        self.stats["relevant_issues"] += 1

        # Skip issues that are not approved by team member
        if not skip_validation and not is_approved(issue):
            log.info("-> Skipping (not approved yet)")
            self.stats["unapproved_issues"] += 1
            return None
        self.stats["approved_issues"] += 1

        # Input validation and plausibility checks
        is_sensible = self._is_sensible_request(json_block)
        if not is_sensible:
            return None
        anthology_id = json_block.get(ANTHOLOGY_ID)
        assert anthology_id is not None, "Input validation already performed"
        paper = self.anthology.get_paper(anthology_id)
        assert paper is not None, "Input validation already performed"

        return paper, json_block

    def _update_paper_authors(self, paper: Paper, changes: dict) -> Paper:
        """
        Update authors of the paper as specified by changes.
        Logic assumes the given ID for each author is the *current* ID.
        This ID is used for matching entries in the new author list against
        the old one to retain existing hidden data (e.g. affiliation, orcid etc).
        """
        assert AUTHORS in changes, "Only call this method, if authors-key in JSON block"

        # create ID-to-JSON mappings for deleted and retained authors
        # (excluding added authors, which have a pseudo-ID of `##ADDED##`)
        deleted_author_json_by_id = {
            auth[AUTHOR_ID]: auth for auth in changes.get(DELETED_AUTHORS, {})
        }
        retained_author_json_by_id = {}
        for auth in changes[AUTHORS]:
            if (aid := auth[AUTHOR_ID]) != AUTHOR_ADDED:
                if aid in retained_author_json_by_id:
                    # we have already seen this author ID. OK if unverified:
                    assert aid.endswith(
                        "/unverified"
                    ), f"Duplicate verified author ID in author list: {aid}"
                    log.warning(
                        f"--> Duplicate unverified author ID in author list (possibly valid): {aid}",
                    )
                retained_author_json_by_id[aid] = auth

        # warn about overlap between IDs in the retained and deleted author lists
        for aid in deleted_author_json_by_id.keys() & retained_author_json_by_id.keys():
            log.warning(
                f"--> Author ID appears in both author list and deleted authors list (possibly valid): {aid}",
            )

        # check that if current author list contains duplicate (unverified) author IDs,
        # they do not have hidden attributes like affiliations attached
        current_author_namespecs_by_id = {}
        for current_author in paper.authors or paper.parent.editors:
            person = self.anthology.people.get_by_namespec(current_author)
            if person.id in current_author_namespecs_by_id:
                # duplicate. check that namespecs are identical
                assert current_author == (
                    earlier_match := current_author_namespecs_by_id[person.id]
                ), f"Duplicate author should have identical namespec: {earlier_match} vs. {current_author}"
            else:
                current_author_namespecs_by_id[person.id] = current_author

        # edit current namespecs for non-added authors. this retains any existing hidden attributes like orcid
        for current_author in paper.authors or paper.parent.editors:
            person = self.anthology.people.get_by_namespec(current_author)
            if person.id in retained_author_json_by_id:
                retained_author_json_by_id[person.id]["namespec"] = current_author
                # update namespec based on JSON
                current_author.name = Name(
                    retained_author_json_by_id[person.id][AUTHOR_FIRST],
                    retained_author_json_by_id[person.id][AUTHOR_LAST],
                )
                if not person.has_name(current_author.name):
                    # new variant
                    person.add_name(current_author.name)
            else:
                assert (
                    person.id in deleted_author_json_by_id
                ), f"Author ID is missing or author should be listed as deleted: {person.id}"
                deleted_author_json_by_id[person.id]["namespec"] = current_author

        # construct revised list of author namespecs, creating new namespecs for any added authors
        final_authors = []
        for auth in changes[AUTHORS]:
            if auth[AUTHOR_ID] == AUTHOR_ADDED:
                auth["namespec"] = NameSpecification(name=Name.from_dict(auth))
            if (
                "namespec" not in auth
                and auth[AUTHOR_ID] in current_author_namespecs_by_id
            ):
                # duplicate author
                auth["namespec"] = current_author_namespecs_by_id[auth[AUTHOR_ID]]
            assert (
                "namespec" in auth
            ), f'Could not match JSON author ID to an entry in the current author list: "{auth[AUTHOR_ID]}"'
            final_authors.append(auth["namespec"])

        # check that deleted authors were in fact present in the original author list
        for aid, auth in deleted_author_json_by_id.items():
            if (
                "namespec" not in auth
                and auth[AUTHOR_ID] in current_author_namespecs_by_id
            ):
                # duplicate author
                auth["namespec"] = current_author_namespecs_by_id[auth[AUTHOR_ID]]
            assert (
                "namespec" in auth
            ), f'Could not match JSON deleted author ID to an entry in the current author list: "{aid}"'

        # replace the old list of authors/editors with the new one
        if paper.is_frontmatter:
            paper.parent.editors = final_authors
        else:  # assume it is normal Paper with authors field
            paper.authors = final_authors

        return paper

    def _apply_changes_to_paper(self, paper: Paper, changes: dict) -> Paper:
        """Apply the specified changes to the paper."""

        def str_to_markup(text: str) -> MarkupText:  # raises lxml.etree.XMLSyntaxError
            return MarkupText.from_xml(etree.fromstring(f"<dummy>{text}</dummy>"))

        if not paper.is_frontmatter:
            # frontmatter has no title or abstract  : cannot change booktitle
            if TITLE in changes:
                paper.title = str_to_markup(changes[TITLE])
            if ABSTRACT in changes:
                paper.abstract = str_to_markup(changes[ABSTRACT])

        if AUTHORS in changes:
            paper = self._update_paper_authors(paper=paper, changes=changes)

        if not paper.is_frontmatter:
            # as of 02/2026 bibkey generation for frontmatter can still be improved
            # also don't expect a change as authors not relevant for frontmatter bibkey
            paper.refresh_bibkey()  # changes bibkey only if necessary
        return paper

    def process_metadata_issues(
        self,
        ids=[],
        skip_validation=False,
        dry_run=False,
        close_old_issues=False,
    ):
        """Process all metadata issues and create PR with changes."""
        # Get all open issues with required labels
        issues = self.github_repo.get_issues(
            state='open', labels=['metadata', 'correction']
        )

        current_branch, new_branch_name, today = self.prepare_and_switch_branch()

        self.load_anthology()

        # record which issues were successfully processed and need closing
        closed_issues = []

        for issue in issues:
            # Parse issue and find paper, filtering out non-eligible issues
            evaluation_result = self.evaluate_issue(
                issue,
                ids=ids,
                dry_run=dry_run,
                skip_validation=skip_validation,
                close_old_issues=close_old_issues,
            )
            if not evaluation_result:
                continue
            paper, json_block = evaluation_result

            # Apply changes to paper
            log.debug("-> Updating paper data based on correction requested")
            try:
                paper = self._apply_changes_to_paper(paper, json_block)
            except Exception as e:  # e.g. XML Parsing failed
                log.warning(f"Failed to apply changes to #{issue.number}: {e}")
                log.exception(e)
                # revert changes already made for this issue # todo how to best do this? test it thoroughly
                self.load_anthology()
                continue

            # Save changes to disk and commit
            try:
                # Save changes to disk
                paper.collection.save()
                self.anthology.people.save()
                self.anthology.reset_indices()

                # No need to take action if the paper XML hasn't received any updates
                paper_path = paper.collection.path
                if not self.local_repo.index.diff(None, paths=paper_path):
                    # assume people file wasn't modified either # todo test this
                    log.debug(
                        f"Nothing modified for {paper.full_id} (#{issue.number}) "
                        f"- nothing to commit. Please review again."
                    )
                    continue

                # Commit changes
                # ... to the paper (XML of collection)
                self.local_repo.index.add([paper.collection.path])
                # ... to the people.yaml
                # e.g. when the metadata correction has surfaced a new name variant
                people_file = self.anthology.people.path
                if self.local_repo.index.diff(None, paths=people_file):
                    log.debug(
                        f"People file has been modified too: "
                        f"Due to {paper.full_id} (#{issue.number})"
                    )
                    self.local_repo.index.add([people_file])

                self.local_repo.index.commit(
                    f"Process metadata corrections for {paper.full_id} (closes #{issue.number})"
                )

                closed_issues.append(issue)

                # TODO: why is this needed after save/commit?
                #self.load_anthology()
            except Exception as e:
                log.warning(f"Error processing issue {issue.number}: {type(e)}: {e}")
                log.exception(e)
                # If we land here, we should carefully monitor file states and git status
                continue

        if len(closed_issues) > 0 and not dry_run:
            self._create_pull_request(closed_issues, new_branch_name, today)
            pass

        # Switch back to original branch
        # self.local_repo.head.reference = current_branch
        # self.local_repo.head.reset(index=True, working_tree=True)
        # self.local_repo.git.stash(["pop"])

        self.stats["closed_issues"] = len(closed_issues)

    def _create_pull_request(
        self, closed_issues: List[Issue], new_branch_name: str, today: str
    ):
        closed_issues_str = "\n".join(
            [f"- closes #{issue.number}" for issue in closed_issues]
        )
        title = f"Bulk metadata corrections {today}"

        # push the local branch to github
        self.local_repo.remotes.origin.push(refspec=f"refs/heads/{new_branch_name}")

        pr = self.github_repo.create_pull(
            title=title,
            body=closed_issues_str,
            head=new_branch_name,
            base="master",
        )
        log.info(f"Created PR: {pr.html_url}")

    def add_comment_to_issue_without_json(self, issue, dry_run: bool):
        """
        Legacy method: close old issues having outdated format

        for old issues, filed without a JSON block, we append a comment
        alerting them to how to file a new issue using the new format.
        If possible, we first parse the Anthology ID out of the title:
        Metadata correction for {anthology_id}. We can then use this to
        post a link to the original paper so they can go through the
        automated process.
        """
        anthology_id = None
        match = re.search(r"Paper Metadata: [\{]?(.*)[\}]?", issue.title)
        if match:
            anthology_id = match[1]
        if anthology_id:
            log.info(f"-> Closing issue {issue.number} with a link to the new process")
            if not dry_run:
                try:
                    url = f"https://aclanthology.org/{anthology_id}"
                    issue.create_comment(
                        close_old_issue_comment.format(anthology_id=anthology_id, url=url)
                    )
                    # close the issue as "not planned"
                    issue.edit(state="closed", state_reason="not_planned")
                except Exception as e:
                    log.error(f"Error trying to close old issue #{issue.number}: {e}")
                    log.exception(e)
                    return
            self.stats["closed_issues"] += 1

    def prepare_and_switch_branch(self):
        # Create new branch off "master"
        base_branch = self.local_repo.head.reference
        # base_branch = self.local_repo.heads.master

        today = datetime.now().strftime("%Y-%m-%d")
        new_branch_name = f"bulk-corrections-{today}"
        # new_branch_name = f"bulk-corrections-debugging"

        # If the branch exists, use it, else create it
        if new_branch_name in self.local_repo.heads:
            ref = self.local_repo.heads[new_branch_name]
            log.info(f"Using existing branch {new_branch_name}")
        else:
            # Create new branch
            ref = self.local_repo.create_head(new_branch_name, base_branch)
            log.info(f"Created branch {new_branch_name} from {base_branch}")

        # store the current branch
        current_branch = self.local_repo.head.reference
        self.local_repo.git.stash(['push', f'-m "{datetime.now().isoformat()}"'])

        # switch to that branch
        self.local_repo.head.reference = ref
        self.local_repo.head.reset(index=True, working_tree=True)

        return current_branch, new_branch_name, today


if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("Please set GITHUB_TOKEN environment variable")

    args = docopt(__doc__)

    log_level = log.DEBUG if not args["--quiet"] else log.INFO
    log.basicConfig(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)
    # tracker = setup_rich_logging(level=log_level)

    ids = [int(iid) for iid in args["<issueid>"]]

    updater = AnthologyMetadataUpdater(github_token, verbose=args["--quiet"])
    with warnings.catch_warnings(action="ignore"):  # NameSpecResolutionWarning
        updater.process_metadata_issues(
            ids=ids,
            skip_validation=args["--skip-validation"],
            dry_run=args["--dry-run"],
            close_old_issues=args["--close-old-issues"],
        )

    for stat in updater.stats:
        log.info(f"{stat}: {updater.stats[stat]}")
