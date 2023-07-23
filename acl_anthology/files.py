# Copyright 2023 Marcel Bollmann <marcel@bollmann.me>
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

"""Classes for representing and resolving file references."""

from attrs import define, field, Factory
from typing import cast, Optional

from .config import config


@define
class FileReference:
    """Base class for all references to local or remote files in the XML data.

    Do not instantiate directly; use the sub-classes instead.

    Attributes:
        template_field (str): The URL formatting template to use.  Set by the sub-classes.
        name (str): The file reference (as found in the XML), typically a URL or an internal filename.
        checksum (Optional[str]): The CRC32 checksum for the file.  Only specified for internal filenames.
    """

    template_field: str = field()
    name: str = field()
    checksum: Optional[str] = field(default=None)

    @property
    def is_local(self) -> bool:
        """Whether this is a local filename."""
        return "://" not in self.name

    @property
    def url(self) -> str:
        """The URL at which this file can be accessed."""
        if "://" in self.name:
            return self.name
        return cast(str, config[self.template_field]).format(self.name)


@define
class PDFReference(FileReference):
    """Reference to a PDF file."""

    template_field: str = "pdf_location_template"


@define
class PDFThumbnailReference(FileReference):
    """Reference to a PDF thumbnail image."""

    template_field: str = "pdf_thumbnail_location_template"


@define
class AttachmentReference(FileReference):
    """Reference to an attachment."""

    # TODO: attachments must be local files according to the schema

    template_field: str = "attachment_location_template"


@define
class EventFileReference(FileReference):
    """Reference to an event-related file."""

    template_field: str = "event_location_template"


@define
class VideoReference(FileReference):
    """Reference to a video."""

    # TODO: videos can only be remote URLs according to the schema

    template_field: str = "attachment_location_template"
    permission: bool = field(default=True)


@define
class PapersWithCodeReference:
    """Class aggregating [Papers with Code](https://paperswithcode.com/) (PwC) links in a paper.

    Attributes:
        code: An official code repository, given as a tuple of the form `(name, url)`.
        community_code: Whether the PwC page of the paper has additional, community-provided code links.
        datasets: A list of datasets on PwC, given as tuples of the form `(name, url)`.
    """

    code: Optional[tuple[str, str]] = field(default=None)
    community_code: bool = field(default=False)
    datasets: list[tuple[str, str]] = Factory(list)
