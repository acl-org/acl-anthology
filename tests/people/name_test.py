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

from acl_anthology.people import Name, NameVariant
from lxml import etree
import itertools as it
import pytest


def test_name_firstlast():
    n1 = Name("John", "Doe")
    assert n1.first == "John"
    assert n1.last == "Doe"
    assert n1.as_first_last() == "John Doe"
    n2 = Name(last="Doe", first="John")
    assert n1 == n2
    assert n1.match(n2)
    assert n2.match(n1)
    assert n2.as_first_last() == "John Doe"


def test_name_onlylast():
    with pytest.raises(TypeError):
        # This is error-prone, so it should fail
        Name("Mausam")
    # Empty first name needs to be given explicitly
    n1 = Name(None, "Mausam")
    assert n1.first is None
    assert n1.last == "Mausam"
    assert n1.as_first_last() == "Mausam"


def test_name_with_affiliation():
    n1 = Name("John", "Doe")
    n2 = Name("John", "Doe", affiliation="University of Someplace")
    assert n1 != n2
    assert n1.match(n2)
    assert n2.match(n1)
    assert n1.as_first_last() == n2.as_first_last()
    assert n1.affiliation is None
    assert n2.affiliation == "University of Someplace"


def test_name_with_id():
    n1 = Name("John", "Doe")
    n2 = Name("John", "Doe", "john-doe-42")
    assert n1 != n2
    assert n1.match(n2)
    assert n2.match(n1)
    assert n1.as_first_last() == n2.as_first_last()
    assert n1.id is None
    assert n2.id == "john-doe-42"


def test_name_variant():
    with pytest.raises(TypeError):
        # Name variants must have a script argument
        NameVariant("大文", "陳")
    nv = NameVariant("大文", "陳", "hani")
    assert nv.first == "大文"
    assert nv.last == "陳"
    assert nv.script == "hani"


def test_name_with_variant():
    n1 = Name("Tai Man", "Chan")
    nv = NameVariant("大文", "陳", "hani")
    n2 = Name("Tai Man", "Chan", variants=[nv])
    assert n1 != n2
    assert n1.match(n2)
    assert n2.match(n1)
    assert n1.as_first_last() == n2.as_first_last()
    assert n2.variants[0] == nv


def test_name_from_xml():
    xml = """
        <author id='john-doe-42'>
          <first>John</first><last>Doe</last>
          <affiliation>UOS</affiliation>
        </author>"""
    element = etree.fromstring(xml)
    n = Name.from_xml(element)
    assert n.first == "John"
    assert n.last == "Doe"
    assert n.id == "john-doe-42"
    assert n.affiliation == "UOS"


def test_name_variant_from_xml():
    xml = """
        <variant script="hani">
          <last>陳</last><first>大文</first>
        </variant>
    """
    element = etree.fromstring(xml)
    nv = NameVariant.from_xml(element)
    assert nv.first == "大文"
    assert nv.last == "陳"
    assert nv.script == "hani"


def test_name_mismatch():
    n1 = Name("Tai Man", "Chan")
    n2 = Name("Tai", "Mai Chan")
    n3 = Name("Tai-Man", "Chan")
    n4 = Name("Tai Man", "Chen")
    for a, b in it.combinations((n1, n2, n3, n4), 2):
        assert a != b
        assert not a.match(b)
        assert not b.match(a)
