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

from attrs import define, field
from typing import cast, Optional

from .config import config


@define
class FileReference:
    """Base class for all references to local or remote files in the XML data.

    Do not instantiate directly; use the sub-classes instead

    Attributes:
        template_field (str): The URL formatting template to use.  Set by the sub-classes.
        name (str): The file reference (as found in the XML), typically a URL or an internal filename.
        checksum (Optional[str]): The CRC32 checksum for the file.  Only specified for internal filenames.
    """

    template_field: str = field()
    name: str = field()
    checksum: Optional[str] = field(default=None)

    @property
    def url(self) -> str:
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

    template_field: str = "attachment_location_template"


@define
class EventFileReference(FileReference):
    """Reference to an event-related file."""

    template_field: str = "event_location_template"


@define
class VideoReference(FileReference):
    """Reference to a video."""

    template_field: str = "attachment_location_template"
