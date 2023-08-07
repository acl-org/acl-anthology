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
from acl_anthology.exceptions import AmbiguousNameError, NameIDUndefinedError
from acl_anthology.people import Name, NameSpecification, Person, PersonIndex


@pytest.fixture
def index(anthology_stub):
    return PersonIndex(anthology_stub)


@pytest.fixture
def index_with_full_anthology(anthology):
    return PersonIndex(anthology)


def test_load_variant_list(index):
    index._load_variant_list()
    for pid in (
        "pranav-a",
        "pranav-anand",
        "yang-liu-edinburgh",
        "yang-liu-icsi",
        "yang-liu-ict",
        "yang-liu-microsoft",
        "steven-krauwer",
    ):
        assert pid in index.people


def test_load_variant_list_correct_variants(index):
    index._load_variant_list()
    n1 = Name("Susan", "Armstrong")
    n2 = Name("Susan", "Warwick")
    assert n1 in index.name_to_ids
    assert n2 in index.name_to_ids
    pid = index.name_to_ids[n1]
    assert pid == index.name_to_ids[n2]
    assert pid[0] in index.people


def test_add_person(index):
    p1 = Person("yang-liu", [Name("Yang", "Liu")])
    index.add_person(p1)
    index.is_built = True
    assert "yang-liu" in index.people
    assert Name("Yang", "Liu") in index.name_to_ids
    assert index.name_to_ids[Name("Yang", "Liu")] == ["yang-liu"]
    assert index.get_by_name(Name("Yang", "Liu"))[0] is p1
    assert index.get("yang-liu") is p1
    with pytest.raises(KeyError):
        index.add_person(Person("yang-liu"))


def test_get_or_create_person_with_id(index):
    ns1 = NameSpecification(Name("Yang", "Liu"), id="yang-liu-icsi")
    ns2 = NameSpecification(Name("Y.", "Liu"), id="yang-liu-icsi")
    with pytest.raises(NameIDUndefinedError):
        index.get_or_create_person(ns1)
    index._load_variant_list()
    person1 = index.get_or_create_person(ns1)
    assert person1.id == "yang-liu-icsi"
    person2 = index.get_or_create_person(ns2)
    assert person1 is person2
    assert person1 is index.people["yang-liu-icsi"]
    assert person1.has_name(Name("Yang", "Liu"))
    assert person1.has_name(Name("Y.", "Liu"))


def test_get_or_create_person_new_person(index):
    ns1 = NameSpecification(Name("Yang", "Liu"))
    ns2 = NameSpecification(Name("Yang", "Liu"), affiliation="University of Edinburgh")
    person1 = index.get_or_create_person(ns1)
    assert person1.has_name(Name("Yang", "Liu"))
    person2 = index.get_or_create_person(ns2)
    assert person1 is person2
    assert person1 is index.people[person1.id]


def test_get_or_create_person_with_ambiguous_name(index):
    index._load_variant_list()
    ns1 = NameSpecification(Name("Yang", "Liu"))
    ns2 = NameSpecification(Name("Yang", "Liu"), id="yang-liu-icsi")
    with pytest.raises(AmbiguousNameError):
        index.get_or_create_person(ns1)
    person = index.get_or_create_person(ns2)
    assert person.id == "yang-liu-icsi"


def test_get_or_create_person_with_name_merging(index):
    ns1 = NameSpecification(Name("John", "Neumann"))
    ns2 = NameSpecification(Name("Jöhn", "Néumänn"))
    person1 = index.get_or_create_person(ns1)
    person2 = index.get_or_create_person(ns2)
    assert person1 is person2
    assert person2.has_name(ns1.name)
    assert person2.has_name(ns2.name)
    assert person2.canonical_name == ns2.name


def test_similar_names_defined_in_variant_list(index):
    index._load_variant_list()
    similar = index.similar.subset("pranav-a")
    assert similar == {"pranav-a", "pranav-anand"}


def test_similar_names_through_same_canonical_name(index):
    index._load_variant_list()
    similar = index.similar.subset("yang-liu-ict")
    assert similar == {
        "yang-liu-edinburgh",
        "yang-liu-icsi",
        "yang-liu-ict",
        "yang-liu-microsoft",
    }


def test_build_personindex(index_with_full_anthology):
    index = index_with_full_anthology
    assert not index.is_built
    index.build(show_progress=False)
    assert index.is_built
    assert "yang-liu-microsoft" in index.people
    assert Name("Nicoletta", "Calzolari") in index.name_to_ids


def test_build_personindex_automatically(index_with_full_anthology):
    index = index_with_full_anthology
    assert not index.is_built
    persons = index.get_by_name(Name("Nicoletta", "Calzolari"))
    assert index.is_built
    assert len(persons) == 1


def test_get_person_coauthors(index_with_full_anthology):
    index = index_with_full_anthology
    person = index.get_by_name(Name("Kathleen", "Dahlgren"))[0]
    coauthors = index.find_coauthors(person)
    assert len(coauthors) == 1
    assert coauthors[0].canonical_name == Name("Joyce", "McDowell")
