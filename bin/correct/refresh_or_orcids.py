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
For NameSpecs that list an OpenReview ID but not an ORCID iD,
query OpenReview to see if that profile now has an ORCID iD.
If so, add it to the database, verifying the author if not already verified.

See also fetch_orcid_from_openreview.py, which applies to a single user.
"""

from collections import defaultdict
import openreview
from openreview import Profile
import openreview.api
import logging as log
import os
import warnings
from acl_anthology import Anthology
from acl_anthology.collections import Paper
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.utils.logging import setup_rich_logging

EARLIEST_YEAR_WITH_OR_IDS = 2026


def get_user_orcids(ids: list, version=2, username=None, password=None) -> dict[str, str]:
    """
    Queries the OpenReview API for a user profile and returns their ORCID link.

    Parameters:
        email_or_id (str): The user's registered email or OpenReview ID (e.g., '~Michael_Spector1').
        version (int): API version to use (1 for legacy, 2 for modern v2). Default is 2.
        username (str, optional): Your OpenReview login email/username if authentication is needed.
        password (str, optional): Your OpenReview login password.

    Returns:
        str: The ORCID URL or ID if found, otherwise None.
    """
    # Establish the appropriate base URL
    baseurl = (
        "https://api2.openreview.net" if version == 2 else "https://api.openreview.net"
    )

    log.info(f"Connecting to OpenReview API v{version}...")

    try:
        # Initialize the client. Public data can generally be read using Guest access (no credentials).
        assert version == 2
        client = openreview.api.OpenReviewClient(
            baseurl=baseurl, username=username, password=password
        )
    except Exception as e:
        log.error("Initialization Error:")
        log.exception(e)
        return {}

    log.info(f"Retrieving profile for: {len(ids)} users: first 10 are {ids[:10]}")

    # Safely look up the profile via openreview.tools (returns None instead of throwing an error if missing)
    profiles = openreview.tools.get_profiles(client, ids)

    if not profiles:
        log.error("No profiles returned.")
        return {}

    orid2orcid = {}
    for profile in profiles:
        assert isinstance(profile, Profile)

        # OpenReview profile metadata is stored under the 'content' dictionary
        content = profile.content
        if not content:
            log.error("No profile content")
            continue

        orcid_data = content.get("orcid")

        if orcid_data:
            # Handle API response formatting variants
            # (API v2 wrapper schemas often enclose custom metadata targets inside a {'value': ...} wrapper)
            if isinstance(orcid_data, dict):
                orcid_link = orcid_data.get("value")
            else:
                orcid_link = orcid_data

            names = profile.content[
                "names"
            ]  # all the user's names including each username
            # one of these usernames will be the queried ID (profile.id is the canonical one,
            # which may be different from the preferred name)
            for name in names:
                if (u := name["username"]) in ids:
                    # index the ORCID under the queried username
                    orid2orcid[u] = orcid_link
                    break
            else:
                assert False, names

    return orid2orcid


# TEST_CASES = [
#     ("2025.emnlp-main.8", "Jandaghi", "~Pegah_Jandaghi1"),
#     ("2025.acl-demo.60", "Zhuocheng", "~Zhang_Zhuocheng1"),
#     ("2023.findings-emnlp.773", "Zhuocheng", "~Zhang_Zhuocheng1"),
#     ("2025.findings-emnlp.679", "Rezaei", "~Mohammad_Reza_Rezaei1"),
# ]
# TODO: test a legacy-verified author


def refresh_or_orcids(username=None, password=None):
    anthology = Anthology.from_within_repo()

    user2nses = defaultdict(list)
    nORCIDOnly, nOROnly, nBoth, nNeither = 0, 0, 0, 0
    nVols = 0
    for vol in anthology.volumes():
        if int(vol.year) >= EARLIEST_YEAR_WITH_OR_IDS:
            nVols += 1
            for paper in vol.papers():
                for ns in paper.namespecs:
                    if ns.orcid is None and ns.openreview is not None:
                        user2nses[ns.openreview].append(ns)
                        nOROnly += 1
                    elif ns.orcid is None:
                        nNeither += 1
                    elif ns.openreview is not None:
                        nBoth += 1
                    else:
                        nORCIDOnly += 1
    del vol
    log.info(
        f"In {nVols} target volumes, {nOROnly} namespecs with openreview but not orcid, {nORCIDOnly} with orcid but not openreview, {nBoth} with both, {nNeither} with neither"
    )

    orid2orcid = get_user_orcids(list(user2nses), username=username, password=password)
    if not orid2orcid:
        log.info("No new ORCIDs found.")
    else:
        log.info(f"{len(orid2orcid)} new ORCIDs found.")
        numUpdatedNSes = 0
        numUpdatedNSesByVolume = defaultdict(int)
        numNSErrors = 0
        numNewPerson = 0
        for user, orcid in orid2orcid.items():
            log.debug(f"{user}: {orcid}")
            bare_orcid = orcid.split("/")[-1]
            person = anthology.people.get_by_orcid(bare_orcid)
            # assert user!="~Yuxi_Sun7",(orcid,bare_orcid,person is None)
            # check if any namespecs have an explicit ID (could be a legacy-verified person)
            explicit_ids = set(ns.id for ns in user2nses[user] if ns.id is not None)
            assert len(explicit_ids) < 2, (
                f"OR ID is associated with multiple explicit Anthology people: {explicit_ids}"
            )
            if explicit_ids:
                (explicit_id,) = explicit_ids
                person = anthology.get_person(explicit_id)

            if person is None:
                log.debug("...will create a new verified person")
            else:
                log.debug(f"...found: {person.id}, current ORCID: {person.orcid}")
                if person.orcid is None:
                    person.orcid = orcid

            for ns in user2nses[user]:
                if person is None:
                    # log.debug("Creating a new verified person")
                    new_aid = anthology.people.generate_person_id(ns.name, orcid=orcid)
                    person = anthology.people.create(
                        new_aid,
                        [ns.name] + list(ns.variants),
                    )
                    numNewPerson += 1
                assert ns.id is None or ns.id == person.id, ns.id
                person.add_name(ns.name)
                ns.id = person.id
                try:
                    ns.orcid = orcid
                    person.orcid = orcid
                    numUpdatedNSes += 1
                    paper = ns.parent
                    assert isinstance(paper, Paper)
                    numUpdatedNSesByVolume[paper.parent.full_id] += 1
                except ValueError:
                    log.error(f"ORCID is invalid: {orcid} for {user}")
                    numNSErrors += 1
        log.info(f"{numNewPerson} new Persons created.")
        log.info(f"{numUpdatedNSes} NameSpecs updated with ORCID.")
        log.info(numUpdatedNSesByVolume)
        log.info(f"{numNSErrors} NameSpecs could not be updated due to an error.")
        anthology.save_all()


if __name__ == "__main__":
    tracker = setup_rich_logging(level=log.DEBUG)

    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    with warnings.catch_warnings(action="ignore", category=NameSpecResolutionWarning):
        username = os.getenv("OR1")
        password = os.getenv("OR2")
        refresh_or_orcids(username=username, password=password)
