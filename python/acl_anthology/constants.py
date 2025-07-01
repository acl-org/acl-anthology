# Copyright 2023-2025 Marcel Bollmann <marcel@bollmann.me>
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
from typing import Final

FRONTMATTER_ID: Final = "0"
"""Paper ID that signals that a paper is frontmatter."""

NO_BIBKEY: Final = "__NO_BIBKEY__"
"""Sentinel value to be set on a newly created paper, before its bibkeys is generated."""

UNKNOWN_INGEST_DATE = date(1900, 1, 1)
"""Default ingestion date."""

RE_EVENT_ID = r"^[a-z0-9]+-[0-9]{4}$"
"""A regular expression matching a valid event ID."""

RE_ISO_DATE = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
"""A regular expression matching a date in ISO format."""
