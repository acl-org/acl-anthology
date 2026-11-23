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

from enum import StrEnum


class SimpleReprEnum(StrEnum):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class EventLink(SimpleReprEnum):
    """How a volume ID was connected to an Event."""

    EXPLICIT = "explicit"
    """Volume ID is explicitly listed in <colocated> block in XML."""

    INFERRED = "inferred"
    """Volume ID was inferred to belong to Event through venue association."""


class PaperDeletionType(SimpleReprEnum):
    """Type of deletion of a paper."""

    RETRACTED = "retracted"
    """Paper was retracted.  A retraction occurs when serious, unrecoverable errors are discovered, which drastically affect the findings of the original work."""

    REMOVED = "removed"
    """Paper was removed.  A removal occurs in rare circumstances where serious ethical or legal issues arise, such as plagiarism."""


class PaperType(SimpleReprEnum):
    """Type of printed paper. Frontmatter is a legacy factory selector."""

    PAPER = "paper"
    """A regular paper."""

    FRONTMATTER = "frontmatter"
    """The frontmatter of a volume."""

    BACKMATTER = "backmatter"
    """The backmatter of a volume."""


class MediaType(SimpleReprEnum):
    """Genre of a standalone media record, independently of its recording format."""

    MEDIA = "media"
    """A recording without a more specific genre."""

    TALK = "talk"
    """An invited talk, presentation, or address."""

    KEYNOTE = "keynote"
    """A keynote talk."""

    PLENARY = "plenary"
    """A plenary talk."""

    PANEL = "panel"
    """A panel discussion."""

    MEETING = "meeting"
    """A business meeting or other meeting."""

    PODCAST = "podcast"
    """A podcast episode."""

    TUTORIAL = "tutorial"
    """A recorded tutorial without an associated paper."""

    INTERVIEW = "interview"
    """An interview or oral history."""

    LECTURE = "lecture"
    """A lecture."""

    CEREMONY = "ceremony"
    """An opening, closing, or awards ceremony."""


class VolumeType(SimpleReprEnum):
    """Type of publication a volume represents."""

    JOURNAL = "journal"
    """A journal issue."""

    PROCEEDINGS = "proceedings"
    """A conference/workshop proceedings volume."""

    MEDIA = "media"
    """A collection of recordings, such as event media or a year of a podcast."""
