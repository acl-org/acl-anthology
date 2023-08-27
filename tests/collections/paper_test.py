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

import pytest
from acl_anthology.collections import CollectionIndex, Paper
from acl_anthology.text import MarkupText
from acl_anthology.utils.xml import indent
from lxml import etree


@pytest.fixture
def index(anthology_stub):
    return CollectionIndex(anthology_stub)


def test_paper_minimum_attribs():
    paper_title = MarkupText.from_string("A minimal example")
    parent = None
    paper = Paper("42", parent, bibkey="nn-1900-minimal", title=paper_title)
    assert not paper.is_deleted
    assert paper.title == paper_title


test_cases_xml = (
    """<paper id="1">
  <title>Strings from neurons to language</title>
  <author><first>Tim</first><last>Fernando</last></author>
  <pages>1–10</pages>
  <url hash="61daae5b">2022.naloma-1.1</url>
  <bibkey>fernando-2022-strings</bibkey>
</paper>
""",
)


@pytest.mark.parametrize("xml", test_cases_xml)
def test_paper_from_to_xml(xml):
    paper = Paper.from_xml(None, etree.fromstring(xml))
    out = paper.to_xml()
    indent(out)
    assert etree.tostring(out, encoding="unicode") == xml
