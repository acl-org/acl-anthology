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
    n1 = Name("Wen", "Zhao")
    n2 = Name("W.", "Zhao")
    n3 = Name("Wen X.", "Zhao")
    person = Person("wen-zhao", anthology_stub.people, [n1, n2])
    assert len(person.names) == 2
    assert person.has_name(n1)
    assert person.has_name(n2)
    assert not person.has_name(n3)


@pytest.mark.parametrize("n2", (Name("W.", "Zhao"), "Zhao, W."))
def test_person_set_canonical_name1(anthology_stub, n2):
    n1 = Name("Wen", "Zhao")
    person = Person("wen-zhao", anthology_stub.people)
    person.names = [n1, n2]
    assert person.canonical_name == n1
    person.canonical_name = n2
    assert person.canonical_name == Name("W.", "Zhao")
    assert len(person.names) == 2


def test_person_set_canonical_name2(anthology_stub):
    person = Person("rene-muller", anthology_stub.people, [Name("Rene", "Muller")])
    assert len(person.names) == 1
    name = Name("René", "Müller")
    person.canonical_name = name
    assert len(person.names) == 2
    assert person.canonical_name == name


@pytest.mark.parametrize("n3", (Name("Wen X.", "Zhao"), "Zhao, Wen X."))
def test_person_add_name(anthology_stub, n3):
    n1 = Name("Wen", "Zhao")
    n2 = Name("W.", "Zhao")
    person = Person("wen-zhao", anthology_stub.people, [n1])
    assert person.canonical_name == n1
    person.canonical_name = n2
    assert person.canonical_name == n2
    assert len(person.names) == 2
    person.add_name(n3)
    assert person.canonical_name == n2
    assert len(person.names) == 3
    assert person.has_name(Name("Wen X.", "Zhao"))


@pytest.mark.parametrize("n2", (Name("W.", "Zhao"), "Zhao, W."))
def test_person_remove_name(anthology_stub, n2):
    n1 = Name("Wen", "Zhao")
    person = Person("wen-zhao", anthology_stub.people)
    person.names = [n1, n2]
    assert person.has_name(n2)
    person.remove_name(n2)
    assert not person.has_name(n2)
    assert len(person.names) == 1


def test_person_names_explicit_vs_inferred(anthology_stub):
    n1 = Name("Wen", "Zhao")
    n2 = Name("W.", "Zhao")
    person = Person("wen-zhao", anthology_stub.people, [n1])
    assert (n1, NameLink.EXPLICIT) in person._names
    person.canonical_name = n2
    assert (n2, NameLink.EXPLICIT) in person._names
    n3 = Name("Wen X.", "Zhao")
    person.add_name(n3, inferred=True)
    assert (n3, NameLink.INFERRED) in person._names


def test_person_add_name_explicit_vs_inferred(anthology_stub):
    n1 = Name("Wen", "Zhao")
    n2 = Name("W.", "Zhao")
    n3 = Name("Wen X.", "Zhao")
    person = Person("wen-zhao", anthology_stub.people, [n1])
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
    person = Person("wen-zhao", anthology_stub.people, [])
    assert len(person.names) == 0
    with pytest.raises(ValueError):
        person.canonical_name
    name = Name("Wen", "Zhao")
    person.canonical_name = name
    assert len(person.names) == 1
    assert person.canonical_name == name


def test_person_orcid(anthology_stub):
    person = Person(
        "alex-fenwick",
        anthology_stub.people,
        [Name("Alex", "Fenwick")],
        orcid="0000-0002-1297-6794",
    )
    assert person.orcid == "0000-0002-1297-6794"
    person.orcid = "0009-0001-4567-8902"
    assert person.orcid == "0009-0001-4567-8902"
    # should automatically convert into correct format
    person.orcid = "https://orcid.org/0000-0002-1297-6794"
    assert person.orcid == "0000-0002-1297-6794"
    with pytest.raises(ValueError):
        person.orcid = "foo-bar"
    with pytest.raises(ValueError):
        # does not pass checksum
        person.orcid = "0009-0001-4567-890X"
    person.orcid = None
    assert person.orcid is None


def test_person_papers_unverified(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="petra-lindholm"))
    assert person.canonical_name == Name("Petra", "Lindholm")
    assert len(person.item_ids) == 3
    assert len(list(person.anthology_items())) == 3
    assert len(list(person.papers())) == 2
    assert len(list(person.volumes())) == 1


def test_person_papers_verified(anthology):
    person = anthology.get_person("wen-zhao-instx")
    assert person.canonical_name == Name("Wen", "Zhao")
    assert len(person.item_ids) == 2
    assert len(list(person.papers())) == 2


def test_person_namespecs(anthology):
    for person in anthology.people.values():
        assert len(list(person.namespecs())) == len(person.item_ids)
        for namespec in person.namespecs():
            assert namespec.resolve() is person


def test_person_change_id(anthology):
    person = anthology.get_person("alex-fenwick")
    person.change_id("alex-fenwick-fakerhausen")
    assert anthology.get_person("alex-fenwick") is None
    assert anthology.get_person("alex-fenwick-fakerhausen") is person
    person.change_id("alex-fenwick")
    assert anthology.get_person("alex-fenwick") is person
    assert anthology.get_person("alex-fenwick-fakerhausen") is None


def test_person_change_id_should_update_connected_papers(anthology):
    person = anthology.get_person("wen-zhao-instx")
    person.change_id("wen-zhao-new")
    namespec = anthology.get("2022.facl-long.424").authors[-1]
    assert namespec.name == Name("Wen", "Zhao")
    assert namespec.id == "wen-zhao-new"
    assert anthology.collections["2022.facl"].is_modified


def test_person_cannot_change_id_when_inferred(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="petra-lindholm"))
    assert not person.is_explicit
    with pytest.raises(AnthologyException):
        person.change_id("petra-lindholm")


def test_person_cannot_change_id_with_invalid_id(anthology):
    person = anthology.get_person("alex-fenwick")
    with pytest.raises(AnthologyInvalidIDError):
        person.change_id("Alex-Fenwick")
    with pytest.raises(AnthologyInvalidIDError):
        person.change_id("42-alex-fenwick")
    with pytest.raises(AnthologyInvalidIDError):
        person.change_id("alex fenwick")


def test_person_cannot_change_id_to_existing_id(anthology):
    person = anthology.get_person("alex-fenwick")
    with pytest.raises(AnthologyInvalidIDError):
        person.change_id("wen-zhao-instx")


def test_person_with_name_variants(anthology):
    # Name variants should be recorded as names of that person
    person = anthology.get_person("wen-zhao-labx")
    assert person.has_name(Name("Wen", "Zhao"))
    assert person.has_name(Name("赵", "文"))


def test_person_is_explicit(anthology):
    person = anthology.get_person("wen-zhao-instx")
    assert person.is_explicit
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="petra-lindholm"))
    assert not person.is_explicit


def test_person_make_explicit(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="petra-lindholm"))
    assert not person.is_explicit
    person.make_explicit("petra-lindholm-abc")
    assert person.is_explicit
    assert person.id == "petra-lindholm-abc"
    # IDs have been added to these collections:
    assert anthology.collections["Q89"].is_modified
    assert anthology.collections["K06"].is_modified
    # But not this one:
    assert not anthology.collections["2022.facl"].is_modified


def test_person_make_explicit_with_default_id(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="petra-lindholm"))
    assert not person.is_explicit
    person.make_explicit()  # default ID
    assert person.is_explicit
    assert person.id == "petra-lindholm"
    # IDs have been added to these collections:
    assert anthology.collections["Q89"].is_modified
    assert anthology.collections["K06"].is_modified
    # But not this one:
    assert not anthology.collections["2022.facl"].is_modified


def test_person_make_explicit_skip_setting_ids(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="petra-lindholm"))
    assert not person.is_explicit
    person.make_explicit(new_id="petra-lindholm", skip_setting_ids=True)
    assert person.is_explicit
    assert person.id == "petra-lindholm"
    # IDs have NOT been added to these collections:
    assert not anthology.collections["Q89"].is_modified
    assert not anthology.collections["K06"].is_modified
    assert not anthology.collections["2022.facl"].is_modified
    # Person still has three papers resolving to them
    assert len(person.item_ids) == 3
    assert len(list(person.namespecs())) == 3


def test_person_make_explicit_skip_setting_ids_updates_item_ids(anthology):
    unverified_id = UNVERIFIED_PID_FORMAT.format(pid="wen-zhao")
    person = anthology.get_person(unverified_id)
    # Prerequisites: Person is implicit and has exactly one paper resolving to them
    assert not person.is_explicit
    assert len(person.item_ids) == 1
    assert len(list(person.namespecs())) == 1
    person.make_explicit(new_id="wen-zhao-suffix", skip_setting_ids=True)
    assert person.is_explicit
    assert person.id == "wen-zhao-suffix"
    # Person no longer has any papers resolving to them
    assert len(person.item_ids) == 0
    assert len(list(person.namespecs())) == 0
    # Unverified person still exists, but is a different person
    person2 = anthology.get_person(unverified_id)
    assert person2 is not None
    assert person2 != person
    # ...and still has the one paper resolving to them
    assert len(person2.item_ids) == 1
    assert len(list(person2.namespecs())) == 1


def test_person_make_explicit_should_raise_when_explicit(anthology):
    person = anthology.get_person("alex-fenwick")
    assert person.is_explicit
    with pytest.raises(AnthologyException):
        person.make_explicit("alex-fenwick-new")


def test_person_make_explicit_should_raise_on_id_errors(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="petra-lindholm"))
    assert not person.is_explicit
    with pytest.raises(AnthologyException, match="Not a valid verified-person ID"):
        person.make_explicit("Petra-Lindholm")
    with pytest.raises(AnthologyException, match="Not a valid verified-person ID"):
        person.make_explicit("petra-lindholm-still/unverified")
    with pytest.raises(AnthologyException, match="ID already exists"):
        person.make_explicit("alex-fenwick")


def test_person_set_id_on_items(anthology):
    person = anthology.get_person("derek-holloway")
    # Verify precondition: Not all papers associated with this person have an ID set
    namespecs = list(person.namespecs())
    assert any(namespec.id is None for namespec in namespecs)
    # Set IDs, excluding one item by ID
    person.set_id_on_items(exclude=["2022.natfake-1.9"])
    paper = anthology.get_paper("2022.natfake-1.9")
    assert any(namespec.id is None for namespec in namespecs)
    assert paper.authors[0].id is None
    person.set_id_on_items(exclude=[paper])
    assert any(namespec.id is None for namespec in namespecs)
    assert paper.authors[0].id is None
    # Set ID, not excluding the paper
    person.set_id_on_items()
    assert all(namespec.id == "derek-holloway" for namespec in namespecs)
    assert paper.authors[0].id == "derek-holloway"


def test_person_set_id_on_items_should_add_name_variants(anthology):
    person = anthology.get_person("mei-ling-tan")
    # Verify precondition: This person has an inferred name variant
    assert person.canonical_name == Name("Mei Ling", "Tan")
    assert (Name("Mei", "Ling Tan"), NameLink.INFERRED) in person._names
    assert (Name("Mei", "Ling Tan"), NameLink.EXPLICIT) not in person._names
    # Set IDs
    person.set_id_on_items()
    namespecs = list(person.namespecs())
    assert all(namespec.id == "mei-ling-tan" for namespec in namespecs)
    # Name should be added as explicit now
    assert (Name("Mei", "Ling Tan"), NameLink.EXPLICIT) in person._names


def test_person_set_id_on_items_should_raise(anthology):
    person = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="petra-lindholm"))
    with pytest.raises(AnthologyException):
        person.set_id_on_items()


def test_person_merge_into_unverified_verified(anthology):
    # Pre-conditions
    person1 = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="wen-zhao"))
    assert not person1.is_explicit
    assert person1.item_ids == {("2022.natfake", "1", "6")}
    person2 = anthology.get_person("wen-zhao-megasoft")
    assert person2.is_explicit
    assert person2.item_ids == {("2022.facl", "long", "226")}

    # Test merging
    person1.merge_into(person2)
    assert not person1.item_ids
    assert person2.item_ids == {("2022.facl", "long", "226"), ("2022.natfake", "1", "6")}
    namespec = anthology.get_paper(("2022.natfake", "1", "6")).authors[0]
    assert namespec.id == "wen-zhao-megasoft"

    anthology.reset_indices()


@pytest.mark.parametrize(
    "pid1, pid2",
    (
        ("a-fenwick", "alex-fenwick"),
        ("alex-fenwick", "a-fenwick"),
    ),
)
def test_person_merge_into_verified_verified(anthology, pid1, pid2):
    person1 = anthology.get_person(pid1)
    person2 = anthology.get_person(pid2)
    expected_canonical_name = person2.canonical_name

    person1.merge_into(person2)

    # Item assignment should have changed
    assert not person1.item_ids
    assert set(person2.item_ids) == {
        ("2022.natfake", "1", "7"),
        ("2022.natfake", "1", "8"),
    }
    namespec = anthology.get_paper(("2022.natfake", "1", "8")).authors[0]
    assert namespec.id == pid2

    # New person should have the old person's attributes
    assert person2.has_name(Name("A.", "Fenwick"))
    assert person2.has_name(Name("Alex", "Fenwick"))
    assert person2.canonical_name == expected_canonical_name
    assert person2.degree == "Fakerhausen University"
    assert person2.orcid == "0009-0001-4567-8902"

    # Old person should no longer exist in index
    assert anthology.people.get_by_orcid("0009-0001-4567-8902") is person2
    assert set(anthology.people.get_by_name(Name("Alex", "Fenwick"))) == set([person2])
    assert pid2 in anthology.people
    assert pid1 not in anthology.people

    anthology.reset_indices()


def test_person_merge_into_unverified_should_raise(anthology):
    person1 = anthology.get_person(UNVERIFIED_PID_FORMAT.format(pid="wen-zhao"))
    person2 = anthology.get_person("wen-zhao-megasoft")
    with pytest.raises(AnthologyException):
        person2.merge_into(person1)

    anthology.reset_indices()


def test_person_equality(anthology_stub):
    n = Name("Wen", "Zhao")
    person1 = Person("wen-zhao", anthology_stub.people, [n])
    person2 = Person("wen-zhao", anthology_stub.people, [n])
    person3 = Person("wen-zhao-other", anthology_stub.people, [n])
    assert person1 == person2
    assert person1 != person3
    assert person2 != person3
    assert person2 != "wen-zhao"  # comparison with non-Person object is always False
    assert hash(person1) == hash(person2)
