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

from acl_anthology.people import Name, Person


def test_person_names(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    n3 = Name("Yang X.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1, n2])
    assert len(person.names) == 2
    assert person.has_name(n1)
    assert person.has_name(n2)
    assert not person.has_name(n3)


def test_person_canonical_names(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1, n2])
    assert person.canonical_name == n1
    person.set_canonical_name(n2)
    assert person.canonical_name == n2
    assert len(person.names) == 2


def test_person_add_names(anthology_stub):
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


def test_person_papers(anthology):
    person = anthology.get_person("nicoletta-calzolari")
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
    person = anthology.get_person("nicoletta-calzolari")
    assert not person.is_explicit
    person = anthology.get_person("srinivas-bangalore")
    assert person.is_explicit


def test_person_equality(anthology_stub):
    n = Name("Yang", "Liu")
    person1 = Person("yang-liu", anthology_stub, [n])
    person2 = Person("yang-liu", anthology_stub, [n])
    person3 = Person("yang-liu-mit", anthology_stub, [n])
    assert person1 == person2
    assert person1 != person3
    assert person2 != person3
    assert hash(person1) == hash(person2)
