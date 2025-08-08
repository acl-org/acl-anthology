# Copyright 2023-2025 Marcel Bollmann <marcel@bollmann.me>
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
from acl_anthology.exceptions import NameSpecResolutionError
from acl_anthology.people import Name, NameSpecification, Person, PersonIndex


@pytest.fixture
def index(anthology_stub):
    return PersonIndex(anthology_stub)


@pytest.fixture
def index_with_full_anthology(anthology):
    return PersonIndex(anthology)


def test_load_people_index(index):
    index._load_people_index()
    index.is_data_loaded = True
    for pid in (
        "emily-prudhommeaux",
        "steven-krauwer",
        "yang-liu-icsi",
        "yang-liu-ict",
        "yang-liu-microsoft",
    ):
        assert pid in index


def test_load_people_index_registers_names(index):
    index._load_people_index()
    index.is_data_loaded = True
    n1 = Name("Steven", "Krauwer")
    n2 = Name("S.", "Krauwer")
    assert n1 in index.by_name
    assert n2 in index.by_name
    pid = index.by_name[n1]
    assert pid == index.by_name[n2]
    assert pid[0] in index


def test_add_person(index):
    p1 = Person("yang-liu", index.parent, [Name("Yang", "Liu")])
    index.add_person(p1)
    index.is_data_loaded = True  # to prevent it attempting to build itself
    assert "yang-liu" in index
    assert Name("Yang", "Liu") in index.by_name
    assert index.by_name[Name("Yang", "Liu")] == ["yang-liu"]
    assert index.get_by_name(Name("Yang", "Liu"))[0] is p1
    assert index.get_by_namespec(NameSpecification(Name("Yang", "Liu"))) is p1
    assert index.get("yang-liu") is p1
    with pytest.raises(KeyError):
        index.add_person(Person("yang-liu", index.parent))


def test_similar_names_defined_in_people_index(index):
    index._load_people_index()
    similar = index.similar.subset("pranav-a")
    assert similar == {"pranav-a", "pranav-anand"}


def test_similar_names_through_same_canonical_name(index):
    index._load_people_index()
    similar = index.similar.subset("yang-liu-ict")
    assert similar == {
        "yang-liu-icsi",
        "yang-liu-ict",
        "yang-liu-microsoft",
    }


def test_build_personindex(index_with_full_anthology):
    index = index_with_full_anthology
    assert not index.is_data_loaded
    index.build(show_progress=False)
    assert index.is_data_loaded
    assert "yang-liu-microsoft" in index
    assert Name("Nicoletta", "Calzolari") in index.by_name


def test_build_personindex_automatically(index_with_full_anthology):
    index = index_with_full_anthology
    assert not index.is_data_loaded
    persons = index.get_by_name(Name("Nicoletta", "Calzolari"))
    assert index.is_data_loaded
    assert len(persons) == 1


def test_canonical_name_is_never_a_variant(index_with_full_anthology):
    index = index_with_full_anthology
    for person in index.values():
        assert person.canonical_name.script is None


# TODO: add tests for resolve_namespec()
# - test name resolution logic
# - test exceptions that can be raised


def test_get_person_coauthors(index_with_full_anthology):
    index = index_with_full_anthology
    person = index.get_by_name(Name("Kathleen", "Dahlgren"))[0]
    coauthors = index.find_coauthors(person)
    assert len(coauthors) == 1
    assert coauthors[0].canonical_name == Name("Joyce", "McDowell")

    person = index.get_by_name(Name("Preslav", "Nakov"))[0]
    coauthors = index.find_coauthors(person)
    assert len(coauthors) == 2
    # Both volumes where Preslav Nakov is editor have frontmatter, so should still be counted
    coauthors = index.find_coauthors(person, include_volumes=False)
    assert len(coauthors) == 2


def test_get_person_coauthors_counter(index_with_full_anthology):
    index = index_with_full_anthology
    person = index.get_by_name(Name("Kathleen", "Dahlgren"))[0]
    coauthors = index.find_coauthors_counter(person)
    assert len(coauthors) == 1
    assert coauthors["unverified/joyce-mcdowell"] == 1

    person = index.get_by_name(Name("Preslav", "Nakov"))[0]
    coauthors = index.find_coauthors_counter(person)
    assert len(coauthors) == 2
    assert coauthors["unverified/joyce-mcdowell"] == 0
    assert coauthors["unverified/aline-villavicencio"] == 2


def test_get_by_namespec(index_with_full_anthology):
    index = index_with_full_anthology
    ns1 = NameSpecification(Name("Yang", "Liu"))
    ns2 = NameSpecification(Name("Yang", "Liu"), id="yang-liu-microsoft")
    with pytest.raises(NameSpecResolutionError):
        index.get_by_namespec(ns1)
    person = index.get_by_namespec(ns2)
    assert person.id == "yang-liu-microsoft"
    assert person.canonical_name == Name("Yang", "Liu")


def test_get_by_name_variants(index_with_full_anthology):
    # It should be possible to find a person by a name variant
    index = index_with_full_anthology
    persons = index.get_by_name(Name("洋", "刘"))
    assert len(persons) == 1
    assert persons[0].id == "yang-liu-ict"


def test_get_by_orcid(index_with_full_anthology):
    index = index_with_full_anthology
    person = index.get_by_orcid("0000-0003-2598-8150")
    assert person is not None
    assert person.id == "marcel-bollmann"
