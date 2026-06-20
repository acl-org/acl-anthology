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
            return {}

        orcid_data = content.get("orcid")

        if orcid_data:
            # Handle API response formatting variants
            # (API v2 wrapper schemas often enclose custom metadata targets inside a {'value': ...} wrapper)
            if isinstance(orcid_data, dict):
                orcid_link = orcid_data.get("value")
            else:
                orcid_link = orcid_data

            orid2orcid[profile.id] = orcid_link
            # TODO: what about aliases? look at profile.referent?

    return orid2orcid


TEST_CASES = [
    ("2025.emnlp-main.8", "Jandaghi", "~Pegah_Jandaghi1"),
    ("2025.acl-demo.60", "Zhuocheng", "~Zhang_Zhuocheng1"),
    ("2023.findings-emnlp.773", "Zhuocheng", "~Zhang_Zhuocheng1"),
    ("2025.findings-emnlp.679", "Rezaei", "~Mohammad_Reza_Rezaei1"),
]
# TODO: test a legacy-verified author


def refresh_or_orcids(username=None, password=None):
    anthology = Anthology.from_within_repo()

    user2nses = defaultdict(list)
    if TEST_CASES:  # TODO: temporary
        for itemid, lastname, user in TEST_CASES:
            paper = anthology.get(itemid)
            assert isinstance(paper, Paper)
            for ns in paper.namespecs:
                if ns.last == lastname:
                    user2nses[user].append(ns)
    else:
        for vol in anthology.volumes():
            if int(vol.year) >= EARLIEST_YEAR_WITH_OR_IDS:
                for ns in vol.namespecs:
                    if ns.orcid is None and ns.openreviewid is not None:
                        user2nses[ns.openreviewid].append(ns)

    orid2orcid = get_user_orcids(list(user2nses), username=username, password=password)
    if not orid2orcid:
        log.info("No new ORCIDs found.")
    else:
        log.info(f"{len(orid2orcid)} new ORCIDs found.")
        numUpdatedNSes = 0
        for user, orcid in orid2orcid.items():
            log.debug(f"{user}: {orcid}")
            person = anthology.people.get_by_orcid(orcid)
            # check if any namespecs have an explicit ID (could be a legacy-verified person)
            explicit_ids = set(ns.id for ns in user2nses[user])
            assert len(explicit_ids) < 2, (
                f"OR ID is associated with multiple explicit Anthology people: {explicit_ids}"
            )
            if explicit_ids:
                (explicit_id,) = explicit_ids
                person = anthology.get_person(explicit_id)

            if person is None:
                log.debug("Will create a new verified person")
            else:
                log.debug(f"Found: {person.id}, current ORCID: {person.orcid}")
                if person.orcid is None:
                    person.orcid = orcid

            for ns in user2nses[user]:
                numUpdatedNSes += 1
                if person is None:
                    # log.debug("Creating a new verified person")
                    new_aid = anthology.people.generate_person_id(ns.name, orcid=orcid)
                    person = anthology.people.create(
                        new_aid,
                        [ns.name] + list(ns.variants),
                    )
                assert ns.id is None or ns.id == person.id, ns.id
                ns.id = person.id
                ns.orcid = orcid
        log.info(f"{numUpdatedNSes} NameSpecs updated with ORCID.")
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
