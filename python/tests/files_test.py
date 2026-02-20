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

import pytest
from lxml import etree
import requests
import responses

from acl_anthology import config
from acl_anthology.exceptions import ChecksumMismatchWarning
from acl_anthology.files import (
    AttachmentReference,
    PDFReference,
    VideoReference,
)

test_cases_pdf = (
    (
        '<url hash="a8b4ae72">2022.acl-demo.14</url>',
        "2022.acl-demo.14",
        "https://aclanthology.org/2022.acl-demo.14.pdf",
        "a8b4ae72",
        True,
    ),
    (
        '<url hash="f9ed34ae">J89-3004</url>',
        "J89-3004",
        "https://aclanthology.org/J89-3004.pdf",
        "f9ed34ae",
        True,
    ),
    (
        "<url>http://www.lrec-conf.org/proceedings/lrec2006/pdf/4_pdf.pdf</url>",
        "http://www.lrec-conf.org/proceedings/lrec2006/pdf/4_pdf.pdf",
        "http://www.lrec-conf.org/proceedings/lrec2006/pdf/4_pdf.pdf",
        None,
        False,
    ),
)


test_cases_video = (
    (
        '<video href="2022.acl-long.225.mp4"/>',
        "2022.acl-long.225.mp4",
        "https://aclanthology.org/2022.acl-long.225.mp4",
        True,
    ),
    (
        '<video href="https://vimeo.com/385504611" permission="false"/>',
        "https://vimeo.com/385504611",
        "https://vimeo.com/385504611",
        False,
    ),
)


def test_pdf_reference_remote():
    name = "https://some-external-server.com/paper.pdf"
    ref = PDFReference(name)
    assert ref.url == name


def test_pdf_reference_internal():
    name = "2023.venue-volume.222"
    pdf_location_template = config.pdf_location_template
    config.pdf_location_template = "https://my-server.com/{}.pdf"
    ref = PDFReference(name)
    assert ref.url == "https://my-server.com/2023.venue-volume.222.pdf"
    config.pdf_location_template = pdf_location_template


@pytest.mark.parametrize("xml, name, url, checksum, is_local", test_cases_pdf)
def test_pdf_reference_from_xml(xml, name, url, checksum, is_local):
    element = etree.fromstring(xml)
    ref = PDFReference.from_xml(element)
    assert ref.name == name
    assert ref.url == url
    assert ref.checksum == checksum
    assert ref.is_local == is_local


@pytest.mark.parametrize("xml, name, url, checksum, is_local", test_cases_pdf)
def test_pdf_reference_init(xml, name, url, checksum, is_local):
    ref = PDFReference(name=name, checksum=checksum)
    assert ref.name == name
    assert ref.url == url
    assert ref.checksum == checksum
    assert ref.is_local == is_local


@pytest.mark.parametrize("xml, name, url, checksum, is_local", test_cases_pdf)
def test_pdf_reference_to_xml(xml, name, url, checksum, is_local):
    ref = PDFReference(name=name, checksum=checksum)
    assert etree.tostring(ref.to_xml("url"), encoding="unicode") == xml


@pytest.mark.parametrize("xml, name, url, permission", test_cases_video)
def test_video_reference_from_xml(xml, name, url, permission):
    element = etree.fromstring(xml)
    ref = VideoReference.from_xml(element)
    assert ref.name == name
    assert ref.url == url
    assert ref.permission == permission


@pytest.mark.parametrize("xml, name, url, permission", test_cases_video)
def test_video_reference_to_xml(xml, name, url, permission):
    ref = VideoReference(name=name, permission=permission)
    assert ref.url == url
    assert etree.tostring(ref.to_xml("video"), encoding="unicode") == xml


def test_reference_cant_change_template_field():
    name = "2023.venue-volume.222"
    ref = PDFReference(name)
    assert isinstance(ref.template_field, str)
    with pytest.raises(AttributeError):
        ref.template_field = "foo"


def test_pdfreference_from_file(datadir):
    ref = PDFReference.from_file(datadir / "J16-4001.pdf")
    assert ref.name == "J16-4001"  # WITHOUT the .pdf
    assert ref.checksum == "f9f4f558"


def test_pdfreference_from_nonexistant_file(datadir):
    with pytest.raises(FileNotFoundError):
        _ = PDFReference.from_file(datadir / "J16-9999.pdf")


def test_attachmentreference_from_file(datadir):
    ref = AttachmentReference.from_file(datadir / "J16-4001.pdf")
    assert ref.name == "J16-4001.pdf"  # WITH the .pdf
    assert ref.checksum == "f9f4f558"


@responses.activate
def test_pdfreference_download(datadir, tmp_path):
    ref = PDFReference(name="J16-4001", checksum="f9f4f558")
    with open(datadir / "J16-4001.pdf", "rb") as f:
        content = f.read()

    # Mock server response
    responses.get(
        "https://aclanthology.org/J16-4001.pdf",
        status=200,
        headers={"Content-Type": "application/pdf"},
        body=content,
    )

    ref.download(tmp_path / "J16-4001.pdf")


@responses.activate
def test_pdfreference_download_warns_on_wrong_checksum(datadir, tmp_path):
    ref = PDFReference(name="J16-4001", checksum="a1e5f231")
    with open(datadir / "J16-4001.pdf", "rb") as f:
        content = f.read()

    # Mock server response
    responses.get(
        "https://aclanthology.org/J16-4001.pdf",
        status=200,
        headers={"Content-Type": "application/pdf"},
        body=content,
    )

    with pytest.warns(ChecksumMismatchWarning):
        ref.download(tmp_path / "J16-4001.pdf")


@responses.activate
def test_pdfreference_download_raises_on_404(tmp_path):
    ref = PDFReference(name="J16-4001", checksum="f9f4f558")

    # Mock server response
    responses.get(
        "https://aclanthology.org/J16-4001.pdf",
        status=404,
    )

    with pytest.raises(requests.HTTPError):
        ref.download(tmp_path / "J16-4001.pdf")


@responses.activate
def test_pdfreference_download_raises_on_wrong_contenttype(tmp_path):
    ref = PDFReference(name="J16-4001", checksum="f9f4f558")

    # Mock server response
    responses.get(
        "https://aclanthology.org/J16-4001.pdf",
        status=200,
    )

    with pytest.raises(ValueError, match="Expected 'application/pdf'"):
        ref.download(tmp_path / "J16-4001.pdf")
