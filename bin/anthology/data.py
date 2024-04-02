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

# Constants associated with DOI assignation
DOI_URL_PREFIX = "https://doi.org/"
DOI_PREFIX = "10.18653/v1/"

# Default ingestion date (= unknown)
UNKNOWN_INGEST_DATE = "1900-01-01"

# The venue format must match this pattern
VENUE_FORMAT = r"^[a-z\d]+$"
