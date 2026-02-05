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


AUTHORS = "authors"
AUTHOR_ID, AUTHOR_LAST, AUTHOR_FIRST = "id", "last", "first"
ABSTRACT = "abstract"
TITLE = "title"
ANTHOLOGY_ID = "anthology_id"
NEW_AUTHORS, OLD_AUTHORS = "authors_new", "authors_old"
allowed_keys = [AUTHORS, ABSTRACT, TITLE, ANTHOLOGY_ID, NEW_AUTHORS, OLD_AUTHORS]
author_keys = [AUTHOR_ID, AUTHOR_LAST, AUTHOR_FIRST]


def match_old_to_new_authors(
    paper: Paper, new_authors: List[NameSpecification], anthology: Anthology
) -> List[Tuple[NameSpecification, NameSpecification]]:
    """
    Given anthology (PersonIndex), matches authors from paper to new author list

    Returns list of old,new NameSpecifications of length new_authors. old may be None

    Match list of new authors to paper's current authors using heuristics
    TODO: improve matching - reordering bug probably still present
    TODO: also handle case of completely different author set
    Heuristics:
    1. explicit id match
    2. slugified names match
    3. If nothing matches, backup to next available in candidate list (or None if no more)
    """
    old_new_pairs = list()

    old_authors = paper.authors if not paper.is_frontmatter else paper.get_editors()
    # candidates: dict( position_old -> (NameSpec, Person) )
    candidates = {
        i: (namespec, anthology.resolve(namespec))
        for i, namespec in enumerate(old_authors)
    }

    # First round: match based on id or name slug
    for new_author in new_authors:
        # (1) id match?  todo: breaks if reordering done by replacing names instead of drag/drop
        id_ = new_author.id
        if id_:
            # NameSpecs often have None id, but the Person they are resolved to has an id we can compare to
            gen = (
                (i, ns)
                for i, (ns, p) in candidates.items()
                if ns.id == id_ or id_ == p.id
            )
            if item := next(gen, None):
                i, ns = item
                old_new_pairs.append((ns, new_author))
                del candidates[i]
                continue
        # (2) Exact match of ORCID (orcid needs to be non-empty for both)
        # skip this case as we shouldn't allow adding ORCIDs in issue json block?
        # (3) Match on name slugs
        slug = new_author.name.slugify()
        gen = ((i, ns) for i, (ns, _) in candidates.items() if ns.name.slugify() == slug)
        if item := next(gen, None):
            i, ns = item
            old_new_pairs.append((ns, new_author))
            del candidates[i]
            continue

        # If no match, register with empty predecessor for now
        old_new_pairs.append((None, new_author))

    # Second round: maybe can match nonetheless?
    if not candidates:  # if no candidates left, nothing more to do
        return old_new_pairs

    for i, new_author in enumerate(new_authors):
        if old_new_pairs[i][0] is not None:  # already found a match
            continue
        # (4) Backup solution to use next available author in the list
        if candidates:
            first, last = new_author.first, new_author.last
            # can lead to errors: print a warning unless either first or last matches
            pos = min(candidates.keys())
            backup_ns = candidates[pos][0]
            b_f, b_l = backup_ns.first, backup_ns.last
            if b_f != first and b_l != last:
                log.debug(
                    f"  Potentially dangerous node selection for "
                    f"'{first}  {last}': '{b_f}  {b_l}'",
                )
            assert old_new_pairs[i][1] == new_author
            old_new_pairs[i] = (backup_ns, new_author)
            del candidates[pos]
            continue

    return old_new_pairs


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

        self.load_anthology()

    def load_anthology(self):
        self.anthology = Anthology.from_within_repo(verbose=self.verbose)
        # self.anthology.load_all()  # not needed to load_all?

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
        if not isinstance(json_block, dict):
            log.warning("-> JSON data has unexpected type (expect dict)")
            return False

        if ik := [k for k in json_block if k not in allowed_keys]:
            log.warning(f"-> Invalid keys in JSON: {ik}")
            return False

        if ANTHOLOGY_ID not in json_block:
            log.warning(f"-> Key not found: {ANTHOLOGY_ID}")

        # need to have at least one of abstract, title or authors
        if not any([AUTHORS in json_block, TITLE in json_block, ABSTRACT in json_block]):
            log.warning(
                f"-> Nothing to change: need to provide at least one of "
                f"'{AUTHORS}', '{ABSTRACT}', '{TITLE}'."
            )
            return False

        # author list need to be a list of dicts with certain keys
        if AUTHORS in json_block:
            if not isinstance(json_block[AUTHORS], list):
                log.warning("-> Invalid format for author list: expect list")
                return False
            if len(json_block[AUTHORS]) == 0:
                log.warning("-> Empty list of authors")
                # return False
            for author in json_block[AUTHORS]:
                if not isinstance(author, dict):
                    log.warning("-> Invalid format for individual author: expect dict")
                    return False
                if not author.get(AUTHOR_LAST):
                    log.warning(f"-> Author has no last name: {author}")
                    if not author.get(AUTHOR_FIRST):
                        log.warning("-> Author has no first name too: cannot continue")
                        return False
                    log.warning(
                        f"-> No last name provided "
                        f"- will use first name instead: '{author[AUTHOR_FIRST]}'"
                    )
                    author[AUTHOR_LAST] = author[AUTHOR_FIRST]
                    author[AUTHOR_FIRST] = None  # todo: test this
                if ak := [k for k in author.keys() if k not in author_keys]:
                    log.warning(f"-> Invalid author keys: {ak}")

        # warn if author list contradicts info in authors_new
        if NEW_AUTHORS in json_block or OLD_AUTHORS in json_block:
            if not (
                AUTHORS in json_block
                and NEW_AUTHORS in json_block
                and OLD_AUTHORS in json_block
            ):
                log.warning(
                    f"-> either just {AUTHORS} or plus both {OLD_AUTHORS} and {NEW_AUTHORS}"
                )
            else:
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

    def _get_namespec_from_changes(self, changes: dict) -> List[NameSpecification]:
        """Convert the JSON-derived author list into  List of NameSpecifications"""
        # we don't process orcid, affiliations, variants right now
        assert AUTHORS in changes, "Don't call this method if no authors to change"
        namespecs = list()

        for author in changes[AUTHORS]:
            # author is assumed to be dict with ['first', 'last', 'id'] as keys (potentially omitted/empty)
            # NameSpecification/Name do distinguish '' and None, while I'd like None for both
            # NameSpecification won't complain if id is not known to the index
            # todo: test all cases
            if not author.get(AUTHOR_ID):
                author[AUTHOR_ID] = None
            assert author.get(AUTHOR_LAST), "Already performed input validation"
            if not author.get(AUTHOR_FIRST):
                author[AUTHOR_FIRST] = None

            ns = NameSpecification(id=author[AUTHOR_ID], name=Name.from_dict(author))
            namespecs.append(ns)

        return namespecs

    def _merge_namespecs(
        self, existing_author: Optional[NameSpecification], new_author: NameSpecification
    ) -> NameSpecification:
        """
        Return NameSpecification merging information from both arguments

        Prefers to keep all information from existing_author if present. If there is no
        existing author, will return new author, but with id set to None to not write
        any ids to XML. Mainly updates author name of existing author (this may
        introduce a new name variant to a verified author).
        """
        # todo simplify logic below if possible (after questions answered)
        if existing_author is None:
            # no existing author, so no need to copy over information like orcid etc.
            # Should we allow submitters to assign an ID, rather than the library figuring it out?
            # The library will usually assign unverified (disable matching true or name not known),
            # unless there is a single, verified person... but even then no explicit id needed?
            # -> Decide to set to None
            if new_author.id is not None and is_verified_person_id(new_author.id):
                # Only notify if provided id is known in principle, but is not the one
                # that will show up after correction: happens if EITHER name lookup
                # yielded multiple persons OR one person but with different id
                pp = self.anthology.find_people(new_author.name)
                if len(pp) > 1 or (len(pp) == 1 and pp.pop().id != new_author.id):
                    log.debug(
                        f"-> Will not consider provided id {new_author.id} "
                        f"for newly inserted author {new_author.name}."
                    )
            # -> Decision None
            new_author.id = None
            return new_author

        # else:  # has old author info to compare to
        if existing_author.name == new_author.name:  # shortcut for authors not changed
            return existing_author  # we don't allow id-only changes
        # use existing NameSpec and only change where necessary, definitely change name
        p = self.anthology.resolve(existing_author)
        assert isinstance(
            p, Person
        ), "Existing author initially retrieved from anthology, so p cannot be a list"

        existing_author.name = new_author.name
        if existing_author.orcid is not None or p.is_explicit:
            # for verified authors only allow name change - no need to update id
            name = new_author.name
            if not p.has_name(name):
                log.info(
                    f"-> Added new name variant '{name}' to {p.id} ({p.canonical_name})"
                )
                p.add_name(name)
                # todo: is this enough? do I have to check for newly introduced namesakes?
            if new_author.id is not None and new_author.id != p.id:
                log.debug(
                    f"-> ID mismatch between asked ({new_author.id}) and final decision ({p.id})"
                )
        else:  # unverified old author
            existing_author.id = None
            # if new name not known to anthology and old was unverified anyway:
            # - no need to add id
            # if new name is ambiguous: don't do disambiguation that way
            # - submitter maybe hasn't intended disambiguation, isn't aware of ambiguity
            # if new name belongs to exactly one known person
            # - unverified: no id in XML anyway. verified: no need for id in XML
        return existing_author

    def _update_paper_authors(self, paper: Paper, changes: dict) -> Paper:
        """
        Update authors of the paper as specified by changes

        Keep existing data where possible (e.g. affiliation, orcid etc).
        """
        assert AUTHORS in changes, "Only call this method, if authors-key in JSON block"

        # (1) Convert new author list into NameSpecifications, match authors to existing
        new_authors = self._get_namespec_from_changes(changes)  # can raise ValueError?
        old_new_matched = match_old_to_new_authors(paper, new_authors, self.anthology)

        # (2) Collect final list of authors - updating information where necessary
        # Copying over non-changed, existing attributes from old_author if available
        final_authors = list()  # can simplify to list comprehension after debugging
        for existing_author, new_author in old_new_matched:
            author = self._merge_namespecs(existing_author, new_author)
            final_authors.append(author)

        # (3) Finally we replace the old list of authors/editors with the new one
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
            except Exception as e:
                log.warning(f"Error processing issue {issue.number}: {type(e)}: {e}")
                log.exception(e)
                # If we land here, we should carefully monitor file states and git status
                continue

        if len(closed_issues) > 0 and not dry_run:
            self._create_pull_request(closed_issues, new_branch_name, today)
            pass

        # Switch back to original branch
        self.local_repo.head.reference = current_branch
        self.local_repo.head.reset(index=True, working_tree=True)
        self.local_repo.git.stash(["pop"])

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
        # base_branch = self.local_repo.head.reference
        base_branch = self.local_repo.heads.master

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
