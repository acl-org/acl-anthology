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

  To add papers under a verified author: all papers currently associated with the listed author(s)
  are explicitly mapped to the target author (merging the author pages).
  If listing multiple author IDs, the first will be used for the canonical name,
  and subsequent ones must be unverified.

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


def _construct_new_person_id(anthology, current_matching_person, name, suffix):
    new_aid = name.slugify()
    if current_matching_person.id.endswith('/unverified'):
        assert new_aid == current_matching_person.id.replace('/unverified', '')
    if current_matching_person.id == new_aid or anthology.get_person(new_aid) is not None:
        log.info(f'The author ID {new_aid} already exists; using suffix')
        assert suffix is not None
        new_aid += '-' + suffix
        assert (
            anthology.get_person(new_aid) is None
        ), f'Even with suffix the author ID exists: {new_aid}'
    return new_aid


def _unverified_person_convert_to_verified(anthology, person, suffix, has_degree):
    """An unverified author page should be converted to a verified page.
    Makes an existing unverified Person verified (and all the papers on the page
    will be explicitly linked)."""
    assert has_degree, 'To newly verify an author we need a degree institution'
    assert person.id.endswith('/unverified'), person.id
    new_aid = _construct_new_person_id(anthology, person, person.names[0], suffix)

    # Convert unverified person to verified, which assigns IDs to all papers under the unverified person
    log.info(f'Verifying author {person.id} -> {new_aid}')
    person.make_explicit(new_aid)


def _implicit_person_to_new_verified(anthology, person, name, suffix, has_degree):
    """A paper is being split off from an implicitly matched (verified or unverified) Person's page.
    Create a new verified Person for this paper (or group of papers)."""
    assert has_degree, 'To newly verify an author we need a degree institution'
    assert name in person.names
    new_aid = _construct_new_person_id(anthology, person, name, suffix)

    # Make a brand new person with the name
    log.info(f'Verifying author from scratch: {new_aid}')
    new_person = anthology.people.create(new_aid, [name])
    return new_person


def verify_all(orcid, author_ids, degree=None, suffix=None, except_paper_ids=None):
    changes = False
    anthology = Anthology.from_within_repo()
    assert is_valid_orcid(orcid), f'Invalid ORCID iD: {orcid}'
    assert len(set(author_ids)) == len(author_ids), 'Author IDs should be unique'

    # First try to match an existing person by ORCID
    person = anthology.people.get_by_orcid(orcid)
    if person is None:
        # No ORCID match. Match canonical person by first author ID instead.
        aid = author_ids[0]
        person = anthology.get_person(aid)
        assert person is not None, f'Unregistered author ID: {aid}'
        if not person.is_explicit:
            # First provided author ID is an unverified author. Convert to a verified author.
            _unverified_person_convert_to_verified(
                anthology, person, suffix=suffix, has_degree=degree is not None
            )
            changes = 'Verify'

            # reset the ID for excluded papers
            if except_paper_ids:
                for paper_id in except_paper_ids:
                    paper = anthology.get(paper_id)
                    assert paper is not None, f'Paper not found: {paper_id}'
                    matching_authors = [ns for ns in paper.authors if ns.id == person.id]
                    assert (
                        matching_authors
                    ), f'Cannot exclude paper {paper_id} because it was not matched in the first place'
                    for ns in matching_authors:
                        log.info(f'Excluding paper {paper_id} author {ns}')
                        ns.id = None
                        paper.collection.is_modified = True

                # since we are verifying an unverified person and there are excluded papers,
                # disable name matching
                log.info('Disabling name matching to limit to the specified papers.')
                person.disable_name_matching = True
                changes = (
                    changes + ' and disable name matching for'
                    if changes
                    else 'Disable name matching for'
                )
        else:
            log.info(f'Matched existing author by author ID: {aid}')

        # We did not find an ORCID match, so assign the provided ORCID to the first matched author ID
        assert (
            not person.orcid
        ), f'Author {aid} already has an ORCID {person.orcid} which differs from {orcid}'
        log.info('Assigning ORCID')
        person.orcid = orcid
        changes = 'Verify'

        # We have used the first of the provided author IDs
        author_ids = author_ids[1:]
    else:
        log.info('Matched existing author by ORCID')

    # Specify the degree institution if provided
    if degree is not None:
        if person.degree:
            assert (
                person.degree == degree
            ), f'Mismatched degree institution: "{person.degree}" != "{degree}"'
        else:
            log.info('Assigning degree institution')
            person.degree = degree
            if not changes:
                changes = 'Add degree for'

    # Merge specified author IDs with the canonical person
    # Note that we may have already used the first author ID
    for aid in author_ids:
        person2 = anthology.get_person(aid)
        assert person2 is not None, f'Invalid author ID: {aid}'
        if person2 is person:  # ORCID match may be the same as first author ID match
            if len(author_ids) == 1 and (not changes or changes == 'Add degree for'):
                # Author is already verified with ORCID; make_explicit() has not been called
                # and merge_with_explicit() will not be called.
                # Interpret as a request to make this author's ID fully explicit on papers.
                log.info(f'Ensuring author ID {aid} is explicit on all papers/volumes')
                # TODO: this is clunky; there ought to be better API support for this
                candidate_namespecs = [
                    (ns, paper) for paper in person.papers() for ns in paper.authors
                ]
                candidate_namespecs += [
                    (ns, volume) for volume in person.volumes() for ns in volume.editors
                ]
                for paper_id in except_paper_ids or []:
                    paper = anthology.get(paper_id)
                    assert paper is not None, f'Paper not found: {paper_id}'
                for namespec, item in candidate_namespecs:
                    if anthology.resolve(namespec) is person:
                        if namespec.id:
                            assert namespec.id == person.id
                        elif item.full_id in (except_paper_ids or []):
                            log.info(f'Excluding paper {item.full_id}')
                        else:
                            namespec.id = person.id
                            item.collection.is_modified = True
                            changes = 'Verify'
            continue

        # Besides the canonical person, other author IDs to merge should be unverified
        # (else it means two author IDs corresponding to the same individual were erroneously verified)
        assert (
            not person2.is_explicit
        ), f'Author ID corresponds to a verified author, should be unverified: {aid}'
        log.info(f'Merging author {aid} into {person.id}')
        except_papers = []
        for paper_id in except_paper_ids or []:
            paper = anthology.get(paper_id)
            assert paper is not None, paper_id
            assert paper.authors, paper
            assert not any(
                ns.id == person.id
                for ns in (paper.authors if isinstance(paper, Paper) else paper.editors)
            ), f'Excluded paper {paper_id} already specifies the author ID {person.id}'
            log.info(f'Temporarily adding paper {paper_id}, will exclude later')
            except_papers.append((paper_id, paper))
        person2.merge_with_explicit(person)
        anthology.save_all()
        anthology.people.reset()

        # reset the ID for excluded papers
        for paper_id, paper in except_papers:
            paper = anthology.get(paper_id)  # reload the paper (to avoid stale NameSpecs)
            matching_authors = [ns for ns in paper.authors if ns.id == person.id]
            assert (
                matching_authors
            ), f'Cannot exclude paper {paper_id} because it was not matched in the first place'
            for ns in matching_authors:
                log.info(f'Excluding paper {paper_id} author {ns}')
                ns.id = None
                paper.collection.is_modified = True
        changes = 'Verify/merge'

    if changes:
        anthology.save_all()
    else:
        changes = 'No changes for'

    return changes + f' author {person.id}'


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
            assert (
                paper_and_name_slug.count(':') == 1
            ), 'First arg after ORCID must be PAPERID:NAMESLUG'
        else:
            assert (
                paper_and_name_slug.count(':') <= 1
            ), f'Invalid arg syntax: {paper_and_name_slug}'
        paper_id, name_slug = (paper_and_name_slug + ':').split(':', 1)
        if name_slug:
            name_slug = name_slug.replace(':', '')
            assert name_slug, name_slug
            assert is_verified_person_id(
                name_slug
            ), f'Name slug must have the form of a verified person ID (not including /unverified): {name_slug}'
            name_slug_queries.add(name_slug)
        paper = anthology.get(paper_id)

        # match the author of the paper by name slug
        author_list = paper.authors if isinstance(paper, Paper) else paper.editors
        query = [name_slug] if name_slug else name_slug_queries
        matches = [
            namespec for namespec in author_list if namespec.name.slugify() in query
        ]
        assert (
            len(matches) == 1
        ), f'In {paper_id}, looking for exactly 1 author matching one of {query}, found: {matches}'
        matched_namespec = matches[0]
        log.info(f'In {paper_id}, matched author {matched_namespec.name}')
        paper_and_namespec.append((paper, matched_namespec))

    assert is_valid_orcid(orcid), f'Invalid ORCID iD: {orcid}'

    # Try to match an existing person by ORCID
    # (requires loading the person index, so do this after other validation)
    person = anthology.people.get_by_orcid(orcid)
    orcid_matched = person is not None
    explicit_verified_matches = [
        namespec for (_, namespec) in paper_and_namespec if namespec.id
    ]
    if person is None:
        # No ORCID match. Look for a verified person among the matched namespecs
        assert (
            len(explicit_verified_matches) <= 1
        ), f'Expected at most 1 explicit verified author match in specified papers, got: {explicit_verified_matches}'
        if explicit_verified_matches:
            assert (
                not only_these_papers
            ), '`--only` flag does not work with an already-verified author'
            # TODO: replace with new .resolve()
            person = anthology.resolve(explicit_verified_matches[0])
    else:
        assert (
            not only_these_papers
        ), '`--only` flag does not work with an already-verified author'
        assert (
            len(explicit_verified_matches) == 0
        ), f'Expected no explicit verified author matches in specified papers, got: {explicit_verified_matches}'

    if person is None:
        # Create new verified person
        implicit_person = anthology.resolve(paper_and_namespec[0][1])
        person = _implicit_person_to_new_verified(
            anthology,
            implicit_person,
            paper_and_namespec[0][1].name,
            suffix=suffix,
            has_degree=degree is not None,
        )
        for _, ns in paper_and_namespec[:1]:
            # Add any names from other papers (which may correspond to other unverified persons)
            person.add_name(ns.name)
        del implicit_person
        changes = 'Verify'

    if not orcid_matched:
        # We did not find an ORCID match, so assign the provided ORCID to the first matched author ID
        assert (
            not person.orcid
        ), f'Author {person.id} already has an ORCID {person.orcid} which differs from {orcid}'
        log.info('Assigning ORCID')
        person.orcid = orcid

    # Specify the degree institution if provided
    if degree is not None:
        if person.degree:
            assert (
                person.degree == degree
            ), f'Mismatched degree institution: "{person.degree}" != "{degree}"'
        else:
            log.info('Assigning degree institution')
            person.degree = degree
            changes = 'Verify'

    # Now add papers under the person (or in other words, specify person ID in namespecs for listed papers)
    for paper, ns in paper_and_namespec:
        if not ns.id:
            ns.id = person.id
            paper.collection.is_modified = True  # TODO: remove after API change
            changes = 'Verify'
        else:
            assert ns.id == person.id, (ns.id, person.id)
    log.info(
        f'The specified {len(paper_and_namespec)} papers have been explicitly assigned to the author'
    )

    if changes:
        anthology.save_all()

    anthology.people.reset()
    person = anthology.get_person(person.id)  # refreshed after reset

    numPapers = len(list(person.anthology_items()))
    if only_these_papers and not person.disable_name_matching:
        log.info(f'This person now has {numPapers} papers.')
        if numPapers > len(paper_and_namespec):
            # There are papers that would appear under this author by name match but should not
            log.info('Disabling name matching to limit to the specified papers.')
            person.disable_name_matching = True
            changes = (
                changes + ' and disable name matching for'
                if changes
                else 'Disable name matching for'
            )
    else:
        log.info(f'This person now has {numPapers} papers')

    if changes:
        anthology.save_all()
        anthology.people.reset()
    else:
        changes = 'No changes for'

    if not person.disable_name_matching:
        # Check that there are no more implicit matches
        person = anthology.get_person(person.id)  # refreshed after reset
        log.info(f'Checking that author ID {person.id} is explicit on all papers/volumes')
        # TODO: this is clunky; there ought to be better API support for this
        candidate_namespecs = [
            (ns, paper) for paper in person.papers() for ns in paper.authors
        ]
        candidate_namespecs += [
            (ns, volume) for volume in person.volumes() for ns in volume.editors
        ]
        for namespec, item in candidate_namespecs:
            if anthology.resolve(namespec) is person:
                assert (
                    namespec.id == person.id
                ), f'Implicit match (did you mean to run with --only?): {item}'

    return changes + f' author {person.id}'


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG if not args.get("--quiet", False) else log.INFO
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    with warnings.catch_warnings(action="ignore", category=NameSpecResolutionWarning):
        if args['AUTHORID']:
            if any(
                ':' in x for x in args['AUTHORID']
            ):  # this is actually paperID:nameslug
                args['PAPERID:NAMESLUG'] = args['AUTHORID']
                args['AUTHORID'] = None
            else:
                msg = verify_all(
                    orcid=args['ORCID'],
                    author_ids=args['AUTHORID'],
                    degree=args['--degree'],
                    suffix=args['--suffix'],
                    except_paper_ids=(
                        args['--except'].split() if args['--except'] else None
                    ),
                )

        if not args['AUTHORID']:
            assert args['PAPERID:NAMESLUG'], args
            msg = verify_by_paper(
                orcid=args['ORCID'],
                paper_ids=args['PAPERID:NAMESLUG'],
                degree=args['--degree'],
                suffix=args['--suffix'],
                only_these_papers=args['--only'],
            )

        if args['--issue']:
            msg += f' (closes #{args["--issue"]})'
        print(f'Now run>>> git commit -a -m "{msg}"')
