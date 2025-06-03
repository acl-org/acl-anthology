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

from enum import Enum


class EventLinkingType(Enum):
    """How a volume ID was connected to an Event."""

    EXPLICIT = "explicit"
    """Volume ID is explicitly listed in <colocated> block in XML."""

    INFERRED = "inferred"
    """Volume ID was inferred to belong to Event through venue association."""


class PaperDeletionType(Enum):
    """Type of deletion of a paper."""

    RETRACTED = "retracted"
    """Paper was retracted.  A retraction occurs when serious, unrecoverable errors are discovered, which drastically affect the findings of the original work."""

    REMOVED = "removed"
    """Paper was removed.  A removal occurs in rare circumstances where serious ethical or legal issues arise, such as plagiarism."""


class PaperType(Enum):
    """Type of paper.

    Currently only exists to support a few paper instances that are marked up as 'backmatter'.
    """

    PAPER = "paper"
    """A regular paper."""

    FRONTMATTER = "frontmatter"
    """The frontmatter of a volume."""

    BACKMATTER = "backmatter"
    """The backmatter of a volume."""


class VolumeType(Enum):
    """Type of publication a volume represents."""

    JOURNAL = "journal"
    """A journal issue."""

    PROCEEDINGS = "proceedings"
    """A conference/workshop proceedings volume."""
