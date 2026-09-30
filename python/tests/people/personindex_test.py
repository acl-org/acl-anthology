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

import pytest
from acl_anthology.exceptions import (
    AnthologyException,
    AnthologyInvalidIDError,
    NameSpecResolutionError,
    NameSpecResolutionWarning,
    PersonDefinitionError,
)
from acl_anthology.people import (
    Name,
    NameLink,
    NameSpecification,
    Person,
    PersonIndex,
    UNVERIFIED_PID_FORMAT,
)


@pytest.fixture
def index_stub(anthology_stub):
    return PersonIndex(anthology_stub)


@pytest.fixture
def index(anthology):
    return anthology.people


def test_load_people_index(index_stub):
    index = index_stub
    index.reset()
    index._load_people_index()
    index.is_data_loaded = True
    for pid in (
        "maeve-oconnell",
        "derek-holloway",
        "wen-zhao-labx",
        "wen-zhao-instx",
        "wen-zhao-megasoft",
    ):
        assert pid in index


def test_load_people_index_registers_names(index_stub):
    index = index_stub
    index.reset()
    index._load_people_index()
    index.is_data_loaded = True
    n1 = Name("Derek", "Holloway")
    n2 = Name("D.", "Holloway")
    assert n1 in index.by_name
    assert n2 in index.by_name
    pid = index.by_name[n1]
    assert pid == index.by_name[n2]
    assert pid[0] in index


def test_add_person(index_stub):
    index = index_stub
    index.reset()
    p1 = Person("wen-zhao", index, [Name("Wen", "Zhao")])
    index.add_person(p1)
    index.is_data_loaded = True  # to prevent it attempting to build itself
    assert "wen-zhao" in index
    assert Name("Wen", "Zhao") in index.by_name
    assert index.by_name[Name("Wen", "Zhao")] == ["wen-zhao"]
    assert index.get_by_name(Name("Wen", "Zhao"))[0] is p1
    assert index.get_by_namespec(NameSpecification(Name("Wen", "Zhao"))) is p1
    assert index.get("wen-zhao") is p1
    with pytest.raises(ValueError):
        index.add_person(Person("wen-zhao", index))


def test_remove_person(index):
    # Preconditions
    pid = "lin-feng-tsingcity"
    name = Name("Lin", "Feng")
    person = index[pid]
    assert index._by_orcid.get("0009-0003-6567-8920") == pid
    assert pid in index._by_name[name]
    assert pid in index._slugs_to_verified_ids["lin-feng"]
    assert len(person.item_ids) == 0

    # Remove person
    index.remove_person(person)

    assert pid not in index
    assert index._by_orcid.get("0009-0003-6567-8920") is None
    assert pid not in index._by_name[name]
    assert pid not in index._slugs_to_verified_ids["lin-feng"]

    with pytest.raises(ValueError):
        # Can't remove again...
        index.remove_person(person)


def test_remove_person_should_raise(index):
    assert "wen-zhao/unverified" in index
    person1 = index["wen-zhao/unverified"]
    # Can't remove unverified
    with pytest.raises(ValueError):
        index.remove_person(person1)

    assert "wen-zhao-labx" in index
    person2 = index["wen-zhao-labx"]
    assert len(person2.item_ids) > 0
    # Can't remove if papers still attached to Person
    with pytest.raises(ValueError):
        index.remove_person(person2)


def test_similar_names_defined_in_people_index(index_stub):
    index = index_stub
    index.reset()
    index._load_people_index()
    index.is_data_loaded = True
    similar = index.similar.subset("ravi-b")
    assert similar == {"ravi-b", "ravi-bishnu"}


def test_similar_names_through_same_canonical_name(index):
    assert not index.is_data_loaded
    index.build(show_progress=False)
    assert index.is_data_loaded
    similar = index.similar.subset("wen-zhao-instx")
    assert similar == {
        "wen-zhao",
        "wen-zhao-labx",
        "wen-zhao-instx",
        "wen-zhao-megasoft",
        "wen-zhao/unverified",
    }


def test_build_personindex(index):
    assert not index.is_data_loaded
    index.build(show_progress=True)
    assert index.is_data_loaded
    assert "wen-zhao/unverified" in index
    assert "wen-zhao-megasoft" in index
    assert Name("Petra", "Lindholm") in index.by_name
    assert "0009-0001-4567-8902" in index.by_orcid


def test_build_personindex_automatically(index):
    assert not index.is_data_loaded
    persons = index.get_by_name(Name("Petra", "Lindholm"))
    assert index.is_data_loaded
    assert len(persons) == 1


@pytest.mark.parametrize(
    "name", ("by_orcid", "by_name", "similar", "slugs_to_verified_ids")
)
def test_build_personindex_automatically_on_property_access(index, name):
    assert not index.is_data_loaded
    _ = getattr(index, name)
    assert index.is_data_loaded


def test_canonical_name_never_has_script(index):
    for person in index.values():
        assert person.canonical_name.script is None


def test_get_person_coauthors(index):
    index.load()
    person = index.by_name[Name("Marguerite", "Solvang")][0]
    coauthors = index.find_coauthors(person)
    assert len(coauthors) == 1
    assert coauthors[0].canonical_name == Name("Owen", "Castellane")

    person = index.get_by_name(Name("Dario", "Pretto"))[0]
    coauthors = index.find_coauthors(person)
    assert len(coauthors) == 2
    # Both volumes where Dario Pretto is editor have frontmatter, so should still be counted
    coauthors = index.find_coauthors(person, include_volumes=False)
    assert len(coauthors) == 2


def test_get_person_coauthors_counter(index):
    coauthors = index.find_coauthors_counter(
        UNVERIFIED_PID_FORMAT.format(pid="marguerite-solvang")
    )
    assert len(coauthors) == 1
    assert coauthors[UNVERIFIED_PID_FORMAT.format(pid="owen-castellane")] == 1

    person = index.get_by_name(Name("Dario", "Pretto"))[0]
    coauthors = index.find_coauthors_counter(person)
    assert len(coauthors) == 2
    assert coauthors[UNVERIFIED_PID_FORMAT.format(pid="owen-castellane")] == 0
    assert coauthors[UNVERIFIED_PID_FORMAT.format(pid="selin-aksoy")] == 2


def test_get_by_namespec(index):
    ns1 = NameSpecification(Name("Li", "Feng"))  # does not exist
    ns2 = NameSpecification(Name("Wen", "Zhao"), id="wen-zhao-megasoft")
    with pytest.raises(NameSpecResolutionError):
        index.get_by_namespec(ns1)
    person = index.get_by_namespec(ns2)
    assert person.id == "wen-zhao-megasoft"
    assert person.canonical_name == Name("Wen", "Zhao")


def test_get_by_name_variants(index):
    # It should be possible to find a person by a name variant
    persons = index.get_by_name(Name("赵", "文"))
    assert len(persons) == 1
    assert persons[0].id == "wen-zhao-labx"


def test_get_by_orcid(index):
    person = index.get_by_orcid("0009-0001-4567-8902")
    assert person is not None
    assert person.id == "alex-fenwick"
    assert index.get_by_orcid("0000-0000-0000-0000") is None


def test_change_orcid(index):
    person = index.get_by_orcid("0009-0001-4567-8902")
    assert person is not None
    assert person.id == "alex-fenwick"
    person.orcid = "0000-0002-2909-0906"
    assert index.get_by_orcid("0009-0001-4567-8902") is None
    assert index.get_by_orcid("0000-0002-2909-0906") is person


test_cases_generate_person_id_from_name = (
    (Name("Matt", "Post"), None, None, "matt-post"),
    (
        Name("Matt", "Post"),
        "jhu",
        "0000-0002-1297-6794",
        "matt-post",
    ),  # suffix/orcid not needed
    (
        Name("Alex", "Fenwick"),
        None,
        None,
        AnthologyException,
    ),  # alex-fenwick already exists
    (Name("Alex", "Fenwick"), "fakerhausen", None, "alex-fenwick-fakerhausen"),
    (Name("Alex", "Fenwick"), "FAKERHAUSEN", None, "alex-fenwick-fakerhausen"),
    (Name("Alex", "Fenwick"), None, "0009-0001-4567-8902", "alex-fenwick-8902"),
    (
        Name("Alex", "Fenwick"),
        "fakerhausen",
        "0009-0001-4567-8902",
        "alex-fenwick-fakerhausen",
    ),
    (
        Name("Wen", "Zhao"),
        "labx",
        None,
        AnthologyException,
    ),  # wen-zhao-labx already exists
    (Name("Wen", "Zhao"), "labx", "0000-0000-0000-018X", UserWarning),
    (Name("Lin", "Feng"), "tsingcity", "0000-0000-0000-018X", "lin-feng-018x"),
)


@pytest.mark.parametrize(
    "name, suffix, orcid, expected_result", test_cases_generate_person_id_from_name
)
def test_generate_person_id_from_name(index, name, suffix, orcid, expected_result):
    if isinstance(expected_result, str):
        pid = index.generate_person_id(name, suffix=suffix, orcid=orcid)
        assert pid == expected_result
    elif isinstance(expected_result, type):
        with pytest.raises(expected_result):
            index.generate_person_id(name, suffix=suffix, orcid=orcid)
    else:
        raise ValueError(
            f"Test cannot take expected result of type {type(expected_result)}"
        )


def test_generate_person_id_from_person(index):
    person = index["alex-fenwick"]
    # Would add suffix to generate new ID for disambiguation
    assert (
        index.generate_person_id(person, suffix="fakerhausen")
        == "alex-fenwick-fakerhausen"
    )
    # Would add ORCID to generate new ID for disambiguation
    assert index.generate_person_id(person) == "alex-fenwick-8902"
    # Would add supplied ORCID to generate new ID for disambiguation
    assert (
        index.generate_person_id(person, orcid="0000-0002-2909-0906")
        == "alex-fenwick-0906"
    )


def test_generate_person_id_should_warn(index):
    index.reset()
    index._load_people_index()
    # This person exists (as verified), but without an ORCID, so generating an
    # ID with an ORCID suffix should emit a warning
    name = Name.from_dict({"first": "Derek", "last": "Holloway"})

    with pytest.warns(UserWarning):
        pid = index.generate_person_id(name, orcid="0000-0002-4236-2611")

    assert pid == "derek-holloway-2611"


def test_create_person(index):
    person = index.create(
        id="matt-post",
        names=[Name("Matt", "Post")],
        orcid="0000-0002-1297-6794",
    )
    assert person.id in index
    assert person.id == "matt-post"
    assert person.orcid == "0000-0002-1297-6794"
    assert person.is_explicit


def test_create_person_changes_namespec_resolution(index):
    implicit_person = index[UNVERIFIED_PID_FORMAT.format(pid="torvald-nyman")]
    namespecs = list(implicit_person.namespecs())
    assert len(namespecs) > 0
    explicit_person = index.create(
        id="torvald-nyman",
        names=[Name("Torvald", "Nyman")],
    )
    # Papers that resolved to implicit_person before should resolve to explicit_person now
    assert all(ns.resolve() is explicit_person for ns in namespecs)
    assert set(explicit_person.namespecs()) == set(namespecs)
    assert len(list(implicit_person.namespecs())) == 0


def test_create_person_creates_ambiguous_name(index):
    person1 = index["torsten-baumann"]
    # Precondition: This person has both explicitly and implicitly linked papers
    assert len(person1.item_ids) == 5
    assert sum(ns.id == "torsten-baumann" for ns in person1.namespecs()) == 2
    # Precondition: No unverified "torsten-baumann" exists
    assert UNVERIFIED_PID_FORMAT.format(pid="torsten-baumann") not in index

    person2 = index.create(
        id="torsten-baumann-two",
        names=[Name("Torsten", "Baumann")],
    )
    # No papers should resolve to person2
    assert len(person2.item_ids) == 0
    # Only explicitly linked papers should resolve to person1 now
    assert len(person1.item_ids) == 2
    assert all(ns.id == "torsten-baumann" for ns in person1.namespecs())
    # An unverified "torsten-baumann" should now exist with the remaining three papers
    person3 = index[UNVERIFIED_PID_FORMAT.format(pid="torsten-baumann")]
    assert person3 is not None
    assert len(person3.item_ids) == 3
    assert all(ns.id is None for ns in person3.namespecs())


def test_create_person_should_fail_on_duplicate_orcid(index):
    with pytest.raises(ValueError):
        index.create(
            id="alex-fenwick-twin",
            names=[Name("Alex", "Fenwick")],
            orcid="0009-0001-4567-8902",  # already assigned to "alex-fenwick"
        )


def test_create_person_should_fail_on_duplicate_id(index):
    with pytest.raises(AnthologyInvalidIDError):
        index.create(
            id="alex-fenwick",  # already exists
            names=[Name("Alex", "Fenwick")],
        )


def test_create_person_should_fail_on_unverified_id(index):
    with pytest.raises(AnthologyInvalidIDError):
        index.create(
            id=UNVERIFIED_PID_FORMAT.format(
                pid="john-doe"
            ),  # cannot create this manually
            names=[Name("John", "Doe")],
        )


def test_create_person_should_handle_duplicate_names(index):
    person = index.create(
        id="matt-post",
        names=[Name("Matt", "Post"), Name("Matt", "Post")],
        orcid="0000-0002-1297-6794",
    )
    assert person.id in index
    assert len(person.names) == 1


def test_create_person_should_fail_on_empty_names(index):
    with pytest.raises(ValueError):
        index.create(
            id="john-doe-new",
            names=[],  # cannot be empty
        )


def test_add_to_index_behavior_on_duplicate_namespecs(index):
    index.build()  # since we’re testing with and without IDs
    example_id = ("1999.cl", "1", "5")
    # Case 1 – should resolve to different persons
    index._add_to_index(
        [
            NameSpecification(Name("Wen", "Zhao"), id="wen-zhao-instx"),
            NameSpecification(Name("Wen", "Zhao")),
        ],
        example_id,
    )
    # Case 2 – should resolve to same unverified person -> warning
    with pytest.warns(NameSpecResolutionWarning):
        index._add_to_index(
            [
                NameSpecification(Name("Wen", "Zhao")),
                NameSpecification(Name("Wen", "Zhao")),
            ],
            example_id,
        )
    # Case 3 – should resolve to same verified person -> error
    with pytest.raises(NameSpecResolutionError):
        index._add_to_index(
            [
                NameSpecification(Name("Derek", "Holloway"), id="derek-holloway"),
                NameSpecification(Name("D.", "Holloway"), id="derek-holloway"),
            ],
            example_id,
        )


##############################################################################
### Tests for changing Person attributes that should update the index
##############################################################################


def test_person_id_change_should_fail_on_existing_items(anthology):
    index = anthology.people
    person = index["alex-fenwick"]
    # Cannot change this directly – there are items associated with the old ID!
    with pytest.raises(PersonDefinitionError):
        person.id = "alex-fenwick-fakerhausen"


def test_person_id_change_should_update_index(anthology):
    index = anthology.people
    person = index["alex-fenwick"]
    # Unlink all items first
    for ns in person.namespecs():
        ns.orcid = None
        ns.id = None
    # Now, the ID can be changed
    person.id = "alex-fenwick-fakerhausen"
    assert "alex-fenwick" not in index
    assert "alex-fenwick-fakerhausen" in index
    assert index.by_orcid["0009-0001-4567-8902"] == "alex-fenwick-fakerhausen"
    assert index.by_name[Name("Alex", "Fenwick")] == ["alex-fenwick-fakerhausen"]


def test_person_orcid_change_should_update_index(anthology):
    index = anthology.people
    person = index["wen-zhao-instx"]
    orcid = "0000-0003-4154-7507"
    assert orcid not in index.by_orcid
    person.orcid = orcid
    assert orcid in index.by_orcid
    assert index.by_orcid[orcid] == "wen-zhao-instx"


def test_person_add_name_should_update_index(anthology):
    index = anthology.people
    person = index["alex-fenwick"]
    name = Name("Marc Alex", "Fenwick")
    assert not index.by_name[name]
    person.add_name(name)
    assert index.by_name[name] == ["alex-fenwick"]
    assert index.slugs_to_verified_ids[name.slugify()] == set(["alex-fenwick"])


def test_person_remove_name_should_update_index(anthology):
    index = anthology.people
    person = index["derek-holloway"]
    name = Name("Derek", "Holloway")
    assert index.by_name[name] == ["derek-holloway"]
    person.remove_name(name)
    assert index.by_name[name] == [UNVERIFIED_PID_FORMAT.format(pid="derek-holloway")]
    assert not index.slugs_to_verified_ids[name.slugify()]


def test_person_setting_names_should_update_index(anthology):
    index = anthology.people
    person = index["derek-holloway"]
    names = [Name("D.", "Holloway"), Name("Derek J.", "Holloway")]
    person.names = names
    # previously existing name
    assert index.by_name[names[0]] == ["derek-holloway"]
    # added name
    assert index.by_name[names[1]] == ["derek-holloway"]
    # removed name, now resolves to unverified
    assert index.by_name[Name("Derek", "Holloway")] == [
        UNVERIFIED_PID_FORMAT.format(pid="derek-holloway")
    ]


##############################################################################
### Tests for name resolution logic
##############################################################################

# Format: (Name, NameSpecification attributes, expected ID or Exception)
test_cases_resolve_namespec = (
    #### "No match" cases
    (  # Name does not exist in people.json
        {"first": "Matthew", "last": "Stevens"},
        {},
        UNVERIFIED_PID_FORMAT.format(pid="matthew-stevens"),
    ),
    (  # Person with explicit ID does not exist in people.json
        {"first": "Matthew", "last": "Stevens"},
        {"id": "matthew-stevens"},
        PersonDefinitionError,
    ),
    #### "One match" cases
    (  # Name exists in people.json, unambiguous
        {"first": "Derek", "last": "Holloway"},
        {},
        "derek-holloway",
    ),
    (  # Name exists in people.json, unambiguous, but not as canonical name
        {"first": "Maeve T.", "last": "O’Connell"},
        {},
        "maeve-oconnell",
    ),
    (  # Person unambiguous, but has `disable_name_matching: true`
        {"first": "Ravi", "last": "Bishnu"},
        {},
        UNVERIFIED_PID_FORMAT.format(pid="ravi-bishnu"),
    ),
    (  # `disable_name_matching: true` doesn't affect NameSpecs with explicit ID
        {"first": "Ravi", "last": "Bishnu"},
        {"id": "ravi-bishnu"},
        "ravi-bishnu",
    ),
    (  # Name exists in people.json with an ORCID, unambiguous
        {"first": "Alex", "last": "Fenwick"},
        {},
        "alex-fenwick",
    ),
    (  # ... with explicit ID
        {"first": "Alex", "last": "Fenwick"},
        {"id": "alex-fenwick"},
        "alex-fenwick",
    ),
    (  # ... with explicit ID & ORCID
        {"first": "Alex", "last": "Fenwick"},
        {"id": "alex-fenwick", "orcid": "0009-0001-4567-8902"},
        "alex-fenwick",
    ),
    (  # ... with explicit ID & ORCID, but ORCID doesn't match
        {"first": "Alex", "last": "Fenwick"},
        {"id": "alex-fenwick", "orcid": "0000-0002-7491-7669"},
        PersonDefinitionError,
    ),
    (  # ... with explicit ID & ORCID, but name isn't listed in people.json
        {"first": "Marc Alex", "last": "Fenwick"},
        {"id": "alex-fenwick", "orcid": "0009-0001-4567-8902"},
        PersonDefinitionError,
    ),
    (  # Name matches an existing, unambiguous name via slugification
        {"first": "Dérek", "last": "Hólloway"},
        {},
        "derek-holloway",
    ),
    (  # ... even when it's not the canonical name
        {"first": "Maeve T.", "last": "Ó’Connell"},
        {},
        "maeve-oconnell",
    ),
    (  # ... even with different first/last split
        {"first": "Maeve", "last": "T. O’Connell"},
        {},
        "maeve-oconnell",
    ),
    #### "2+ matches" cases
    (  # Name exists in people.json for several people
        {"first": "Wen", "last": "Zhao"},
        {},
        UNVERIFIED_PID_FORMAT.format(pid="wen-zhao"),
    ),
    (  # ... will resolve to known person with explicit ID
        {"first": "Wen", "last": "Zhao"},
        {"id": "wen-zhao-labx"},
        "wen-zhao-labx",
    ),
    (  # ... affiliation is NOT used in any way for name resolution
        {"first": "Wen", "last": "Zhao"},
        {"affiliation": "Microsoft Cognitive Services Research"},
        UNVERIFIED_PID_FORMAT.format(pid="wen-zhao"),
    ),
    #### Malformed name specifications
    (  # Person with explicit ORCID, but no explicit ID (always disallowed)
        {"first": "Matthew", "last": "Stevens"},
        {"orcid": "0000-0002-7491-7669"},
        NameSpecResolutionError,
    ),
    (  # ... even if the person exists (ID is still required)
        {"first": "Alex", "last": "Fenwick"},
        {"orcid": "0009-0001-4567-8902"},
        NameSpecResolutionError,
    ),
)


@pytest.mark.parametrize(
    "name_dict, namespec_params, expected_result",
    test_cases_resolve_namespec,
)
def test_resolve_namespec(name_dict, namespec_params, expected_result, index):
    index.reset()
    index._load_people_index()
    name = Name.from_dict(name_dict)
    namespec = NameSpecification(name, **namespec_params)

    if isinstance(expected_result, str):
        person = index._resolve_namespec(namespec, allow_creation=True)
        assert person.has_name(name)
        assert person.id == expected_result
    elif isinstance(expected_result, type):
        with pytest.raises(expected_result):
            index._resolve_namespec(namespec, allow_creation=True)
    else:
        raise ValueError(
            f"Test cannot take expected result of type {type(expected_result)}"
        )


def test_resolve_namespec_disallow_creation(index):
    index.reset()
    index._load_people_index()
    # If we would map to an unverified ID but allow_creation is False, should raise
    with pytest.raises(NameSpecResolutionError):
        index._resolve_namespec(
            NameSpecification(Name("Matthew", "Stevens")), allow_creation=False
        )


def test_resolve_namespec_name_scoring_for_unverified_ids(index_stub):
    # Person does not exist, will create an unverified ID
    person1 = index_stub._resolve_namespec(
        NameSpecification(Name("Rene", "Muller")), allow_creation=True
    )
    assert person1.id == UNVERIFIED_PID_FORMAT.format(pid="rene-muller")
    assert person1.canonical_name == Name("Rene", "Muller")
    # Name resolves to the same person as above
    person2 = index_stub._resolve_namespec(
        NameSpecification(Name("René", "Müller")), allow_creation=True
    )
    assert person2.id == UNVERIFIED_PID_FORMAT.format(pid="rene-muller")
    assert person2 is person1
    # ... and also updates their canonical name, as it scores higher!
    assert person2.canonical_name == Name("René", "Müller")


test_cases_namelink = (
    # Names that are explicitly defined in people.json should always have
    # NameLink.EXPLICIT after resolve_namespec()
    (
        {"first": "Derek", "last": "Holloway"},
        NameLink.EXPLICIT,
    ),
    (
        {"first": "D.", "last": "Holloway"},
        NameLink.EXPLICIT,
    ),
    (
        {"first": "Alex", "last": "Fenwick"},
        NameLink.EXPLICIT,
    ),
    # Names that are matched via slugification should always have
    # NameLink.INFERRED after resolve_namespec()
    (
        {"first": "Dérek", "last": "Hólloway"},
        NameLink.INFERRED,
    ),
    (
        {"first": "Maeve T.", "last": "Ó’Connell"},
        NameLink.INFERRED,
    ),
    (
        {"first": "Maeve", "last": "T. O’Connell"},
        NameLink.INFERRED,
    ),
)


@pytest.mark.parametrize("name_dict, expected_namelink", test_cases_namelink)
def test_check_namelink_after_resolve_namespec(name_dict, expected_namelink, index):
    index.reset()
    index._load_people_index()
    name = Name.from_dict(name_dict)
    namespec = NameSpecification(name)
    person = index._resolve_namespec(namespec, allow_creation=True)

    assert (
        name,
        expected_namelink,
    ) in person._names  # maybe provide a function for this?


def test_person_add_name_affects_name_resolution(anthology):
    index = anthology.people
    # Precondition: 3 papers resolve to this explicit person
    person1 = index["wen-zhao-labx"]
    assert len(person1.item_ids) == 3
    # Precondition: 1 paper resolves to this unverified person
    person2 = index[UNVERIFIED_PID_FORMAT.format(pid="alexander-zhao")]
    assert len(person2.item_ids) == 1
    all_papers = person1.item_ids | person2.item_ids

    # Adding a name should move unverified papers to this person via name matching
    name = Name("Alexander", "Zhao")
    person1.add_name(name)
    assert "wen-zhao-labx" in index.by_name[name]
    assert set(person1.item_ids) == all_papers
    assert len(person2.item_ids) == 0


def test_person_remove_name_affects_name_resolution(anthology):
    index = anthology.people
    person = index["derek-holloway"]
    # Precondition: 2 papers resolve to this person
    assert len(person.item_ids) == 2

    # Remove a name should move implicitly-linked papers to unverified person
    name = Name("Derek", "Holloway")
    person.remove_name(name)
    assert UNVERIFIED_PID_FORMAT.format(pid="derek-holloway") in index
    assert index.by_name[name] == [UNVERIFIED_PID_FORMAT.format(pid="derek-holloway")]
    assert len(person.item_ids) == 1


def test_person_disable_name_matching_affects_name_resolution(anthology):
    index = anthology.people
    person = index["derek-holloway"]
    # Precondition: 2 papers resolve to this person
    assert len(person.item_ids) == 2

    # Setting disable_name_matching should move implicitly-linked papers to
    # unverified person
    person.disable_name_matching = True
    assert UNVERIFIED_PID_FORMAT.format(pid="derek-holloway") in index
    assert len(person.item_ids) == 1

    # Setting it back should change it back
    person.disable_name_matching = False
    assert len(person.item_ids) == 2


def test_namespec_change_name_affects_name_resolution(anthology):
    index = anthology.people
    # Precondition: Find a paper that resolves to a given unverified person
    item_id = ("2022.facl", "long", "187")
    namespec = anthology.get_paper(item_id).authors[2]
    person1 = index.get(UNVERIFIED_PID_FORMAT.format(pid="soren-kessling"))
    assert namespec.resolve() is person1
    assert item_id in person1.item_ids

    # Changing the name should move the paper to another person
    namespec.name = Name("Soren Middlename", "Kessling")
    person2 = namespec.resolve()
    assert person2 is not person1
    assert person2.id == UNVERIFIED_PID_FORMAT.format(pid="soren-middlename-kessling")
    assert item_id not in person1.item_ids
    assert item_id in person2.item_ids


def test_namespec_change_name_affects_volume_and_frontmatter(anthology):
    index = anthology.people
    # Precondition: Find a volume that resolves to a given (unverified) person
    item_id = ("2022.facl", "long", None)
    frontmatter_id = ("2022.facl", "long", "0")
    namespec = anthology.get_volume(item_id).editors[-1]
    person1 = index.get(UNVERIFIED_PID_FORMAT.format(pid="nadia-ferris"))
    assert namespec.resolve() is person1
    assert item_id in person1.item_ids
    assert frontmatter_id in person1.item_ids

    # Changing the name should move the volume AND its frontmatter
    namespec.name = Name("Nadia Middlename", "Ferris")
    person2 = namespec.resolve()
    assert person2 is not person1
    assert person2.id == UNVERIFIED_PID_FORMAT.format(pid="nadia-middlename-ferris")
    assert item_id not in person1.item_ids
    assert frontmatter_id not in person1.item_ids
    assert item_id in person2.item_ids
    assert frontmatter_id in person2.item_ids


def test_namespec_change_id_affects_name_resolution(anthology):
    index = anthology.people
    # Precondition: Find a paper that resolves to a given verified person
    item_id = ("2022.facl", "long", "88")
    namespec = anthology.get_paper(item_id).authors[-2]
    person1 = index.get("wen-zhao-labx")
    person2 = index.get("wen-zhao-megasoft")
    assert namespec.resolve() is person1
    assert item_id in person1.item_ids
    assert item_id not in person2.item_ids

    # Changing the ID should move the paper to another person
    namespec.id = "wen-zhao-megasoft"
    assert namespec.resolve() is person2
    assert item_id not in person1.item_ids
    assert item_id in person2.item_ids


def test_namespec_change_id_affects_volume_and_frontmatter(anthology):
    index = anthology.people
    # Precondition: Find a volume that resolves to a given (unverified) person
    item_id = ("2022.facl", "long", None)
    frontmatter_id = ("2022.facl", "long", "0")
    namespec = anthology.get_volume(item_id).editors[-1]
    person1 = index.get(UNVERIFIED_PID_FORMAT.format(pid="nadia-ferris"))
    assert namespec.resolve() is person1
    assert item_id in person1.item_ids
    assert frontmatter_id in person1.item_ids

    # Changing the name should move the volume AND its frontmatter
    namespec.id = "nadia-ferris-test"
    person2 = namespec.resolve()
    assert person2 is not person1
    assert person2.id == "nadia-ferris-test"
    assert item_id not in person1.item_ids
    assert frontmatter_id not in person1.item_ids
    assert item_id in person2.item_ids
    assert frontmatter_id in person2.item_ids


def test_namespec_remove_id_affects_name_resolution(anthology):
    index = anthology.people
    # Precondition: Find a paper that resolves to a given verified person
    item_id = ("2022.facl", "long", "88")
    namespec = anthology.get_paper(item_id).authors[-2]
    person1 = index.get("wen-zhao-labx")
    person2 = index.get(UNVERIFIED_PID_FORMAT.format(pid="wen-zhao"))
    assert namespec.resolve() is person1
    assert item_id in person1.item_ids
    assert item_id not in person2.item_ids

    # Changing the ID should move the paper to another person
    namespec.id = None
    assert namespec.resolve() is person2
    assert item_id not in person1.item_ids
    assert item_id in person2.item_ids


def test_namespec_add_id_affects_name_resolution(anthology):
    index = anthology.people
    # Precondition: Find a paper that resolves to a given verified person
    item_id = ("2022.natfake", "1", "6")
    namespec = anthology.get_paper(item_id).authors[0]
    person1 = index.get(UNVERIFIED_PID_FORMAT.format(pid="wen-zhao"))
    person2 = index.get("wen-zhao-labx")
    assert namespec.resolve() is person1
    assert item_id in person1.item_ids
    assert item_id not in person2.item_ids

    # Changing the ID should move the paper to another person
    namespec.id = "wen-zhao-labx"
    assert namespec.resolve() is person2
    assert item_id not in person1.item_ids
    assert item_id in person2.item_ids


def test_namespec_normalize_affects_person_names_unverified(anthology):
    index = anthology.people
    # Precondition: Find a paper that resolves to a person with all-lowercase name
    item_id = ("2022.natfake", "1", "4")
    namespec = anthology.get_paper(item_id).authors[-1]
    person = index.get(UNVERIFIED_PID_FORMAT.format(pid="petros-angelidis"))
    assert namespec.resolve() is person
    assert namespec.name == Name("petros", "angelidis")
    assert person.names == [Name("petros", "angelidis")]

    # Normalizing should update the person's name
    namespec.normalize()
    assert namespec.name == Name("Petros", "Angelidis")
    assert (
        Name("Petros", "Angelidis") in person.names
    )  # for an unverified person, it's fine that the old name is still in here


##############################################################################
### Tests for ingestion logic
##############################################################################

# Format: (Name, NameSpecification attributes, expected ID)
test_cases_ingest_namespec = (
    (  # No ORCID in the ingestion material
        {"first": "Matthew", "last": "Stevens"},
        {},
        None,
    ),
    #### ORCID in the ingestion material, matches a person in our `people.json`
    (
        {"first": "Alex", "last": "Fenwick"},
        {"orcid": "0009-0001-4567-8902"},
        "alex-fenwick",
    ),
    (  # ... even if the name wasn't recorded yet in `people.json`
        {"first": "Marc Alex", "last": "Fenwick"},
        {"orcid": "0009-0001-4567-8902"},
        "alex-fenwick",
    ),
    (  # ... and even if the ORCID is given in URL style
        {"first": "Alex", "last": "Fénwick"},
        {"orcid": "https://orcid.org/0009-0001-4567-8902"},
        "alex-fenwick",
    ),
    #### ORCID in the ingestion material, no match in our `people.json`
    (  # Person should be created
        {"first": "Matt", "last": "Post"},
        {"orcid": "0000-0002-1297-6794"},
        "matt-post",
    ),
    (  # It shouldn't matter if other persons with the same name exist, only ORCID matters
        {"first": "Lin", "last": "Feng"},
        {"orcid": "0000-0003-4154-7507"},
        "lin-feng-7507",
    ),
    (  # When generated ID is already taken, append the last four digits of ORCID
        {"first": "Alex", "last": "Fenwick"},
        {"orcid": "0000-0003-3750-1098"},
        "alex-fenwick-1098",
    ),
    #### Edge cases
    (  # If function is already called with an ID for some reason, nothing happens
        {"first": "Alex", "last": "Fenwick"},
        {"id": "alex-fenwick"},
        "alex-fenwick",
    ),
)


@pytest.mark.parametrize(
    "name_dict, namespec_params, expected_result",
    test_cases_ingest_namespec,
)
def test_ingest_namespec(name_dict, namespec_params, expected_result, index):
    index.reset()
    index._load_people_index()
    name = Name.from_dict(name_dict)
    namespec = NameSpecification(name, **namespec_params)
    index.ingest_namespec(namespec)

    assert namespec.id == expected_result
    if namespec.id is not None:
        # Should also exist in (or have been added to) index
        assert namespec.id in index
        # ... with the name given here
        assert index[namespec.id].has_name(name)


def test_ingest_namespec_returns_namespec(index):
    ns1 = NameSpecification(Name("Matt", "Post"), orcid="0000-0002-1297-6794")
    ns2 = index.ingest_namespec(ns1)
    assert ns1 is ns2


##############################################################################
### Tests for saving people.json
##############################################################################


def test_people_data_roundtrip(index, tmp_path):
    index.load()
    data_in = index.path
    data_out = tmp_path / "people.json"
    index.save(data_out)
    assert data_out.is_file()
    with (
        open(data_in, "r", encoding="utf-8") as f,
        open(data_out, "r", encoding="utf-8") as g,
    ):
        expected = f.read()
        out = g.read()
    assert out == expected


def test_add_fields_to_people_data(index, tmp_path):
    index.load()
    data_out = tmp_path / "people.add_fields.json"

    # Modifications
    person = index["alex-fenwick"]
    person.add_name(Name("Marc Alex", "Fenwick"))
    person.degree = "Fakerhausen University"

    # Test that modifications are saved to people.json
    index.save(data_out)
    assert data_out.is_file()
    with open(data_out, "r", encoding="utf-8") as f:
        out = f.read()

    assert (
        """  "alex-fenwick": {
    "names": [
      {"first": "Alex", "last": "Fenwick"},
      {"first": "Marc Alex", "last": "Fenwick"}
    ],
    "degree": "Fakerhausen University",
    "orcid": "0009-0001-4567-8902"
  }"""
        in out
    )


def test_add_person_to_people_data_via_make_explicit(index, tmp_path):
    index.load()
    data_out = tmp_path / "people.make_explicit.json"

    # Modifications
    person = index[UNVERIFIED_PID_FORMAT.format(pid="dario-pretto")]
    person.make_explicit("dario-pretto")
    person.orcid = "0000-0002-3600-1510"

    # Test that modifications are saved to people.json
    index.save(data_out)
    assert data_out.is_file()
    with open(data_out, "r", encoding="utf-8") as f:
        out = f.read()

    assert (
        """  "dario-pretto": {
    "names": [
      {"first": "Dario", "last": "Pretto"}
    ],
    "orcid": "0000-0002-3600-1510"
  }"""
        in out
    )


def test_add_person_to_people_data_via_create_person(index, tmp_path):
    index.load()
    data_out = tmp_path / "people.create_person.json"

    # Modifications
    index.create(
        id="dario-pretto",
        names=[Name("Dario", "Pretto")],
        orcid="0000-0002-3600-1510",
    )

    # Test that modifications are saved to people.json
    index.save(data_out)
    assert data_out.is_file()
    with open(data_out, "r", encoding="utf-8") as f:
        out = f.read()

    assert (
        """  "dario-pretto": {
    "names": [
      {"first": "Dario", "last": "Pretto"}
    ],
    "orcid": "0000-0002-3600-1510"
  }"""
        in out
    )
