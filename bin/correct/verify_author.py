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
Verifies an author with an ORCID iD and all or a subset of items on one or more author pages.

If the ORCID iD is already in the system under a verified author,
any listed unverified pages will be merged with that page.

All papers on the final verified author page will be explicitly marked
with the author ID (even if the author is already verified and
implicitly associated with all the right papers).


Usage:
  verify_author.py [--issue NUM | --no-commit] [--degree DEGREE] [--suffix SUFFIX] [--except PAPERIDs] ORCID AUTHORID ...
  verify_author.py [--issue NUM | --no-commit] [--degree DEGREE] [--suffix SUFFIX] [--only] ORCID PAPERID:NAMESLUG ...

verify_author.py [--issue NUM | --no-commit] [--degree DEGREE] [--suffix SUFFIX] ORCID AUTHORID ...

  Merges the author pages corresponding to the provided author IDs
  into a (new or existing) verified page with an ORCID.
  Papers under this verified Person will all have explicit author IDs.
  If listing multiple author IDs, the first will be used for the canonical name.

verify_author.py [--issue NUM | --no-commit] [--degree DEGREE] [--suffix SUFFIX] [--only] ORCID PAPERID:NAMESLUG ...

  To add specified papers under a verified author (the target author).
  Currently, the specified papers are under an unverified author, or implicitly matched to a verified author
  with a similar name.
  If target author is not yet verified, the name from the first listed paper will be used as the canonical name.
  If target author is verified but ORCID is not in the database yet, at most one of the specified
  papers can be a paper already linked to this author.
  With `--only`, ensures that only these papers will appear on the new author page;
  if there are other papers that would be matched based on name alone, implicit matching will be disabled
  for the author. `--only` is not an option if the author is already verified.

Arguments:
    ORCID               ORCID iD of the author. May already be associated with a verified person in the database.
    AUTHORID            One or more author IDs to associate with the ORCID iD and merge
                        as a single person in the database. If a verified person in the database
                        already has this ORCID iD, listing that author ID is optional.
                        If none of the author IDs are currently verified, the first one listed
                        will be the source of the verified author's canonical name.
    PAPERID             Paper or volume to include under the verified author.
    NAMESLUG            Slug representing a name in the paper's author list that corresponds to this author.
                        Required for the first specified paper. If omitted on any subsequent papers,
                        the earlier specified name slugs will be tried.

Options:
    -h --help           Show this help message.
    --issue NUM         GitHub issue number to include in commit message.
    --degree DEGREE     Full name of the author's highest degree institution.
                        Required if a new author ID is being created.
    --suffix SUFFIX     Disambiguating suffix (usually abbreviated from the degree institution).
                        Required if a new author ID is being created and the plain name slug is already in use.
    --only              Create a newly verified author for only the specified papers;
                        other papers should not be matched by name.
    --except PAPERIDS   Assign to this author all papers on selected pages except the ones listed here.
"""

import warnings
import logging as log
from docopt import docopt


from acl_anthology import Anthology
from acl_anthology.collections import Paper
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.utils.ids import is_valid_orcid, is_verified_person_id
from acl_anthology.utils.logging import setup_rich_logging


def verify_by_author_id(
    orcid, author_ids, degree=None, suffix=None, except_paper_ids=None
):
    """
    Merges the author pages corresponding to the provided author IDs
    into a (new or existing) verified page with an ORCID.
    Papers under this verified Person will all have explicit author IDs.

    The logic is as follows: given one or more author IDs, identifies
    - the target Person to be used for verification/merging
    - the primary Person, whose canonical name will be made canonical for the result.
    These are typically the same Person, but not necessarily.
    The primary Person is determined based on the first listed author ID.
    The target Person is selected among the ones denoted by listed author IDs according to the priority:
        existing legacy-verified > existing ORCID-verified > primary Person (who may be unverified)
    (legacy-verified is preferred because this ID was created manually, whereas the ORCID-verified
    one may have been autocreated and have an ORCID-based suffix).
    """
    changes = False
    anthology = Anthology.from_within_repo()
    assert is_valid_orcid(orcid), f"Invalid ORCID iD: {orcid}"
    assert author_ids, "At least 1 author ID is required"
    assert len(set(author_ids)) == len(author_ids), "Author IDs should be unique"

    # TODO: not tested:
    #   * changing the canonical name of the target Person
    #   * merging 2 verified profiles
    # TODO: if merging an unverified Person with an author with ORCID-based suffix,
    # strip the suffix to leave the bare name slug as ID if not already taken?
    # (Not sure this ever occurs in practice because ORCID suffix was only added if necessary.)

    people = []
    for aid in author_ids:
        person = anthology.get_person(aid)
        assert person is not None, f"Unregistered author ID: {aid}"
        people.append(person)
    person = anthology.people.get_by_orcid(orcid)
    if person is not None and person not in people:
        people.append(person)
    del person

    # count how many items have explicit IDs
    numExplicit = 0  # items initially with an explicit author ID
    for person in people:
        numExplicit += sum(1 for ns in person.namespecs() if ns.id is not None)

    primary_person = people[0]
    target_person = (
        [p for p in people if p.is_explicit and p.orcid is None]
        + [p for p in people if p.is_explicit and p.orcid is not None]
        + [primary_person]
    )[0]

    if not target_person.is_explicit:
        # Convert unverified person to verified
        assert degree is not None, (
            "To newly verify an author we need a degree institution"
        )
        new_aid = anthology.people.generate_person_id(target_person, suffix)
        log.info(f"Verifying author {target_person.id} -> {new_aid}")

        # target_person.make_explicit(new_aid, skip_setting_ids=True)
        # workaround for bug #7879
        # new_person = anthology.people.create(new_aid, [target_person.canonical_name])
        # new_person.disable_name_matching = True  # temporarily, so authors don't get automatically moved from `target_person`
        # assert (
        #     not except_paper_ids
        # ), 'Person.merge_into() currently does not support excluding some papers'
        # target_person.merge_into(new_person)  # copy attributes, set explicit IDs
        # target_person = new_person
        # new_person.disable_name_matching = False  # reset

        # validate the excluded papers list
        for item_id in except_paper_ids or []:
            assert anthology.get(item_id).get_namespec_for(target_person).id is None, (
                f"Paper {item_id.full_id} in the exclude list does not belong to {target_person.id}"
            )

        # create verified person and set explicit IDs for all papers
        target_person.make_explicit(new_aid)

        # remove the ID for any excluded paper
        for item_id in except_paper_ids or []:
            anthology.get(item_id).get_namespec_for(target_person).id = None

        changes = "Verify/merge" if len(author_ids) > 1 else "Verify"

    canonical_name = primary_person.canonical_name

    # Merge any other Persons into the target Person
    for person in people:
        if person is not target_person:
            if person.is_explicit:
                log.info(f"Already verified, merging into another person: {person.id}")
            assert (person.orcid is None) or (target_person.orcid is None), (
                f"ORCID clash: {person.orcid}, {target_person.orcid}"
            )
            assert not except_paper_ids, (
                "Person.merge_into() currently does not support excluding some papers"
            )
            person.merge_into(target_person)
            if not changes:
                changes = "Verify/merge"
    del person

    if target_person.canonical_name != canonical_name:
        log.info(f"Using {canonical_name} as canonical")
        target_person.canonical_name = canonical_name
        # TODO: also update the ID?

    # Set ORCID
    if target_person.orcid is None:
        log.info("Assigning ORCID")
        target_person.orcid = orcid
        if not changes:
            changes = "Add ORCID for"

    # Specify the degree institution if provided
    if degree is not None:
        if target_person.degree:
            assert target_person.degree == degree, (
                f'Mismatched degree institution: "{target_person.degree}" != "{degree}"'
            )
        else:
            log.info("Assigning degree institution")
            target_person.degree = degree
            if not changes:
                changes = "Add degree for"

    msg = f"Ensuring author ID {target_person.id} is explicit on all papers/volumes"
    log.info(msg if not except_paper_ids else msg + f" except: {except_paper_ids}")

    if not changes and numExplicit < len(list(target_person.namespecs())) - len(
        except_paper_ids or []
    ):
        changes = (
            "Verify"  # simply want to set explicit IDs on all items for a verified author
        )

    target_person.set_id_on_items(exclude=except_paper_ids)

    numExplicit2 = sum(1 for ns in target_person.namespecs() if ns.id is not None)
    log.info(f"...was explicit on {numExplicit}, now explicit on {numExplicit2}:")
    log.info(
        [
            item.full_id
            for item in target_person.anthology_items()
            if item.get_namespec_for(target_person).id is not None
        ]
    )

    # If any of the excluded papers appear under the target person by implicit matching,
    # disable name matching
    for item_id in except_paper_ids or []:
        if anthology.get(item_id).get_namespec_for(target_person) is not None:
            log.info("Disabling name matching to limit to the specified papers.")
            target_person.disable_name_matching = True
            changes = (
                changes + " and disable name matching for"
                if changes
                else "Disable name matching for"
            )
            break

    if changes:
        anthology.save_all()
    else:
        changes = "No changes for"

    return changes + f" author {target_person.id}"


def verify_by_paper(orcid, paper_ids, degree=None, suffix=None, only_these_papers=False):
    """
    Links a verified author to specific papers not already explicitly associated with them,
    creating a new verified author in the process if necessary.

    The logic is as follows:
    We are given the ORCID and one or more papers to attach.
    - Paper author has explicit ID (of verified Person)
        - Author is legacy-verified (no ORCID in database): add specified ORCID, degree, and papers
        - Paper author Person has a different ORCID: ERROR (ORCID mismatch)
        - Paper author Person has the same ORCID: ERROR (nothing to do as the paper is already linked)
    - Paper author has implicit ID resolved to either a verified or unverified Person
        - Resolves to a person with matching ORCID: make the link explicit, add degree
        - Otherwise: move paper from the currently resolving Person (verified or unverified) to
          a brand new verified Person by assigning explicit ID. With `only_these_papers=True`,
          disable name matching for the new Person if not doing so would cause other papers
          to appear on the author page based on name match.

    Does not handle the case where there is already an explicit author ID on a paper that is incorrect.
    """
    changes = False
    anthology = Anthology.from_within_repo()

    assert len(paper_ids) > 0
    name_slug_queries = set()
    paper_and_namespec = []
    for paper_and_name_slug in paper_ids:
        if not paper_and_namespec:
            assert paper_and_name_slug.count(":") == 1, (
                "First arg after ORCID must be PAPERID:NAMESLUG"
            )
        else:
            assert paper_and_name_slug.count(":") <= 1, (
                f"Invalid arg syntax: {paper_and_name_slug}"
            )
        paper_id, name_slug = (paper_and_name_slug + ":").split(":", 1)
        if name_slug:
            name_slug = name_slug.replace(":", "")
            assert name_slug, name_slug
            assert is_verified_person_id(name_slug), (
                f"Name slug must have the form of a verified person ID (not including /unverified): {name_slug}"
            )
            name_slug_queries.add(name_slug)
        paper = anthology.get(paper_id)

        # match the author of the paper by name slug
        author_list = paper.authors if isinstance(paper, Paper) else paper.editors
        query = [name_slug] if name_slug else name_slug_queries
        matches = [
            namespec for namespec in author_list if namespec.name.slugify() in query
        ]
        assert len(matches) == 1, (
            f"In {paper_id}, looking for exactly 1 author matching one of {query}, found: {matches}"
        )
        matched_namespec = matches[0]
        log.info(f"In {paper_id}, matched author {matched_namespec.name}")
        paper_and_namespec.append((paper, matched_namespec))

    assert is_valid_orcid(orcid), f"Invalid ORCID iD: {orcid}"

    # Try to match an existing person by ORCID
    # (requires loading the person index, so do this after other validation)
    person = anthology.people.get_by_orcid(orcid)
    orcid_matched = person is not None
    explicit_verified_matches = [
        namespec for (_, namespec) in paper_and_namespec if namespec.id
    ]
    if person is None:
        # No ORCID match. Look for a verified person among the matched namespecs
        if explicit_verified_matches:
            person = explicit_verified_matches[0].resolve()

    # If there is an already-verified person, ensure there aren't more than one
    if person is not None:
        just_paper_ids = []
        for paper, ns in paper_and_namespec:
            just_paper_ids.append(paper.full_id)
            if ns.id:
                assert ns.id == person.id, (paper.full_id, ns.id, person.id)
        if only_these_papers:
            # ensure the already-verified person doesn't have other explicit papers
            for paper in person.anthology_items():
                assert (
                    paper.full_id in just_paper_ids
                    or paper.get_namespec_for(person).id is None
                ), (
                    f"--only was specified, but list does not include already explicit paper under author {person.id}: {paper.full_id}"
                )

    if person is None:
        # Create new verified person
        assert degree is not None, (
            "To newly verify an author we need a degree institution"
        )
        cur_person = paper_and_namespec[0][1].resolve()  # implicit match

        # A paper is being split off from an implicitly matched (verified or unverified) Person's page.
        # Create a new verified Person for this paper (or group of papers).
        # We will add the papers to the new Person later.
        if not cur_person.is_explicit:
            # Currently unverified; verify
            log.info("Verifying an unverified person for specific papers")
            # new_aid = anthology.people.generate_person_id(cur_person, suffix)
            # cur_person.make_explicit(new_aid, skip_setting_ids=True)
            # -- make_explicit() currently copies all names, but we may just want a subset of names
            # person = cur_person
        else:
            # Matches a verified person; we need to create a new verified person
            log.info("Splitting from a verified person (implicit name match)")

        new_aid = anthology.people.generate_person_id(
            paper_and_namespec[0][1].name, suffix
        )
        log.info(f"Creating new verified author: {new_aid}")
        person = anthology.people.create(
            new_aid, [paper_and_namespec[0][1].name] + paper_and_namespec[0][1].variants
        )

        for _, ns in paper_and_namespec[1:]:
            # Add any names from other papers (which may correspond to other unverified persons)
            person.add_name(ns.name)
            for variant in ns.variants:
                person.add_name(variant)  # name in different script

        changes = "Verify"

    if not orcid_matched:
        # We did not find an ORCID match, so assign the provided ORCID to the first matched author ID
        assert not person.orcid, (
            f"Author {person.id} already has an ORCID {person.orcid} which differs from {orcid}"
        )
        log.info("Assigning ORCID")
        person.orcid = orcid

    # Specify the degree institution if provided
    if degree is not None:
        if person.degree:
            assert person.degree == degree, (
                f'Mismatched degree institution: "{person.degree}" != "{degree}"'
            )
        else:
            log.info("Assigning degree institution")
            person.degree = degree
            changes = "Verify"

    # Now add papers under the person (or in other words, specify person ID in namespecs for listed papers)
    for paper, ns in paper_and_namespec:
        if not ns.id:
            ns.id = person.id
            changes = "Verify"
        else:
            assert ns.id == person.id, (ns.id, person.id)
            log.warning(
                f"Already explicitly linked to author {person.id}: {paper.full_id}"
            )
    log.info(
        f"The specified {len(paper_and_namespec)} papers have been explicitly assigned to the author"
    )

    if changes:
        anthology.save_all()

    anthology.people.reset()
    person = anthology.get_person(person.id)  # refreshed after reset

    numPapers = len(list(person.anthology_items()))
    if only_these_papers and not person.disable_name_matching:
        log.info(f"This person now has {numPapers} papers.")
        if numPapers > len(paper_and_namespec):
            # There are papers that would appear under this author by name match but should not
            log.info("Disabling name matching to limit to the specified papers.")
            person.disable_name_matching = True
            changes = (
                changes + " and disable name matching for"
                if changes
                else "Disable name matching for"
            )
    else:
        log.info(f"This person now has {numPapers} papers")

    if changes:
        anthology.save_all()
        anthology.people.reset()
    else:
        changes = "No changes for"

    if not person.disable_name_matching:
        # Check that there are no more implicit matches
        person = anthology.get_person(person.id)  # refreshed after reset
        log.info(f"Checking that author ID {person.id} is explicit on all papers/volumes")
        numNamespecs = sum(1 for ns in person.namespecs())
        numExplicit = sum(1 for ns in person.namespecs() if ns.id is not None)
        if numExplicit < numNamespecs:
            log.warning(
                f"There are {numNamespecs - numExplicit} implicit matches (did you mean to run with --only?)"
            )

    return changes + f" author {person.id}"


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG if not args.get("--quiet", False) else log.INFO
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    with warnings.catch_warnings(action="ignore", category=NameSpecResolutionWarning):
        if args["AUTHORID"]:
            if any(
                ":" in x for x in args["AUTHORID"]
            ):  # this is actually paperID:nameslug
                args["PAPERID:NAMESLUG"] = args["AUTHORID"]
                args["AUTHORID"] = None
            else:
                msg = verify_by_author_id(
                    orcid=args["ORCID"],
                    author_ids=args["AUTHORID"],
                    degree=args["--degree"],
                    suffix=args["--suffix"],
                    except_paper_ids=(
                        args["--except"].split() if args["--except"] else None
                    ),
                )

        if not args["AUTHORID"]:
            assert args["PAPERID:NAMESLUG"], args
            msg = verify_by_paper(
                orcid=args["ORCID"],
                paper_ids=args["PAPERID:NAMESLUG"],
                degree=args["--degree"],
                suffix=args["--suffix"],
                only_these_papers=args["--only"],
            )

        if args["--issue"]:
            msg += f" (closes #{args['--issue']})"
        print(f'Now run>>> git commit -a -m "{msg}"')
