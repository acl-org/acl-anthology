# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
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

import sys
from attrs import define, field, Factory
from lxml import etree
from lxml.builder import E
from typing import cast, Optional

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from .config import config
from .utils.xml import xsd_boolean


@define
class FileReference:
    """Base class for all references to local or remote files in the XML data.

    Do not instantiate directly; use the sub-classes instead.

    Attributes:
        template_field (str): The URL formatting template to use.  Set by the sub-classes.
        name (str): The file reference (as found in the XML), typically a URL or an internal filename.
        checksum (Optional[str]): The CRC32 checksum for the file.  Only specified for internal filenames.
    """

    name: str = field()
    checksum: Optional[str] = field(default=None)
    template_field: str = field(repr=False, default="")

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

    @classmethod
    def from_xml(cls, elem: etree._Element) -> Self:
        """Instantiates a new file reference from a corresponding XML element."""
        checksum = elem.get("hash")
        return cls(name=str(elem.text), checksum=str(checksum) if checksum else None)

    def to_xml(self, tag: str = "url") -> etree._Element:
        """
        Arguments:
            tag: Name of outer tag in which this file reference should be wrapped.  Defaults to "url".

        Returns:
            A serialization of this file reference in Anthology XML format.
        """
        elem = etree.Element(tag)
        elem.text = self.name
        if self.is_local and self.checksum is not None:
            elem.set("hash", str(self.checksum))
        return elem


@define
class PDFReference(FileReference):
    """Reference to a PDF file."""

    template_field: str = field(repr=False, default="pdf_location_template")


@define
class PDFThumbnailReference(FileReference):
    """Reference to a PDF thumbnail image."""

    template_field: str = field(repr=False, default="pdf_thumbnail_location_template")


@define
class AttachmentReference(FileReference):
    """Reference to an attachment."""

    # TODO: attachments must be local files according to the schema

    template_field: str = field(repr=False, default="attachment_location_template")


@define
class EventFileReference(FileReference):
    """Reference to an event-related file."""

    template_field: str = field(repr=False, default="event_location_template")


@define
class VideoReference(FileReference):
    """Reference to a video."""

    # TODO: videos can only be remote URLs according to the schema

    template_field: str = field(repr=False, default="attachment_location_template")
    permission: bool = field(default=True)

    @classmethod
    def from_xml(cls, elem: etree._Element) -> Self:
        name = str(elem.get("href"))
        if (value := elem.get("permission")) is not None:
            return cls(name=name, permission=xsd_boolean(str(value)))
        else:
            return cls(name=name)

    def to_xml(self, tag: str = "video") -> etree._Element:
        elem = E.video(href=self.name)
        if not self.permission:
            elem.set("permission", "false")
        return elem


@define
class PapersWithCodeReference:
    """Class aggregating [Papers with Code](https://paperswithcode.com/) (PwC) links in a paper.

    Attributes:
        code: An official code repository, given as a tuple of the form `(name, url)`.
        community_code: Whether the PwC page of the paper has additional, community-provided code links.
        datasets: A list of datasets on PwC, given as tuples of the form `(name, url)`.
    """

    code: Optional[tuple[str | None, str]] = field(default=None)
    community_code: bool = field(default=False)
    datasets: list[tuple[str | None, str]] = Factory(list)

    def append_from_xml(self, elem: etree._Element) -> None:
        """Appends information from a `<pwccode>` or `<pwcdataset>` block to this reference."""
        pwc_tuple = (elem.text, elem.get("url", ""))
        if elem.tag == "pwccode":
            self.community_code = xsd_boolean(elem.get("additional", ""))
            self.code = pwc_tuple
        elif elem.tag == "pwcdataset":
            self.datasets.append(pwc_tuple)
        else:
            raise ValueError(
                f"Unsupported element for PapersWithCodeReference: <{elem.tag}>"
            )

    def to_xml_list(self) -> list[etree._Element]:
        """
        Returns:
            A serialization of all PapersWithCode information as a list of corresponding XML tags in the Anthology XML format.
        """
        elements = []
        if self.code is not None:
            args = [self.code[0]] if self.code[0] is not None else []
            elements.append(
                E.pwccode(
                    *args,
                    url=self.code[1],
                    additional=str(self.community_code).lower(),
                )
            )
        for dataset in self.datasets:
            args = [dataset[0]] if dataset[0] is not None else []
            elements.append(E.pwcdataset(*args, url=dataset[1]))
        return elements
