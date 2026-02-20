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

from acl_anthology.people import Name, NameSpecification
from lxml import etree
import itertools as it
import pytest


def test_name_firstlast():
    n1 = Name("John", "Doe")
    assert n1.first == "John"
    assert n1.last == "Doe"
    assert n1.as_first_last() == "John Doe"
    assert n1.as_last_first() == "Doe, John"
    assert n1.as_full() == "John Doe"
    assert n1.as_bibtex() == "Doe, John"
    n2 = Name(last="Doe", first="John")
    assert n1 == n2
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
    assert n1.as_last_first() == "Mausam"
    assert n1.as_full() == "Mausam"
    assert n1.as_bibtex() == "Mausam"


def test_name_onlylast_none_vs_empty_string():
    n1 = Name(None, "Mausam")
    n2 = Name("", "Mausam")
    assert n1.as_first_last() == n2.as_first_last()
    assert n1.as_last_first() == n2.as_last_first()
    assert n1.as_full() == n2.as_full()
    assert n1.as_bibtex() == n2.as_bibtex()
    assert n1 == n2


def test_name_specification():
    n1 = NameSpecification(Name("John", "Doe"))
    n2 = NameSpecification(Name("John", "Doe"))
    assert n1 == n2


def test_name_specification_converter():
    n1 = NameSpecification(("John", "Doe"))
    n2 = NameSpecification("Doe, John")
    n3 = NameSpecification({"first": "John", "last": "Doe"})
    assert n1 == n2 == n3


def test_name_spec_citeproc():
    n1 = NameSpecification(Name("John", "Doe"))
    assert n1.citeproc_dict == {"family": "Doe", "given": "John"}
    n2 = NameSpecification(Name(None, "Mausam"))
    assert n2.citeproc_dict == {"family": "Mausam"}


def test_name_spec_with_affiliation():
    name = Name("John", "Doe")
    ns1 = NameSpecification(name)
    ns2 = NameSpecification(name, affiliation="University of Someplace")
    assert ns1 != ns2
    assert ns1.name == ns2.name
    assert ns1.affiliation is None
    assert ns2.affiliation == "University of Someplace"


def test_name_spec_with_id():
    name = Name("John", "Doe")
    ns1 = NameSpecification(name)
    ns2 = NameSpecification(name, "john-doe-42")
    assert ns1 != ns2
    assert ns1.id is None
    assert ns2.id == "john-doe-42"


def test_name_with_script():
    n1 = Name("大文", "陳", "hani")
    n2 = Name("大文", "陳")
    assert n1.first == "大文"
    assert n1.last == "陳"
    assert n1.script == "hani"
    assert n1.as_full() == "陳大文"
    # Script information is NOT distinctive, so names should still compare equal
    assert n1 == n2


def test_name_spec_with_variant():
    name = Name("Tai Man", "Chan")
    nv = Name("大文", "陳", "hani")
    ns1 = NameSpecification(name)
    ns2 = NameSpecification(name, variants=[nv])
    assert ns1 != ns2
    assert ns2.variants[0] == nv


def test_name_spec_from_xml():
    xml = """
        <author id='john-doe-42'>
          <first>John</first><last>Doe</last>
          <affiliation>UOS</affiliation>
        </author>"""
    element = etree.fromstring(xml)
    ns = NameSpecification.from_xml(element)
    assert ns.first == "John"
    assert ns.last == "Doe"
    assert ns.name == Name("John", "Doe")
    assert ns.id == "john-doe-42"
    assert ns.affiliation == "UOS"


def test_name_spec_to_xml():
    xml = '<author id="john-doe-42"><first>John</first><last>Doe</last><affiliation>UOS</affiliation></author>'
    element = NameSpecification.from_xml(etree.fromstring(xml)).to_xml("author")
    assert etree.tostring(element, encoding="unicode") == xml


def test_name_spec_to_xml_onlylast():
    xml = "<editor><first/><last>Mausam</last></editor>"
    element = NameSpecification.from_xml(etree.fromstring(xml)).to_xml("editor")
    assert etree.tostring(element, encoding="unicode") == xml


def test_name_spec_to_xml_with_id_and_orcid():
    xml = '<editor id="mausam" orcid="0000-0003-4088-4296"><first/><last>Mausam</last></editor>'
    element = NameSpecification.from_xml(etree.fromstring(xml)).to_xml("editor")
    assert etree.tostring(element, encoding="unicode") == xml


class CollectionMock:
    def __init__(self):
        self.is_modified = False


class NameSpecParent:
    def __init__(self):
        self.collection = CollectionMock()


@pytest.fixture
def parent():
    return NameSpecParent()


@pytest.mark.parametrize(
    "attr_name",
    (
        "id",
        "name",
        "orcid",
        "affiliation",
        "variants",
    ),
)
def test_namespec_setattr_sets_parentcollection_is_modified(attr_name, parent):
    namespec = NameSpecification(
        name=Name("Xinyue", "Lou"),
        id="xinyue-lou",
        orcid="0009-0001-8460-3882",
        affiliation=None,
        variants=[Name("馨月", "娄")],
        parent=parent,
    )
    assert not parent.collection.is_modified
    setattr(namespec, attr_name, getattr(namespec, attr_name))
    assert parent.collection.is_modified


def test_name_variant_from_xml():
    xml = """
        <variant script="hani">
          <last>陳</last><first>大文</first>
        </variant>
    """
    element = etree.fromstring(xml)
    nv = Name.from_xml(element)
    assert nv.first == "大文"
    assert nv.last == "陳"
    assert nv.script == "hani"


def test_name_variant_to_xml():
    xml = '<variant script="hani"><first>大文</first><last>陳</last></variant>'
    element = Name.from_xml(etree.fromstring(xml)).to_xml()
    assert etree.tostring(element, encoding="unicode") == xml


def test_name_variant_to_xml_onlylast():
    xml = "<variant><first/><last>陳</last></variant>"
    element = Name.from_xml(etree.fromstring(xml)).to_xml()
    assert etree.tostring(element, encoding="unicode") == xml


test_cases_slugify = (
    # Should slugify to the same thing
    (
        [
            ("Tai Man", "Chan"),
            ("Tai", "Man Chan"),
            ("Tai-Man", "Chan"),
            (None, "Tai Man Chan"),
        ],
        True,
    ),
    (
        [
            ("James", "O'Neill"),
            ("James", "OʼNeill"),
            ("James", "O’Neill"),
            ("James", "O`Neill"),
        ],
        True,
    ),
    ([("A", "B-C"), ("A", "B–C"), ("A", "B—C")], True),
    ([("Charles M.", "King"), ("Charles M", "King")], True),
    ([("澳", "李"), ("Ao", "Li")], True),
    # Should NOT slugify to the same thing
    ([("Tai Man", "Chan"), ("TaiMan", "Chan")], False),
)


@pytest.mark.parametrize("names, should_match", test_cases_slugify)
def test_name_slugify(names, should_match):
    for a, b in it.combinations(names, 2):
        if should_match:
            assert Name(*a).slugify() == Name(*b).slugify()
        else:
            assert Name(*a).slugify() != Name(*b).slugify()


def test_name_scoring():
    n1 = Name("Andre", "Rieu")
    n2 = Name("André", "Rieu")
    n3 = Name("ANdre", "Rieu")
    n4 = Name("Andre", "rieu")
    n5 = Name("Andres", "Rieu")
    assert n1.score() < n2.score()
    assert n1.score() > n3.score()
    assert n1.score() > n4.score()
    assert n1.score() < n5.score()


def test_name_scoring_umlauts():
    n1 = Name("Gokhan", "Tur")
    n2 = Name("Gökhan", "Tür")
    assert n1.score() < n2.score()


def test_name_scoring_dashes():
    n1 = Name("Pascual", "Martínez Gómez")
    n2 = Name("Pascual", "Martínez-Gómez")
    assert n1.score() < n2.score()


def test_name_scoring_first_vs_last_name():
    n1 = Name("Chan Tai", "Man")
    n2 = Name("Chan", "Tai Man")
    assert n1.score() > n2.score()


def test_name_from_string():
    n1 = Name.from_string("André Rieu")
    n2 = Name.from_string("Rieu, André")
    assert n1.first == "André"
    assert n1.last == "Rieu"
    assert n1 == n2
    n3 = Name.from_string("Chan, Tai Man")
    assert n3.first == "Tai Man"
    assert n3.last == "Chan"
    with pytest.raises(ValueError):
        Name.from_string("Tai Man Chan")
    n4 = Name.from_string("Mausam")
    assert n4.first is None
    assert n4.last == "Mausam"


def test_name_from_any():
    n1 = Name.from_("Jane Doe")
    n2 = Name.from_({"first": "Jane", "last": "Doe"})
    n3 = Name.from_(("Jane", "Doe"))
    n4 = Name.from_(n1)
    assert n1 == n2 == n3 == n4
    with pytest.raises(TypeError):
        Name.from_(["Jane", "Doe"])  # ... but could be allowed maybe?


def test_name_as_bibtex():
    n1 = Name.from_string("André Rieu")
    assert n1.as_bibtex() == "Rieu, Andr{\\'e}"
