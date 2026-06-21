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
Queries the OpenReview API by one or more OpenReview user IDs
and retrieves the ORCID link from the profile, if present.
With -i, looks up the specified author page issue(s) in the Anthology issue tracker
and checks the ORCID field in the issue against the OpenReview profile.
Should be called on a small number of users to avoid hitting API limits.

Usage:
  fetch_orcid_from_openreview.py ORID ...
  fetch_orcid_from_openreview.py -i ISSUE ...
"""

# Drafted with Gemini

import openreview
import openreview.api
import logging as log
from acl_anthology.utils.logging import setup_rich_logging


def get_user_orcid(email_or_id, version=2, username=None, password=None):
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
        if version == 2:
            client = openreview.api.OpenReviewClient(
                baseurl=baseurl, username=username, password=password
            )
        else:
            client = openreview.Client(
                baseurl=baseurl, username=username, password=password
            )
    except Exception as e:
        log.error("Initialization Error:")
        log.exception(e)
        return None

    log.info(
        f"Retrieving profile for: {email_or_id} / https://openreview.net/profile?id={email_or_id}"
    )

    # Safely look up the profile via openreview.tools (returns None instead of throwing an error if missing)
    profile = openreview.tools.get_profile(client, email_or_id)

    if not profile:
        log.error(f"Profile matching '{email_or_id}' could not be found.")
        return None

    # OpenReview profile metadata is stored under the 'content' dictionary
    content = profile.content
    if not content:
        log.error("No profile content")
        return None

    orcid_data = content.get("orcid")

    if not orcid_data:
        log.error(f"No ORCID entry found associated with the profile: {email_or_id}")
        return None

    # Handle API response formatting variants
    # (API v2 wrapper schemas often enclose custom metadata targets inside a {'value': ...} wrapper)
    if isinstance(orcid_data, dict):
        orcid_link = orcid_data.get("value")
    else:
        orcid_link = orcid_data

    return orcid_link


if __name__ == "__main__":
    tracker = setup_rich_logging(level=log.DEBUG)

    # Substitute with the tilde ID or email you want to test
    # target_user = "~Michael_Spector1"  # no ORCID
    target_user = "~Hao_Chen1"

    orcid_url = get_user_orcid(target_user, version=2)

    if orcid_url:
        log.info(f"Success! ORCID found: {orcid_url}")
    else:
        log.error("Could not resolve an ORCID link for this user.")
