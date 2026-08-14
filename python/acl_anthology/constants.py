# Copyright 2023-2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Constants used within the library."""

from datetime import date
import re
from typing import Final

FRONTMATTER_ID: Final = "0"
"""Paper ID that signals that a paper is frontmatter."""

NO_BIBKEY: Final = "__NO_BIBKEY__"
"""Sentinel value to be set on a newly created paper, before its bibkey is generated."""

NO_PERSON_ID: Final = "__NO_PERSON_ID__"
"""Sentinel value to be set on a NameSpecification to temporarily unlink it from a Person."""

UNKNOWN_INGEST_DATE = date(1900, 1, 1)
"""Default ingestion date."""

RE_BIBKEY = re.compile(rf"^([a-z][a-z0-9-]+)|({NO_BIBKEY})$")
"""A regular expression matching a valid bibkey (following our conventions)."""

RE_COLLECTION_ID = re.compile(r"([0-9]{4}\.[a-z0-9]+)|([A-Z][0-9]{2})")
"""A regular expression matching any valid collection ID."""

RE_ITEM_ID = re.compile(r"[a-z0-9]+")
"""A regular expression matching any valid volume or paper ID."""

RE_VERIFIED_PERSON_ID = re.compile(rf"([a-z][\-a-z0-9]+)|({NO_PERSON_ID})")
"""A regular expression matching any valid verified person ID."""

RE_ORCID = re.compile(r"[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]")
"""A regular expression matching any string that looks like an ORCID."""

RE_EVENT_ID = re.compile(r"^[a-z0-9]+-[0-9]{4}$")
"""A regular expression matching a valid event ID."""

RE_VENUE_ID = re.compile(r"^[a-z][a-z0-9]+$")
"""A regular expression matching a valid venue ID."""

RE_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
"""A regular expression matching a date in ISO format."""
