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
from acl_anthology.collections import CollectionIndex
from acl_anthology.collections.types import VolumeType
from acl_anthology.files import PDFReference
from acl_anthology.text import MarkupText
from acl_anthology.utils.xml import indent
from lxml import etree

from acl_anthology.collections.paper import (
    Paper,
    PaperDeletionType,
    PaperDeletionNotice,
    PaperErratum,
    PaperRevision,
)


class VolumeStub:
    title = "Generic volume"
    editors = []


@pytest.fixture
def index(anthology_stub):
    return CollectionIndex(anthology_stub)


def test_paper_minimum_attribs():
    paper_title = MarkupText.from_string("A minimal example")
    parent = None
    paper = Paper("42", parent, bibkey="nn-1900-minimal", title=paper_title)
    assert not paper.is_deleted
    assert paper.title == paper_title


def test_paper_web_url(anthology):
    paper = anthology.get_paper("2022.acl-demo.2")
    assert paper.web_url == "https://aclanthology.org/2022.acl-demo.2/"


def test_paper_get_events(anthology):
    paper = anthology.get_paper("2022.acl-demo.2")
    assert paper is not None
    assert paper.get_events() == [anthology.events["acl-2022"]]


def test_paper_bibtype():
    volume = VolumeStub()
    volume.type = VolumeType.JOURNAL
    paper = Paper("1", volume, bibkey="", title=MarkupText.from_string(""))
    assert paper.bibtype == "article"
    volume.type = VolumeType.PROCEEDINGS
    assert paper.bibtype == "inproceedings"
    paper.id = "0"
    assert paper.bibtype == "proceedings"
    volume.type = VolumeType.JOURNAL
    assert paper.bibtype == "book"


test_cases_xml = (
    """<frontmatter>
  <url hash="56ea4e43">2022.acl-long.0</url>
  <bibkey>acl-2022-association-linguistics-1</bibkey>
</frontmatter>
""",
    """<paper id="1">
  <title>Strings from neurons to language</title>
  <author><first>Tim</first><last>Fernando</last></author>
  <pages>1–10</pages>
  <url hash="61daae5b">2022.naloma-1.1</url>
  <bibkey>fernando-2022-strings</bibkey>
</paper>
""",
    """<paper id="9">
  <title>Briefly Noted</title>
  <url hash="166bd6c1">J89-1009</url>
  <bibkey>nn-1989-briefly</bibkey>
</paper>
""",
    """<paper id="6">
  <title>Domain Adaptation in Multilingual and Multi-Domain Monolingual Settings for Complex Word Identification</title>
  <author><first>George-Eduard</first><last>Zaharia</last></author>
  <author><first>Răzvan-Alexandru</first><last>Smădu</last></author>
  <author><first>Dumitru</first><last>Cercel</last></author>
  <author><first>Mihai</first><last>Dascalu</last></author>
  <pages>70-80</pages>
  <abstract>Complex word identification (CWI) is a cornerstone process towards proper text simplification. CWI is highly dependent on context, whereas its difficulty is augmented by the scarcity of available datasets which vary greatly in terms of domains and languages. As such, it becomes increasingly more difficult to develop a robust model that generalizes across a wide array of input examples. In this paper, we propose a novel training technique for the CWI task based on domain adaptation to improve the target character and context representations. This technique addresses the problem of working with multiple domains, inasmuch as it creates a way of smoothing the differences between the explored datasets. Moreover, we also propose a similar auxiliary task, namely text simplification, that can be used to complement lexical complexity prediction. Our model obtains a boost of up to 2.42% in terms of Pearson Correlation Coefficients in contrast to vanilla training techniques, when considering the CompLex from the Lexical Complexity Prediction 2021 dataset. At the same time, we obtain an increase of 3% in Pearson scores, while considering a cross-lingual setup relying on the Complex Word Identification 2018 dataset. In addition, our model yields state-of-the-art results in terms of Mean Absolute Error.</abstract>
  <url hash="23e260bb">2022.acl-long.6</url>
  <doi>10.18653/v1/2022.acl-long.6</doi>
  <video href="2022.acl-long.6.mp4"/>
  <bibkey>zaharia-etal-2022-domain</bibkey>
</paper>
""",
    """<paper id="max" ingest-date="2023-09-30">
  <title>This <fixed-case>P</fixed-case>aper Has All Fields That A Paper Can Have</title>
  <author><first/><last>None</last></author>
  <editor><first>Marcel</first><last>Bollmann</last></editor>
  <pages>0</pages>
  <abstract>
    <b>Look</b> at <i>this</i>!
  </abstract>
  <url hash="d6a71220">2023.fake-volume.max</url>
  <erratum id="1" hash="21a4921f">2023.fake-volume.maxe2</erratum>
  <revision id="1" href="2023.fake-volume.max" hash="21e2f21f"/>
  <revision id="2" href="2023.fake-volume.maxv2" hash="bc27f0f5" date="2023-10-03">Some explanation</revision>
  <doi>10.18653/v1/2023.fake-volume.max</doi>
  <language>Klingon</language>
  <note>This is not a real paper, obviously.</note>
  <attachment hash="a6a7a5a4" type="website">2023.fake-attachment</attachment>
  <attachment hash="12345678" type="software">2023.fake-software</attachment>
  <video href="2023.fake-video.mp4"/>
  <award>Most ridiculous entry</award>
  <removed date="2023-09-30">Removed immediately for being fake</removed>
  <bibkey>why-would-you-cite-this</bibkey>
  <pwccode url="https://github.com/acl-org/fake-repo" additional="false">acl-org/fake-repo</pwccode>
  <pwcdataset url="https://paperswithcode.com/dataset/fake-dataset">FaKe-DaTaSeT</pwcdataset>
</paper>
""",
)


@pytest.mark.parametrize("xml", test_cases_xml)
def test_paper_roundtrip_xml(xml):
    paper = Paper.from_xml(VolumeStub(), etree.fromstring(xml))
    out = paper.to_xml()
    indent(out)
    assert etree.tostring(out, encoding="unicode") == xml


def test_paper_to_bibtex_inproceedings(anthology):
    paper = anthology.get("2022.acl-long.268")
    expected = """@inproceedings{alvarez-mellado-lignos-2022-detecting,
    title = "Detecting Unassimilated Borrowings in {S}panish: {A}n Annotated Corpus and Approaches to Modeling",
    author = "\\'Alvarez-Mellado, Elena  and
      Lignos, Constantine",
    editor = "Muresan, Smaranda  and
      Nakov, Preslav  and
      Villavicencio, Aline",
    booktitle = "Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
    month = may,
    year = "2022",
    address = "Dublin, Ireland",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2022.acl-long.268/",
    doi = "10.18653/v1/2022.acl-long.268",
    pages = "3868--3888",
    abstract = "This work presents a new resource for borrowing identification and analyzes the performance and errors of several models on this task. We introduce a new annotated corpus of Spanish newswire rich in unassimilated lexical borrowings---words from one language that are introduced into another without orthographic adaptation---and use it to evaluate how several sequence labeling models (CRF, BiLSTM-CRF, and Transformer-based models) perform. The corpus contains 370,000 tokens and is larger, more borrowing-dense, OOV-rich, and topic-varied than previous corpora available for this task. Our results show that a BiLSTM-CRF model fed with subword embeddings along with either Transformer-based embeddings pretrained on codeswitched data or a combination of contextualized word embeddings outperforms results obtained by a multilingual BERT-based model."
}"""
    assert paper.to_bibtex(with_abstract=True) == expected
    expected_without_abstract = """@inproceedings{alvarez-mellado-lignos-2022-detecting,
    title = "Detecting Unassimilated Borrowings in {S}panish: {A}n Annotated Corpus and Approaches to Modeling",
    author = "\\'Alvarez-Mellado, Elena  and
      Lignos, Constantine",
    editor = "Muresan, Smaranda  and
      Nakov, Preslav  and
      Villavicencio, Aline",
    booktitle = "Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
    month = may,
    year = "2022",
    address = "Dublin, Ireland",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2022.acl-long.268/",
    doi = "10.18653/v1/2022.acl-long.268",
    pages = "3868--3888"
}"""
    assert paper.to_bibtex(with_abstract=False) == expected_without_abstract


def test_paper_to_bibtex_proceedings(anthology):
    paper = anthology.get("2022.acl-short.0")
    expected = """@proceedings{acl-2022-association-linguistics,
    title = "Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 2: Short Papers)",
    editor = "Muresan, Smaranda  and
      Nakov, Preslav  and
      Villavicencio, Aline",
    month = may,
    year = "2022",
    address = "Dublin, Ireland",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2022.acl-short.0/"
}"""
    assert paper.to_bibtex() == expected


def test_paper_to_bibtex_article(anthology):
    paper = anthology.get("J89-2002")
    expected = """@article{oshaughnessy-1989-parsing,
    title = "Parsing with a Small Dictionary for Applications such as Text to Speech",
    author = "O'Shaughnessy, Douglas D.",
    journal = "Computational Linguistics",
    volume = "15",
    number = "2",
    year = "1989",
    url = "https://aclanthology.org/J89-2002/",
    pages = "97--108"
}"""
    assert paper.to_bibtex(with_abstract=True) == expected


def test_paper_to_bibtex_journal(anthology):
    paper = anthology.get("J89-4000")
    expected = """@book{cl-1989-linguistics-15-number-4,
    title = "Computational Linguistics, Volume 15, Number 4, {D}ecember 1989",
    year = "1989",
    url = "https://aclanthology.org/J89-4000/"
}"""
    assert paper.to_bibtex() == expected


test_cases_paperdeletionnotice = (
    (
        '<retracted date="2022-05-06">Paper was intended for the non-archival track.</retracted>',
        PaperDeletionType.RETRACTED,
        "Paper was intended for the non-archival track.",
        "2022-05-06",
    ),
    (
        '<removed date="1984-01-01">Scientific misconduct</removed>',
        PaperDeletionType.REMOVED,
        "Scientific misconduct",
        "1984-01-01",
    ),
)


@pytest.mark.parametrize("xml, type_, note, date", test_cases_paperdeletionnotice)
def test_paperdeletionnotice_from_xml(xml, type_, note, date):
    element = etree.fromstring(xml)
    notice = PaperDeletionNotice.from_xml(element)
    assert notice.type == type_
    assert notice.note == note
    assert notice.date == date


@pytest.mark.parametrize("xml, type_, note, date", test_cases_paperdeletionnotice)
def test_paperdeletionnotice_to_xml(xml, type_, note, date):
    notice = PaperDeletionNotice(type=type_, note=note, date=date)
    assert etree.tostring(notice.to_xml(), encoding="unicode") == xml


test_cases_papererratum = (
    (
        '<erratum id="1" hash="8eecd4c3" date="2022-09-20">P18-1188e1</erratum>',
        "1",
        "P18-1188e1",
        "8eecd4c3",
        "2022-09-20",
    ),
    (
        '<erratum id="42" hash="8edae19f">C12-1115e42</erratum>',
        "42",
        "C12-1115e42",
        "8edae19f",
        None,
    ),
)


@pytest.mark.parametrize(
    "xml, id_, pdf_name, pdf_checksum, date", test_cases_papererratum
)
def test_papererratum_from_xml(xml, id_, pdf_name, pdf_checksum, date):
    element = etree.fromstring(xml)
    erratum = PaperErratum.from_xml(element)
    assert erratum.id == id_
    assert erratum.pdf.name == pdf_name
    assert erratum.pdf.checksum == pdf_checksum
    assert erratum.date == date


@pytest.mark.parametrize(
    "xml, id_, pdf_name, pdf_checksum, date", test_cases_papererratum
)
def test_papererratum_to_xml(xml, id_, pdf_name, pdf_checksum, date):
    erratum = PaperErratum(
        id_, PDFReference(name=pdf_name, checksum=pdf_checksum), date=date
    )
    assert etree.tostring(erratum.to_xml(), encoding="unicode") == xml


test_cases_paperrevision = (
    (
        '<revision id="1" href="Q15-1022v1" hash="f16c56cd"/>',
        "1",
        "Q15-1022v1",
        "f16c56cd",
        None,
        None,
    ),
    (
        '<revision id="2" href="Q15-1022v2" hash="59f9673b">No description of the changes were recorded.</revision>',
        "2",
        "Q15-1022v2",
        "59f9673b",
        None,
        "No description of the changes were recorded.",
    ),
    (
        '<revision id="2" href="2020.pam-1.0v2" hash="7e1b77c7" date="2021-05-04">Author typo correction.</revision>',
        "2",
        "2020.pam-1.0v2",
        "7e1b77c7",
        "2021-05-04",
        "Author typo correction.",
    ),
)


@pytest.mark.parametrize(
    "xml, id_, pdf_name, pdf_checksum, date, note", test_cases_paperrevision
)
def test_paperrevision_from_xml(xml, id_, pdf_name, pdf_checksum, date, note):
    element = etree.fromstring(xml)
    revision = PaperRevision.from_xml(element)
    assert revision.id == id_
    assert revision.pdf.name == pdf_name
    assert revision.pdf.checksum == pdf_checksum
    assert revision.date == date
    assert revision.note == note


@pytest.mark.parametrize(
    "xml, id_, pdf_name, pdf_checksum, date, note", test_cases_paperrevision
)
def test_paperrevision_to_xml(xml, id_, pdf_name, pdf_checksum, date, note):
    revision = PaperRevision(
        id_, note=note, pdf=PDFReference(name=pdf_name, checksum=pdf_checksum), date=date
    )
    assert etree.tostring(revision.to_xml(), encoding="unicode") == xml
