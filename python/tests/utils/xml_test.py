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
from acl_anthology.utils import xml

test_cases_xml = (
    (
        "<span>Lorem <b>ipsum</b> <i>dolor</i> sit <b>a<i>men</i></b></span>",
        None,
        "Lorem <b>ipsum</b> <i>dolor</i> sit <b>a<i>men</i></b>",
    ),
    (
        "<span>Lorem <b>ipsum</b> <i>dolor</i> sit <b>a<i>men</i></b></span>",
        "./b",
        "ipsum",
    ),
    (
        "<span>Lorem <b>ipsum</b> <i>dolor</i> sit <b>a<i>men</i></b></span>",
        "./i",
        "dolor sit",
    ),
    (
        "<span>Lorem ipsum <i>dolor</i> sit <b>a<i>men</i></b>!</span>",
        "./b",
        "a<i>men</i>!",
    ),
)

test_cases_indent = (
    (
        "<paper><author><first>Peter</first><last>Parker</last></author></paper>",
        """<paper>
  <author><first>Peter</first><last>Parker</last></author>
</paper>
""",
    ),
    (
        "<meta>    <foo>Foo</foo> <bar>Bar</bar></meta>",
        """<meta>
  <foo>Foo</foo>
  <bar>Bar</bar>
</meta>
""",
    ),
    (
        "<title>With <b>nested <i>markup with subsequent closing tags</i></b></title>",
        """<title>With <b>nested <i>markup with subsequent closing tags</i></b></title>
""",
    ),
)


@pytest.mark.parametrize("inp, child, out", test_cases_xml)
def test_stringify_children(inp, child, out):
    element = etree.fromstring(inp)
    if child is not None:
        element = element.find(child)
    assert xml.stringify_children(element) == out


@pytest.mark.parametrize("inp, out", test_cases_indent)
def test_indent(inp, out):
    element = etree.fromstring(inp)
    xml.indent(element)
    assert etree.tostring(element, encoding="unicode") == out
