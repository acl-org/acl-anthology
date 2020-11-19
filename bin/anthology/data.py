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

ANTHOLOGY_PREFIX = "https://www.aclweb.org/anthology"
ATTACHMENT_PREFIX = ANTHOLOGY_PREFIX + "/attachments"

# These should be renamed as "templates" so it's clear how they should be used
ANTHOLOGY_URL = ANTHOLOGY_PREFIX + "/{}"
ANTHOLOGY_PDF = ANTHOLOGY_PREFIX + "/{}.pdf"
ANTHOLOGY_THUMBNAIL = ANTHOLOGY_PREFIX + "/thumb/{}.jpg"

# Regular expression matching full Anthology IDs
ANTHOLOGY_ID_REGEX = r"[A-Z]\d{2}-\d{4}"

# Names of XML elements that may appear multiple times
LIST_ELEMENTS = (
    "attachment",
    "author",
    "editor",
    "video",
    "revision",
    "erratum",
    "award",
)

# New-style IDs that should be handled as journals
JOURNAL_IDS = ("cl", "tacl")

# Constants associated with DOI assignation
DOI_URL_PREFIX = "http://dx.doi.org/"
DOI_PREFIX = "10.18653/v1/"

# Default ingestion date (= unknown)
UNKNOWN_INGEST_DATE = "1900-01-01"

# The venue format must match this pattern
VENUE_FORMAT = r"^[A-Za-z\d]+$"


def get_journal_title(top_level_id, volume_title):
    # TODO: consider moving this from code to data (perhaps
    # under <booktitle> in the volume metadata

    top_level_id = top_level_id.split(".")[-1]  # for new-style IDs; is a no-op otherwise

    if top_level_id == "cl":
        return "Computational Linguistics"
    if top_level_id[0] == "J":
        year = int(top_level_id[1:3])
        if year >= 65 and year <= 83:
            return "American Journal of Computational Linguistics"
        else:
            return "Computational Linguistics"
    elif top_level_id[0] == "Q" or top_level_id == "tacl":
        return "Transactions of the Association for Computational Linguistics"
    else:
        return volume_title
