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
