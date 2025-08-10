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
from acl_anthology.people import Name, NameLink, Person


def test_person_names(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    n3 = Name("Yang X.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1, n2])
    assert len(person.names) == 2
    assert person.has_name(n1)
    assert person.has_name(n2)
    assert not person.has_name(n3)


def test_person_canonical_name(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1, n2])
    assert person.canonical_name == n1
    person.set_canonical_name(n2)
    assert person.canonical_name == n2
    assert len(person.names) == 2


def test_person_add_name(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1])
    assert person.canonical_name == n1
    person.set_canonical_name(n2)
    assert person.canonical_name == n2
    assert len(person.names) == 2
    n3 = Name("Yang X.", "Liu")
    person.add_name(n3)
    assert person.canonical_name == n2
    assert len(person.names) == 3


def test_person_remove_name(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1, n2])
    assert person.has_name(n2)
    person.remove_name(n2)
    assert not person.has_name(n2)
    assert len(person.names) == 1


def test_person_names_explicit_vs_inferred(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1])
    assert (n1, NameLink.EXPLICIT) in person._names
    person.set_canonical_name(n2)
    assert (n2, NameLink.EXPLICIT) in person._names
    n3 = Name("Yang X.", "Liu")
    person.add_name(n3, inferred=True)
    assert (n3, NameLink.INFERRED) in person._names


def test_person_no_name(anthology_stub):
    person = Person("yang-liu", anthology_stub, [])
    assert len(person.names) == 0
    with pytest.raises(ValueError):
        person.canonical_name
    name = Name("Yang", "Liu")
    person.set_canonical_name(name)
    assert len(person.names) == 1
    assert person.canonical_name == name


def test_person_set_canonical_name(anthology_stub):
    person = Person("rene-muller", anthology_stub, [Name("Rene", "Muller")])
    assert len(person.names) == 1
    name = Name("René", "Müller")
    person.set_canonical_name(name)
    assert len(person.names) == 2
    assert person.canonical_name == name


def test_person_orcid(anthology_stub):
    person = Person(
        "marcel-bollmann",
        anthology_stub,
        [Name("Marcel", "Bollmann")],
        orcid="0000-0002-1297-6794",
    )
    assert person.orcid == "0000-0002-1297-6794"
    person.orcid = "0000-0003-2598-8150"
    assert person.orcid == "0000-0003-2598-8150"
    with pytest.raises(ValueError):
        person.orcid = "https://orcid.org/0000-0003-2598-8150"
    with pytest.raises(ValueError):
        person.orcid = "0000-0003-2598-815X"


def test_person_papers(anthology):
    person = anthology.get_person("unverified/nicoletta-calzolari")
    assert person.canonical_name == Name("Nicoletta", "Calzolari")
    assert len(person.item_ids) == 3
    assert len(list(person.papers())) == 2
    assert len(list(person.volumes())) == 1


def test_person_with_name_variants(anthology):
    # Name variants should be recorded as names of that person
    person = anthology.get_person("yang-liu-ict")
    assert person.has_name(Name("Yang", "Liu"))
    assert person.has_name(Name("洋", "刘"))


def test_person_is_explicit(anthology):
    person = anthology.get_person("yang-liu-ict")
    assert person.is_explicit
    person = anthology.get_person("unverified/nicoletta-calzolari")
    assert not person.is_explicit


def test_person_make_explicit(anthology):
    person = anthology.get_person("unverified/nicoletta-calzolari")
    assert not person.is_explicit
    person.make_explicit("nicoletta-calzolari")
    assert person.is_explicit
    assert person.id == "nicoletta-calzolari"


def test_person_equality(anthology_stub):
    n = Name("Yang", "Liu")
    person1 = Person("yang-liu", anthology_stub, [n])
    person2 = Person("yang-liu", anthology_stub, [n])
    person3 = Person("yang-liu-mit", anthology_stub, [n])
    assert person1 == person2
    assert person1 != person3
    assert person2 != person3
    assert person2 != "yang-liu"  # comparison with non-Person object is always False
    assert hash(person1) == hash(person2)
