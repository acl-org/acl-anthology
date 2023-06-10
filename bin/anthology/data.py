# -*- coding: utf-8 -*-
#
# Copyright 2019 Marcel Bollmann <marcel@bollmann.me>
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

################################################################################
# This file contains all constants and functions that have hardcoded data (such
# as URLs or journal titles) which does not come from the XML.  This is to
# provide a single file where such hardcoded data can be looked up and/or
# changed.
################################################################################

import os
import re

from typing import Tuple


# this is the canonical URL.  In contrast to all other
# URL templates, it always links to the official anthology.
CANONICAL_URL_TEMPLATE = "https://aclanthology.org/{}"

# the prefix is used in different programs and we need to set it everywhere
# We use a environment variable to set this and not have to forward the value
# through all the programs. If this does not look like the best idea, keep in mind
# that the structure is historically grown -- from 2019 to 2020 :-)
try:
    ANTHOLOGY_PREFIX = os.environ["ANTHOLOGY_PREFIX"]
except KeyError:
    ANTHOLOGY_PREFIX = "https://aclanthology.org"

ATTACHMENT_PREFIX = ANTHOLOGY_PREFIX + "/attachments"
ATTACHMENT_TEMPLATE = ATTACHMENT_PREFIX + "/{}"

PDF_LOCATION_TEMPLATE = ANTHOLOGY_PREFIX + "/{}.pdf"
PDF_THUMBNAIL_LOCATION_TEMPLATE = ANTHOLOGY_PREFIX + "/thumb/{}.jpg"

# URL template for videos
VIDEO_LOCATION_TEMPLATE = ANTHOLOGY_PREFIX + "/{}"

# URL template for handbooks Where files related to events can be found, e.g., /{2022.acl.handbook.pdf}
EVENT_LOCATION_TEMPLATE = ANTHOLOGY_PREFIX + "/{}"

# Regular expression matching full Anthology IDs
ANTHOLOGY_ID_REGEX = r"[A-Z]\d{2}-\d{4}"

# Anthology file location on server
# Defaults to ~/anthology-files
ANTHOLOGY_FILE_DIR = os.environ.get(
    "ANTHOLOGY_FILES", os.path.join(os.environ["HOME"], "anthology-files")
)

# Names of XML elements that may appear multiple times, and should be accumulated as a list
LIST_ELEMENTS = (
    "attachment",
    "author",
    "editor",
    "video",
    "revision",
    "erratum",
    "award",
    "pwcdataset",
    "video",
    "venue",
)

# Names of XML elements that should not be parsed, so that they can be interpreted later in
# a context-specific way
DONT_PARSE_ELEMENTS = (
    "abstract",
    "title",
    "booktitle",
)

# New-style IDs that should be handled as journals
JOURNAL_IDS = ("cl", "tacl", "tal", "lilt", "ijclclp")

# Constants associated with DOI assignation
DOI_URL_PREFIX = "https://dx.doi.org/"
DOI_PREFIX = "10.18653/v1/"

# Default ingestion date (= unknown)
UNKNOWN_INGEST_DATE = "1900-01-01"

# The venue format must match this pattern
VENUE_FORMAT = r"^[a-z\d]+$"


def match_volume_and_issue(booktitle) -> Tuple[str, str]:
    """Parses a volume name and issue name from a title.

    Examples:
    - <booktitle>Computational Linguistics, Volume 26, Number 1, March 2000</booktitle>
    - <booktitle>Traitement Automatique des Langues 2011 Volume 52 Numéro 1</booktitle>
    - <booktitle>Computational Linguistics, Volume 26, Number 1, March 2000</booktitle>

    :param booktitle: The booktitle
    :return: the volume and issue numbers
    """
    volume_no = re.search(r"Volume\s*(\d+)", booktitle, flags=re.IGNORECASE)
    if volume_no is not None:
        volume_no = volume_no.group(1)

    issue_no = re.search(
        r"(Number|Numéro|Issue)\s*(\d+-?\d*)", booktitle, flags=re.IGNORECASE
    )
    if issue_no is not None:
        issue_no = issue_no.group(2)

    return volume_no, issue_no


def get_journal_info(top_level_id, volume_title) -> Tuple[str, str, str]:
    """Returns info about the journal: title, volume no., and issue no.
    Currently (Feb 2023), this information is parsed from the <booktitle> tag!
    We should move instead to an explicit representation. See

        https://github.com/acl-org/acl-anthology/issues/2379

    :param top_level_id: The collection ID
    :param volume_title: The text from the <booktitle> tag
    :return: The journal title, volume number, and issue number
    """

    # TODO: consider moving this from code to data (perhaps
    # under <booktitle> in the volume metadata

    top_level_id = top_level_id.split(".")[-1]  # for new-style IDs; is a no-op otherwise

    journal_title = None
    volume_no = None
    issue_no = None

    if top_level_id == "cl":
        # <booktitle>Computational Linguistics, Volume 26, Number 1, March 2000</booktitle>
        journal_title = "Computational Linguistics"
        volume_no, issue_no = match_volume_and_issue(volume_title)

    elif top_level_id == "lilt":
        # <booktitle>Linguistic Issues in Language Technology, Volume 10, 2015</booktitle>
        journal_title = "Linguistic Issues in Language Technology"
        volume_no, _ = match_volume_and_issue(volume_title)

    elif top_level_id == "tal":
        # <booktitle>Traitement Automatique des Langues 2011 Volume 52 Numéro 1</booktitle>
        journal_title = "Traitement Automatique des Langues"
        volume_no, issue_no = match_volume_and_issue(volume_title)

    elif top_level_id == "ijclclp":
        journal_title = "International Journal of Computational Linguistics & Chinese Language Processing"
        volume_no, issue_no = match_volume_and_issue(volume_title)

    elif top_level_id == "nejlt":
        journal_title = "Northern European Journal of Language Technology"
        volume_no, _ = match_volume_and_issue(volume_title)

    elif top_level_id[0] == "J":
        # <booktitle>Computational Linguistics, Volume 26, Number 1, March 2000</booktitle>
        year = int(top_level_id[1:3])
        if year >= 65 and year <= 83:
            journal_title = "American Journal of Computational Linguistics"
        else:
            journal_title = "Computational Linguistics"

        volume_no, issue_no = match_volume_and_issue(volume_title)

    elif top_level_id[0] == "Q" or top_level_id == "tacl":
        journal_title = "Transactions of the Association for Computational Linguistics"
        volume_no, _ = match_volume_and_issue(volume_title)

    else:
        journal_title = volume_title

    return journal_title, volume_no, issue_no
