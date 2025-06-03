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


test_cases_assert_equals = (
    (  # Switching <first> and <last> is logically equivalent
        "<paper><author><first>Peter</first><last>Parker</last></author></paper>",
        "<paper><author><last>Parker</last><first>Peter</first></author></paper>",
        True,
    ),
    (  # Empty <first> is logically equivalent to missing <first>
        "<paper><author><first/><last>Gandhi</last></author></paper>",
        "<paper><author><last>Gandhi</last></author></paper>",
        True,
    ),
    (  # Switching the order of bibkey, doi, title, etc. is logically equivalent
        """<paper>
             <author><first>Peter</first><last>Parker</last></author>
             <title>On the reordering of XML elements</title>
             <bibkey>parker-2025-reordering</bibkey>
             <doi>10.18653/v1/2025.xml-conference.1</doi>
             <note>This paper doesn't exist.</note>
           </paper>""",
        """<paper>
             <title>On the reordering of XML elements</title>
             <author><first>Peter</first><last>Parker</last></author>
             <note>This paper doesn't exist.</note>
             <doi>10.18653/v1/2025.xml-conference.1</doi>
             <bibkey>parker-2025-reordering</bibkey>
           </paper>""",
        True,
    ),
    (  # Changing an attribute is NOT logically equivalent
        '<paper id="1"><author><first>Peter</first><last>Parker</last></author></paper>',
        '<paper id="2"><author><first>Peter</first><last>Parker</last></author></paper>',
        False,
    ),
    (  # Switching author order is NOT logically equivalent
        """<paper>
             <author><first>Peter</first><last>Parker</last></author>
             <author><first>Bonnie</first><last>Taylor</last></author>
           </paper>""",
        """<paper>
             <author><first>Bonnie</first><last>Taylor</last></author>
             <author><first>Peter</first><last>Parker</last></author>
           </paper>""",
        False,
    ),
    (  # Switching editor order is NOT logically equivalent
        """<frontmatter>
             <editor><first>Peter</first><last>Parker</last></editor>
             <editor><first>Bonnie</first><last>Taylor</last></editor>
           </frontmatter>""",
        """<frontmatter>
             <editor><first>Bonnie</first><last>Taylor</last></editor>
             <editor><first>Peter</first><last>Parker</last></editor>
           </frontmatter>""",
        False,
    ),
    (  # Elements in <title> may NOT be reordered
        "<title><b>Bold</b><i>Italics</i></title>",
        "<title><i>Italics</i><b>Bold</b></title>",
        False,
    ),
)


@pytest.mark.parametrize("a, b, should_be_equal", test_cases_assert_equals)
def test_xml_assert_equals(a, b, should_be_equal):
    root_a = etree.fromstring(a)
    root_b = etree.fromstring(b)
    if should_be_equal:
        xml.assert_equals(root_a, root_b)
    else:
        with pytest.raises(AssertionError):
            xml.assert_equals(root_a, root_b)
