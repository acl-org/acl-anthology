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

from acl_anthology import config
from acl_anthology.files import PDFReference, VideoReference, PapersWithCodeReference


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
        "https://aclanthology.org/attachments/2022.acl-long.225.mp4",
        True,
    ),
    (
        '<video href="https://vimeo.com/385504611" permission="false"/>',
        "https://vimeo.com/385504611",
        "https://vimeo.com/385504611",
        False,
    ),
)


test_cases_pwc = (
    (
        (
            '<pwcdataset url="https://paperswithcode.com/dataset/wlasl">WLASL</pwcdataset>',
        ),
        None,
        False,
        [("WLASL", "https://paperswithcode.com/dataset/wlasl")],
    ),
    (
        (
            '<pwccode url="https://github.com/lksenel/coda21" additional="false">lksenel/coda21</pwccode>',
        ),
        ("lksenel/coda21", "https://github.com/lksenel/coda21"),
        False,
        [],
    ),
    (
        (
            '<pwcdataset url="https://paperswithcode.com/dataset/commonsenseqa">CommonsenseQA</pwcdataset>',
            '<pwcdataset url="https://paperswithcode.com/dataset/qasc">QASC</pwcdataset>',
            '<pwcdataset url="https://paperswithcode.com/dataset/squad">SQuAD</pwcdataset>',
            '<pwcdataset url="https://paperswithcode.com/dataset/sciq">SciQ</pwcdataset>',
        ),
        None,
        False,
        [
            ("CommonsenseQA", "https://paperswithcode.com/dataset/commonsenseqa"),
            ("QASC", "https://paperswithcode.com/dataset/qasc"),
            ("SQuAD", "https://paperswithcode.com/dataset/squad"),
            ("SciQ", "https://paperswithcode.com/dataset/sciq"),
        ],
    ),
    (
        (
            '<pwccode url="https://github.com/thunlp/OpenPrompt" additional="true">thunlp/OpenPrompt</pwccode>',
            '<pwcdataset url="https://paperswithcode.com/dataset/glue">GLUE</pwcdataset>',
        ),
        ("thunlp/OpenPrompt", "https://github.com/thunlp/OpenPrompt"),
        True,
        [("GLUE", "https://paperswithcode.com/dataset/glue")],
    ),
    (
        # This happens, so it needs to be handled
        ('<pwccode url="" additional="true"/>',),
        (None, ""),
        True,
        [],
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


@pytest.mark.parametrize("xml_list, code, community_code, datasets", test_cases_pwc)
def test_pwc_reference_from_xml(xml_list, code, community_code, datasets):
    ref = PapersWithCodeReference()
    for xml in xml_list:
        element = etree.fromstring(xml)
        ref.append_from_xml(element)
    assert ref.code == code
    assert ref.community_code == community_code
    assert ref.datasets == datasets


@pytest.mark.parametrize("xml_list, code, community_code, datasets", test_cases_pwc)
def test_pwc_reference_to_xml(xml_list, code, community_code, datasets):
    ref = PapersWithCodeReference(
        code=code,
        community_code=community_code,
        datasets=datasets,
    )
    actual_xml_list = ref.to_xml_list()
    assert len(xml_list) == len(actual_xml_list)
    for expected_xml, actual_xml in zip(xml_list, actual_xml_list):
        assert etree.tostring(actual_xml, encoding="unicode") == expected_xml
