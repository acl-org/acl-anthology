# Copyright 2023-2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Is it cheaper to parse an <author> element via .findtext() lookups or by
iterating over its children once?"""

import pytest
from lxml import etree

SAMPLE_XML = """
<list-of-authors>
  <author>
    <first>John</first><last>Doe</last>
  </author>
  <author id="john-doe-42">
    <first>John</first><last>Doe</last>
  </author>
  <author>
    <first>Matt</first>
    <last>Post</last>
    <affiliation>Johns Hopkins University</affiliation>
  </author>
  <author>
    <first>Weiguang</first>
    <last>Qu</last>
    <variant script="hani">
      <first>维光</first><last>曲</last>
    </variant>
  </author>
</list-of-authors>
"""


def parse_with_findtext(element):
    return [
        element.findtext("first"),
        element.findtext("last"),
        element.get("id"),
        element.findtext("affiliation"),
        [child.get("script") for child in element.iterchildren("variant")],
    ]


def parse_with_iter(element):
    first, last, affiliation = None, None, None
    variants = []
    for child in element:
        if child.tag == "first":
            first = child.text
        elif child.tag == "last":
            last = child.text
        elif child.tag == "affiliation":
            affiliation = child.text
        elif child.tag == "variant":
            variants.append(child.get("script"))  # simplification
    return [first, last, element.get("id"), affiliation, variants]


@pytest.fixture(scope="module")
def author_elements():
    return list(etree.fromstring(SAMPLE_XML))


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "parse_fn", [parse_with_findtext, parse_with_iter], ids=["findtext", "iterate"]
)
def test_parse_author_name(benchmark, author_elements, parse_fn):
    def parse_all():
        return [parse_fn(author) for author in author_elements]

    benchmark(parse_all)
