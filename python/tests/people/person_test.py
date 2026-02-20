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
from acl_anthology.exceptions import AnthologyException, AnthologyInvalidIDError
from acl_anthology.people import Name, NameLink, Person, UNVERIFIED_PID_FORMAT


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
    person.canonical_name = n2
    assert person.canonical_name == n2
    assert len(person.names) == 2


def test_person_add_name(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1])
    assert person.canonical_name == n1
    person.canonical_name = n2
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
    person.canonical_name = n2
    assert (n2, NameLink.EXPLICIT) in person._names
    n3 = Name("Yang X.", "Liu")
    person.add_name(n3, inferred=True)
    assert (n3, NameLink.INFERRED) in person._names


def test_person_add_name_explicit_vs_inferred(anthology_stub):
    n1 = Name("Yang", "Liu")
    n2 = Name("Y.", "Liu")
    n3 = Name("Yang X.", "Liu")
    person = Person("yang-liu", anthology_stub, [n1])
    person.add_name(n2, inferred=True)
    person.add_name(n3, inferred=False)
    assert person._names[1] == (n2, NameLink.INFERRED)
    assert person._names[2] == (n3, NameLink.EXPLICIT)
    # Calling add_name() with an existing name, but different "inferred" flag,
    # should overwrite the NameLink value but keep the name in the same position
    person.add_name(n2, inferred=False)
    assert person._names[1] == (n2, NameLink.EXPLICIT)
    person.add_name(n3, inferred=True)
    assert person._names[2] == (n3, NameLink.INFERRED)


def test_person_no_name(anthology_stub):
    person = Person("yang-liu", anthology_stub, [])
    assert len(person.names) == 0
    with pytest.raises(ValueError):
        person.canonical_name
    name = Name("Yang", "Liu")
    person.canonical_name = name
    assert len(person.names) == 1
    assert person.canonical_name == name


def test_person_set_canonical_name(anthology_stub):
    person = Person("rene-muller", anthology_stub, [Name("Rene", "Muller")])
    assert len(person.names) == 1
    name = Name("René", "Müller")
    person.canonical_name = name
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


def test_person_papers_unverified(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="nicoletta-calzolari"))
    assert person.canonical_name == Name("Nicoletta", "Calzolari")
    assert len(person.item_ids) == 3
    assert len(list(person.anthology_items())) == 3
    assert len(list(person.papers())) == 2
    assert len(list(person.volumes())) == 1


def test_person_papers_verified(anthology):
    person = anthology.get_person("yang-liu-ict")
    assert person.canonical_name == Name("Yang", "Liu")
    assert len(person.item_ids) == 2
    assert len(list(person.papers())) == 2


def test_person_namespecs(anthology):
    for person in anthology.people.values():
        assert len(list(person.namespecs())) == len(person.item_ids)
        for namespec in person.namespecs():
            assert namespec.resolve() is person


def test_person_change_id(anthology):
    person = anthology.get_person("marcel-bollmann")
    person.change_id("marcel-bollmann-rub")
    assert anthology.get_person("marcel-bollmann") is None
    assert anthology.get_person("marcel-bollmann-rub") is person
    person.change_id("marcel-bollmann")
    assert anthology.get_person("marcel-bollmann") is person
    assert anthology.get_person("marcel-bollmann-rub") is None


def test_person_change_id_should_update_connected_papers(anthology):
    person = anthology.get_person("yang-liu-ict")
    person.change_id("yang-liu-new")
    namespec = anthology.get(person.item_ids[0]).authors[-1]
    assert namespec.name == Name("Yang", "Liu")
    assert namespec.id == "yang-liu-new"
    assert anthology.collections["2022.acl"].is_modified


def test_person_cannot_change_id_when_inferred(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="nicoletta-calzolari"))
    assert not person.is_explicit
    with pytest.raises(AnthologyException):
        person.change_id("nicoletta-calzolari")


def test_person_cannot_change_id_with_invalid_id(anthology):
    person = anthology.get_person("marcel-bollmann")
    with pytest.raises(AnthologyInvalidIDError):
        person.change_id("Marcel-Bollmann")
    with pytest.raises(AnthologyInvalidIDError):
        person.change_id("42-marcel-bollmann")
    with pytest.raises(AnthologyInvalidIDError):
        person.change_id("marcel bollmann")


def test_person_cannot_change_id_to_existing_id(anthology):
    person = anthology.get_person("marcel-bollmann")
    with pytest.raises(AnthologyInvalidIDError):
        person.change_id("yang-liu-ict")


def test_person_with_name_variants(anthology):
    # Name variants should be recorded as names of that person
    person = anthology.get_person("yang-liu-ict")
    assert person.has_name(Name("Yang", "Liu"))
    assert person.has_name(Name("洋", "刘"))


def test_person_is_explicit(anthology):
    person = anthology.get_person("yang-liu-ict")
    assert person.is_explicit
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="nicoletta-calzolari"))
    assert not person.is_explicit


def test_person_make_explicit(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="nicoletta-calzolari"))
    assert not person.is_explicit
    person.make_explicit("nicoletta-calzolari")
    assert person.is_explicit
    assert person.id == "nicoletta-calzolari"
    # IDs have been added to these collections:
    assert anthology.collections["J89"].is_modified
    assert anthology.collections["L06"].is_modified
    # But not this one:
    assert not anthology.collections["2022.acl"].is_modified


def test_person_make_explicit_should_raise_when_explicit(anthology):
    person = anthology.get_person("marcel-bollmann")
    assert person.is_explicit
    with pytest.raises(AnthologyException):
        person.make_explicit("marcel-bollmann")


def test_person_merge_with_explicit(anthology):
    # Pre-conditions
    person1 = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="yang-liu"))
    assert not person1.is_explicit
    assert person1.item_ids == [("2022.naloma", "1", "6")]
    person2 = anthology.get_person("yang-liu-microsoft")
    assert person2.item_ids == [("2022.acl", "long", "226")]

    # Test merging
    person1.merge_with_explicit(person2)
    assert not person1.item_ids
    assert person2.item_ids == [("2022.acl", "long", "226"), ("2022.naloma", "1", "6")]
    namespec = anthology.get_paper(("2022.naloma", "1", "6")).authors[0]
    assert namespec.id == "yang-liu-microsoft"

    anthology.reset_indices()


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
