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

from docopt import docopt
import openreview
import openreview.api
import logging as log
import os
import re
import urllib.parse
from acl_anthology.utils.logging import setup_rich_logging
from github import Github


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

    # log.info(f"Connecting to OpenReview API v{version}...")

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

    # log.info(
    #     f"Retrieving profile for: {email_or_id} / https://openreview.net/profile?id={email_or_id}"
    # )

    # Safely look up the profile via openreview.tools (returns None instead of throwing an error if missing)
    profile = openreview.tools.get_profile(client, email_or_id)

    if not profile:
        log.error(
            f"Profile matching '{email_or_id}' could not be found. It may exist but be unavailable to guest API users. Try checking manually: https://openreview.net/profile?id={email_or_id}"
        )
        return None

    # OpenReview profile metadata is stored under the 'content' dictionary
    content = profile.content
    if not content:
        # log.error("No profile content")
        return None

    orcid_data = content.get("orcid")

    if not orcid_data:
        # log.error(f"No ORCID entry found associated with the profile: {email_or_id}")
        return None

    # Handle API response formatting variants
    # (API v2 wrapper schemas often enclose custom metadata targets inside a {'value': ...} wrapper)
    if isinstance(orcid_data, dict):
        orcid_link = orcid_data.get("value")
    else:
        orcid_link = orcid_data

    return orcid_link


def parse_issue_body(issue_body: str) -> dict[str, str] | None:
    issue_body = issue_body.replace("\r\n", "\n").replace("\r", "\n")
    m = re.search(
        # r"### Author ORCID\n\n(https://orcid.org/[0-9X-]{19})\n.*### OpenReview profile page URL\n\n([^\n]+)(\n|$)",
        r"### Author ORCID\n\n(https://orcid.org/[0-9X-]{19})\n",
        issue_body,
        re.MULTILINE,
    )
    if m is None:
        return None
    orcid = m.group(1)
    m = re.search(
        r"### OpenReview profile page URL\n\n([^\n]+)",
        issue_body,
        re.MULTILINE,
    )
    if m is None:
        return None
    return {"orcid": orcid, "orurl": m.group(1)}


def check_issues(issues: list[str], github_token: str):
    """
    For each Anthology GitHub issue, check whether the listed ORCID link
    is also present at the provided OpenReview URL.
    """
    aclrepo = Github(github_token).get_repo("acl-org/acl-anthology")
    candidate_issues = aclrepo.get_issues(state="open")
    issues_by_num = {iss.number: iss for iss in candidate_issues}
    log.info(f"Found {len(issues_by_num)} open issues in repo")
    for issnum in issues:
        # Load info from issue
        issue = issues_by_num.get(int(issnum))
        if issue is None:
            log.error(f"Cannot find open issue {issnum}")
            continue
        fields = parse_issue_body(issue.body)
        if fields is None:
            log.error(f"Cannot parse ORCID and OpenReview fields from issue {issnum}")
            log.debug(issue.body)
            continue

        # Extract OR user ID from profile URL
        orurl = fields["orurl"]
        if "http" not in orurl:
            log.warning(f"Skipping issue {issnum} due to empty OpenReview URL? {orurl}")
            continue
        oridM = re.search(r"/profile\?id=(\S+)", orurl)
        assert oridM is not None, orurl
        orid = urllib.parse.unquote(oridM.group(1))

        # Extract issue's ORCID
        issorcid = fields["orcid"]
        assert issorcid is not None

        # Query OpenReview
        orcid_url = get_user_orcid(orid, version=2)

        # Compare the two ORCIDs
        if orcid_url is None:
            log.warning(f"No ORCID at {orurl} from issue {issnum}")
        elif issorcid != orcid_url:
            log.warning(
                f"ORCIDs do not match: {issorcid} in issue {issnum} vs. {orcid_url} at {orurl}"
            )
        else:
            log.debug(f"Issue {issnum} ORCIDs match")


if __name__ == "__main__":
    args = docopt(__doc__)

    tracker = setup_rich_logging(level=log.DEBUG)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    if args["ISSUE"]:
        github_token = os.getenv("GITHUB_TOKEN")
        assert github_token is not None, "Set env variable GITHUB_TOKEN to access GitHub"
        check_issues(args["ISSUE"], github_token)
    else:
        for user in args[
            "ORID"
        ]:  # e.g. "~Hao_Chen1" (has ORCID), "~Michael_Spector1" (no ORCID)
            orcid_url = get_user_orcid(user, version=2)
            if orcid_url:
                log.info(f"{user}: {orcid_url}")
            else:
                log.error(f"{user}: no ORCID link in OpenReview")
