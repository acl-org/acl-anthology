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

test_cases_stringify_children = (
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
        "<title>With <b>nested <i>markup with subsequent closing tags</i></b></title>\n",
    ),
    (
        "<abstract>Text where URL is followed by text: <url>https://aclanthology.org/</url>!</abstract>",
        "<abstract>Text where URL is followed by text: <url>https://aclanthology.org/</url>!</abstract>\n",
    ),
    (
        "<abstract>Text that ends in a URL: <url>https://aclanthology.org/</url></abstract>",
        "<abstract>Text that ends in a URL: <url>https://aclanthology.org/</url></abstract>\n",
    ),
    (
        """<collection id="W14">
  <volume id="1">
    <meta>
      <booktitle>  Proceedings of the Seventh Global <fixed-case>Wordnet</fixed-case> Conference </booktitle>
      <editor><first>Heili</first><last>Orav</last></editor>
      <editor><first>Christiane</first><last>Fellbaum</last></editor>
    <editor><first>Piek
           </first><last>Vossen</last>
           </editor>
     <publisher>University of Tartu Press</publisher>
     <address>Tartu, Estonia</address>
     <month>January</month>
   <year>2014</year>
   </meta>
                  <frontmatter>
      <url>W14-0100</url>
    </frontmatter>
    <paper id="1">
      <title> <fixed-case>W</fixed-case>o<fixed-case>N</fixed-case>e<fixed-case>F</fixed-case>, an improved, expanded and evaluated automatic <fixed-case>F</fixed-case>rench translation of <fixed-case>W</fixed-case>ord<fixed-case>N</fixed-case>et
    </title>
    <author>
      <first  >Quentin</first><last>Pradet   </last>
</author>
<pages>32-39</pages>
<url>W14-0105</url>
</paper>
  <paper>
      <title><fixed-case>K</fixed-case>yoto<fixed-case>EBMT</fixed-case> System Description for the 1st Workshop on <fixed-case>A</fixed-case>sian Translation</title></paper>
  </volume>
    </collection>""",
        """<collection id="W14">
  <volume id="1">
    <meta>
      <booktitle>Proceedings of the Seventh Global <fixed-case>Wordnet</fixed-case> Conference</booktitle>
      <editor><first>Heili</first><last>Orav</last></editor>
      <editor><first>Christiane</first><last>Fellbaum</last></editor>
      <editor><first>Piek</first><last>Vossen</last></editor>
      <publisher>University of Tartu Press</publisher>
      <address>Tartu, Estonia</address>
      <month>January</month>
      <year>2014</year>
    </meta>
    <frontmatter>
      <url>W14-0100</url>
    </frontmatter>
    <paper id="1">
      <title><fixed-case>W</fixed-case>o<fixed-case>N</fixed-case>e<fixed-case>F</fixed-case>, an improved, expanded and evaluated automatic <fixed-case>F</fixed-case>rench translation of <fixed-case>W</fixed-case>ord<fixed-case>N</fixed-case>et</title>
      <author><first>Quentin</first><last>Pradet</last></author>
      <pages>32-39</pages>
      <url>W14-0105</url>
    </paper>
    <paper>
      <title><fixed-case>K</fixed-case>yoto<fixed-case>EBMT</fixed-case> System Description for the 1st Workshop on <fixed-case>A</fixed-case>sian Translation</title>
    </paper>
  </volume>
</collection>
""",
    ),
)


@pytest.mark.parametrize("inp, child, out", test_cases_stringify_children)
def test_xml_stringify_children(inp, child, out):
    element = etree.fromstring(inp)
    if child is not None:
        element = element.find(child)
    assert xml.stringify_children(element) == out


@pytest.mark.parametrize("inp, out", test_cases_indent)
def test_xml_indent(inp, out):
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


test_cases_ensure_minimal_diff = (
    (  # Attributes should always be reordered
        '<attachment type="software" hash="fc212cbc"/>',  # elem
        '<attachment hash="fc212cbc" type="software"/>',  # reference
        '<attachment hash="fc212cbc" type="software"/>',  # expected result
    ),
    (
        '<volume id="1" ingest-date="2022-11-22" type="proceedings"/>',
        '<volume id="1" type="proceedings" ingest-date="2022-11-22"/>',
        '<volume id="1" type="proceedings" ingest-date="2022-11-22"/>',
    ),
    (  # ...including when they've been changed
        '<volume id="8" ingest-date="2022-11-22" type="journal"/>',
        '<volume id="1" type="proceedings" ingest-date="2022-11-22"/>',
        '<volume id="8" type="journal" ingest-date="2022-11-22"/>',
    ),
    (  # Author tags should NOT be reordered
        """<paper>
             <author><first>Peter</first><last>Parker</last></author>
             <author><first>Bonnie</first><last>Taylor</last></author>
           </paper>""",
        """<paper>
             <author><first>Bonnie</first><last>Taylor</last></author>
             <author><first>Peter</first><last>Parker</last></author>
           </paper>""",
        """<paper>
             <author><first>Peter</first><last>Parker</last></author>
             <author><first>Bonnie</first><last>Taylor</last></author>
           </paper>""",
    ),
    (  # Editor tags should NOT be reordered
        """<frontmatter>
             <editor><first>Peter</first><last>Parker</last></editor>
             <editor><first>Bonnie</first><last>Taylor</last></editor>
           </frontmatter>""",
        """<frontmatter>
             <editor><first>Bonnie</first><last>Taylor</last></editor>
             <editor><first>Peter</first><last>Parker</last></editor>
           </frontmatter>""",
        """<frontmatter>
             <editor><first>Peter</first><last>Parker</last></editor>
             <editor><first>Bonnie</first><last>Taylor</last></editor>
           </frontmatter>""",
    ),
    (  # Logically equivalent tags should be reordered
        """<paper id="1">
             <author><first>Peter</first><last>Parker</last></author>
             <title>On the reordering of XML elements</title>
             <bibkey>parker-2025-reordering</bibkey>
             <doi>10.18653/v1/2025.xml-conference.1</doi>
             <note>This paper doesn't exist.</note>
           </paper>""",
        """<paper id="1">
             <title>On the reordering of XML elements</title>
             <author><first>Peter</first><last>Parker</last></author>
             <note>This paper doesn't exist.</note>
             <doi>10.18653/v1/2025.xml-conference.1</doi>
             <bibkey>parker-2025-reordering</bibkey>
           </paper>""",
        """<paper id="1">
             <title>On the reordering of XML elements</title>
             <author><first>Peter</first><last>Parker</last></author>
             <note>This paper doesn't exist.</note>
             <doi>10.18653/v1/2025.xml-conference.1</doi>
             <bibkey>parker-2025-reordering</bibkey>
           </paper>""",
    ),
    (  # ...even when their content has changed
        """<paper id="1">
             <author><first>Peter</first><last>Parker</last></author>
             <title>On the logical reordering of XML elements</title>
             <bibkey>parker-2025-logical</bibkey>
             <doi>10.18653/v1/2025.xml-conference.32</doi>
             <note>This paper still doesn't exist.</note>
           </paper>""",
        """<paper id="1">
             <title>On the reordering of XML elements</title>
             <author><first>Peter</first><last>Parker</last></author>
             <note>This paper doesn't exist.</note>
             <doi>10.18653/v1/2025.xml-conference.1</doi>
             <bibkey>parker-2025-reordering</bibkey>
           </paper>""",
        """<paper id="1">
             <title>On the logical reordering of XML elements</title>
             <author><first>Peter</first><last>Parker</last></author>
             <note>This paper still doesn't exist.</note>
             <doi>10.18653/v1/2025.xml-conference.32</doi>
             <bibkey>parker-2025-logical</bibkey>
           </paper>""",
    ),
    (  # Reordering should recurse into child elements
        """<volume id="long">
             <paper id="1">
               <author><first>Peter</first><last>Parker</last></author>
               <title>On the logical reordering of XML elements</title>
               <bibkey>parker-2025-logical</bibkey>
               <doi>10.18653/v1/2025.xml-conference.32</doi>
               <note>This paper still doesn't exist.</note>
             </paper>
           </volume>""",
        """<volume id="long">
             <paper id="1">
               <title>On the reordering of XML elements</title>
               <author><first>Peter</first><last>Parker</last></author>
               <note>This paper doesn't exist.</note>
               <doi>10.18653/v1/2025.xml-conference.1</doi>
               <bibkey>parker-2025-reordering</bibkey>
             </paper>
           </volume>""",
        """<volume id="long">
             <paper id="1">
               <title>On the logical reordering of XML elements</title>
               <author><first>Peter</first><last>Parker</last></author>
               <note>This paper still doesn't exist.</note>
               <doi>10.18653/v1/2025.xml-conference.32</doi>
               <bibkey>parker-2025-logical</bibkey>
             </paper>
           </volume>""",
    ),
    (  # If logically equivalent, reference will just be copied
        """<paper>
             <author><first>Peter</first><last>Parker</last></author>
           </paper>""",
        """<paper>
             <author><first>Peter</first><last>Parker</last></author>
             <pages/>
           </paper>""",
        """<paper>
             <author><first>Peter</first><last>Parker</last></author>
             <pages/>
           </paper>""",
    ),
    (
        "<author><first/><last>Parker</last></author>",
        "<author><last>Parker</last></author>",
        "<author><last>Parker</last></author>",
    ),
    (
        "<author><last>Parker</last></author>",
        "<author><first/><last>Parker</last></author>",
        "<author><first/><last>Parker</last></author>",
    ),
    (
        '<paper><revision id="1"/></paper>',
        '<paper><revision id="1"></revision></paper>',
        '<paper><revision id="1"></revision></paper>',
    ),
    (
        '<paper><revision id="1"></revision></paper>',
        '<paper><revision id="1"/></paper>',
        '<paper><revision id="1"/></paper>',
    ),
    (  # Complex reordering with multiple, order-sensitive child tags is not supported -- but if logically equivalent, reference will just be copied
        """<paper>
             <attachment type="software" hash="079d4f4a">2022.acl-long.48.software.txt</attachment>
             <attachment type="software" hash="079d4f4b">2022.acl-long.48.software.zip</attachment>
             <bibkey>feng-etal-2022-legal</bibkey>
           </paper>""",
        """<paper>
             <attachment type="software" hash="079d4f4a">2022.acl-long.48.software.txt</attachment>
             <bibkey>feng-etal-2022-legal</bibkey>
             <attachment type="software" hash="079d4f4b">2022.acl-long.48.software.zip</attachment>
           </paper>""",
        """<paper>
             <attachment type="software" hash="079d4f4a">2022.acl-long.48.software.txt</attachment>
             <bibkey>feng-etal-2022-legal</bibkey>
             <attachment type="software" hash="079d4f4b">2022.acl-long.48.software.zip</attachment>
           </paper>""",
    ),
)


@pytest.mark.parametrize("a, b, c", test_cases_ensure_minimal_diff)
def test_xml_ensure_minimal_diff(a, b, c):
    elem, reference, target = (
        etree.fromstring(a),
        etree.fromstring(b),
        etree.fromstring(c),
    )
    # Match elem to reference
    xml.ensure_minimal_diff(elem, reference)
    # Make sure that any difference is not just due to indentation
    xml.indent(elem), xml.indent(target)
    matched, expected = etree.tounicode(elem), etree.tounicode(target)
    assert expected == matched
