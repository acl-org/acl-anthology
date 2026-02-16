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
        "emily-prudhommeaux",
        "steven-krauwer",
        "yang-liu-icsi",
        "yang-liu-ict",
        "yang-liu-microsoft",
    ):
        assert pid in index


def test_load_people_index_registers_names(index_stub):
    index = index_stub
    index.reset()
    index._load_people_index()
    index.is_data_loaded = True
    n1 = Name("Steven", "Krauwer")
    n2 = Name("S.", "Krauwer")
    assert n1 in index.by_name
    assert n2 in index.by_name
    pid = index.by_name[n1]
    assert pid == index.by_name[n2]
    assert pid[0] in index


def test_add_person(index_stub):
    index = index_stub
    index.reset()
    p1 = Person("yang-liu", index.parent, [Name("Yang", "Liu")])
    index.add_person(p1)
    index.is_data_loaded = True  # to prevent it attempting to build itself
    assert "yang-liu" in index
    assert Name("Yang", "Liu") in index.by_name
    assert index.by_name[Name("Yang", "Liu")] == ["yang-liu"]
    assert index.get_by_name(Name("Yang", "Liu"))[0] is p1
    assert index.get_by_namespec(NameSpecification(Name("Yang", "Liu"))) is p1
    assert index.get("yang-liu") is p1
    with pytest.raises(ValueError):
        index.add_person(Person("yang-liu", index.parent))


def test_similar_names_defined_in_people_index(index_stub):
    index = index_stub
    index.reset()
    index._load_people_index()
    index.is_data_loaded = True
    similar = index.similar.subset("pranav-a")
    assert similar == {"pranav-a", "pranav-anand"}


def test_similar_names_through_same_canonical_name(index):
    assert not index.is_data_loaded
    index.build(show_progress=False)
    assert index.is_data_loaded
    similar = index.similar.subset("yang-liu-ict")
    assert similar == {
        "yang-liu-icsi",
        "yang-liu-ict",
        "yang-liu-microsoft",
        "yang-liu/unverified",
    }


def test_build_personindex(index):
    assert not index.is_data_loaded
    index.build(show_progress=True)
    assert index.is_data_loaded
    assert "yang-liu/unverified" in index
    assert "yang-liu-microsoft" in index
    assert Name("Nicoletta", "Calzolari") in index.by_name
    assert "0000-0003-2598-8150" in index.by_orcid


def test_build_personindex_automatically(index):
    assert not index.is_data_loaded
    persons = index.get_by_name(Name("Nicoletta", "Calzolari"))
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
    person = index.by_name[Name("Kathleen", "Dahlgren")][0]
    coauthors = index.find_coauthors(person)
    assert len(coauthors) == 1
    assert coauthors[0].canonical_name == Name("Joyce", "McDowell")

    person = index.get_by_name(Name("Preslav", "Nakov"))[0]
    coauthors = index.find_coauthors(person)
    assert len(coauthors) == 2
    # Both volumes where Preslav Nakov is editor have frontmatter, so should still be counted
    coauthors = index.find_coauthors(person, include_volumes=False)
    assert len(coauthors) == 2


def test_get_person_coauthors_counter(index):
    coauthors = index.find_coauthors_counter(
        UNVERIFIED_PID_FORMAT.format(pid="kathleen-dahlgren")
    )
    assert len(coauthors) == 1
    assert coauthors[UNVERIFIED_PID_FORMAT.format(pid="joyce-mcdowell")] == 1

    person = index.get_by_name(Name("Preslav", "Nakov"))[0]
    coauthors = index.find_coauthors_counter(person)
    assert len(coauthors) == 2
    assert coauthors[UNVERIFIED_PID_FORMAT.format(pid="joyce-mcdowell")] == 0
    assert coauthors[UNVERIFIED_PID_FORMAT.format(pid="aline-villavicencio")] == 2


def test_get_by_namespec(index):
    ns1 = NameSpecification(Name("Li", "Feng"))  # does not exist
    ns2 = NameSpecification(Name("Yang", "Liu"), id="yang-liu-microsoft")
    with pytest.raises(NameSpecResolutionError):
        index.get_by_namespec(ns1)
    person = index.get_by_namespec(ns2)
    assert person.id == "yang-liu-microsoft"
    assert person.canonical_name == Name("Yang", "Liu")


def test_get_by_name_variants(index):
    # It should be possible to find a person by a name variant
    persons = index.get_by_name(Name("洋", "刘"))
    assert len(persons) == 1
    assert persons[0].id == "yang-liu-ict"


def test_get_by_orcid(index):
    person = index.get_by_orcid("0000-0003-2598-8150")
    assert person is not None
    assert person.id == "marcel-bollmann"
    assert index.get_by_orcid("0000-0000-0000-0000") is None


def test_change_orcid(index):
    person = index.get_by_orcid("0000-0003-2598-8150")
    assert person is not None
    assert person.id == "marcel-bollmann"
    person.orcid = "0000-0002-2909-0906"
    assert index.get_by_orcid("0000-0003-2598-8150") is None
    assert index.get_by_orcid("0000-0002-2909-0906") is person


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


def test_create_person_should_fail_on_duplicate_orcid(index):
    with pytest.raises(ValueError):
        index.create(
            id="marcel-bollmann-twin",
            names=[Name("Marcel", "Bollmann")],
            orcid="0000-0003-2598-8150",  # already assigned to "marcel-bollmann"
        )


def test_create_person_should_fail_on_duplicate_id(index):
    with pytest.raises(AnthologyInvalidIDError):
        index.create(
            id="marcel-bollmann",  # already exists
            names=[Name("Marcel", "Bollmann")],
        )


def test_create_person_should_fail_on_unverified_id(index):
    with pytest.raises(AnthologyInvalidIDError):
        index.create(
            id=UNVERIFIED_PID_FORMAT.format(
                pid="john-doe"
            ),  # cannot create this manually
            names=[Name("John", "Doe")],
        )


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
            NameSpecification(Name("Yang", "Liu"), id="yang-liu-ict"),
            NameSpecification(Name("Yang", "Liu")),
        ],
        example_id,
    )
    # Case 2 – should resolve to same unverified person -> warning
    with pytest.warns(NameSpecResolutionWarning):
        index._add_to_index(
            [
                NameSpecification(Name("Yang", "Liu")),
                NameSpecification(Name("Yang", "Liu")),
            ],
            example_id,
        )
    # Case 3 – should resolve to same verified person -> error
    with pytest.raises(NameSpecResolutionError):
        index._add_to_index(
            [
                NameSpecification(Name("Steven", "Krauwer"), id="steven-krauwer"),
                NameSpecification(Name("S.", "Krauwer"), id="steven-krauwer"),
            ],
            example_id,
        )


##############################################################################
### Tests for changing Person attributes that should update the index
##############################################################################


def test_person_id_change_should_update_index(anthology):
    index = anthology.people
    person = index["marcel-bollmann"]
    person.id = "marcel-bollmann-rub"
    assert "marcel-bollmann" not in index
    assert "marcel-bollmann-rub" in index
    assert index.by_orcid["0000-0003-2598-8150"] == "marcel-bollmann-rub"
    assert index.by_name[Name("Marcel", "Bollmann")] == ["marcel-bollmann-rub"]


def test_person_orcid_change_should_update_index(anthology):
    index = anthology.people
    person = index["yang-liu-ict"]
    orcid = "0000-0003-4154-7507"
    assert orcid not in index.by_orcid
    person.orcid = orcid
    assert orcid in index.by_orcid
    assert index.by_orcid[orcid] == "yang-liu-ict"


def test_person_add_name_should_update_index(anthology):
    index = anthology.people
    person = index["marcel-bollmann"]
    name = Name("Marc Marcel", "Bollmann")
    assert not index.by_name[name]
    person.add_name(name)
    assert index.by_name[name] == ["marcel-bollmann"]
    assert index.slugs_to_verified_ids[name.slugify()] == set(["marcel-bollmann"])


def test_person_remove_name_should_update_index(anthology):
    index = anthology.people
    person = index["steven-krauwer"]
    name = Name("S.", "Krauwer")
    assert index.by_name[name] == ["steven-krauwer"]
    person.remove_name(name)
    assert not index.by_name[name]
    assert not index.slugs_to_verified_ids[name.slugify()]


def test_person_setting_names_should_update_index(anthology):
    index = anthology.people
    person = index["steven-krauwer"]
    names = [Name("Steven", "Krauwer"), Name("Steven J.", "Krauwer")]
    person.names = names
    # previously existing name
    assert index.by_name[names[0]] == ["steven-krauwer"]
    # added name
    assert index.by_name[names[1]] == ["steven-krauwer"]
    # removed name
    assert not index.by_name[Name("S.", "Krauwer")]


##############################################################################
### Tests for name resolution logic
##############################################################################

# Format: (Name, NameSpecification attributes, expected ID or Exception)
test_cases_resolve_namespec = (
    #### "No match" cases
    (  # Name does not exist in people.yaml
        {"first": "Matthew", "last": "Stevens"},
        {},
        UNVERIFIED_PID_FORMAT.format(pid="matthew-stevens"),
    ),
    (  # Person with explicit ID does not exist in people.yaml
        {"first": "Matthew", "last": "Stevens"},
        {"id": "matthew-stevens"},
        PersonDefinitionError,
    ),
    #### "One match" cases
    (  # Name exists in people.yaml, unambiguous
        {"first": "Steven", "last": "Krauwer"},
        {},
        "steven-krauwer",
    ),
    (  # Name exists in people.yaml, unambiguous, but not as canonical name
        {"first": "Emily T.", "last": "Prud’hommeaux"},
        {},
        "emily-prudhommeaux",
    ),
    (  # Person unambiguous, but has `disable_name_matching: true`
        {"first": "Pranav", "last": "Anand"},
        {},
        UNVERIFIED_PID_FORMAT.format(pid="pranav-anand"),
    ),
    (  # `disable_name_matching: true` doesn't affect NameSpecs with explicit ID
        {"first": "Pranav", "last": "Anand"},
        {"id": "pranav-anand"},
        "pranav-anand",
    ),
    (  # Name exists in people.yaml with an ORCID, unambiguous
        {"first": "Marcel", "last": "Bollmann"},
        {},
        "marcel-bollmann",
    ),
    (  # ... with explicit ID
        {"first": "Marcel", "last": "Bollmann"},
        {"id": "marcel-bollmann"},
        "marcel-bollmann",
    ),
    (  # ... with explicit ID & ORCID
        {"first": "Marcel", "last": "Bollmann"},
        {"id": "marcel-bollmann", "orcid": "0000-0003-2598-8150"},
        "marcel-bollmann",
    ),
    (  # ... with explicit ID & ORCID, but ORCID doesn't match
        {"first": "Marcel", "last": "Bollmann"},
        {"id": "marcel-bollmann", "orcid": "0000-0002-7491-7669"},
        PersonDefinitionError,
    ),
    (  # ... with explicit ID & ORCID, but name isn't listed in people.yaml
        {"first": "Marc Marcel", "last": "Bollmann"},
        {"id": "marcel-bollmann", "orcid": "0000-0003-2598-8150"},
        PersonDefinitionError,
    ),
    (  # Name matches an existing, unambiguous name via slugification
        {"first": "Stèven", "last": "Kräuwer"},
        {},
        "steven-krauwer",
    ),
    (  # ... even when it's not the canonical name
        {"first": "Emily T.", "last": "Prüd’hommeaux"},
        {},
        "emily-prudhommeaux",
    ),
    (  # ... even with different first/last split
        {"first": "Emily", "last": "T. Prud’hommeaux"},
        {},
        "emily-prudhommeaux",
    ),
    #### "2+ matches" cases
    (  # Name exists in people.yaml for several people
        {"first": "Yang", "last": "Liu"},
        {},
        UNVERIFIED_PID_FORMAT.format(pid="yang-liu"),
    ),
    (  # ... will resolve to known person with explicit ID
        {"first": "Yang", "last": "Liu"},
        {"id": "yang-liu-icsi"},
        "yang-liu-icsi",
    ),
    (  # ... affiliation is NOT used in any way for name resolution
        {"first": "Yang", "last": "Liu"},
        {"affiliation": "Microsoft Cognitive Services Research"},
        UNVERIFIED_PID_FORMAT.format(pid="yang-liu"),
    ),
    #### Malformed name specifications
    (  # Person with explicit ORCID, but no explicit ID (always disallowed)
        {"first": "Matthew", "last": "Stevens"},
        {"orcid": "0000-0002-7491-7669"},
        NameSpecResolutionError,
    ),
    (  # ... even if the person exists (ID is still required)
        {"first": "Marcel", "last": "Bollmann"},
        {"orcid": "0000-0003-2598-8150"},
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
    # Names that are explicitly defined in people.yaml should always have
    # NameLink.EXPLICIT after resolve_namespec()
    (
        {"first": "Steven", "last": "Krauwer"},
        NameLink.EXPLICIT,
    ),
    (
        {"first": "S.", "last": "Krauwer"},
        NameLink.EXPLICIT,
    ),
    (
        {"first": "Marcel", "last": "Bollmann"},
        NameLink.EXPLICIT,
    ),
    # Names that are matched via slugification should always have
    # NameLink.INFERRED after resolve_namespec()
    (
        {"first": "Stèven", "last": "Kräuwer"},
        NameLink.INFERRED,
    ),
    (
        {"first": "Emily T.", "last": "Prüd’hommeaux"},
        NameLink.INFERRED,
    ),
    (
        {"first": "Emily", "last": "T. Prud’hommeaux"},
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
    #### ORCID in the ingestion material, matches a person in our `people.yaml`
    (
        {"first": "Marcel", "last": "Bollmann"},
        {"orcid": "0000-0003-2598-8150"},
        "marcel-bollmann",
    ),
    (  # ... even if the name wasn't recorded yet in `people.yaml`
        {"first": "Marc Marcel", "last": "Bollmann"},
        {"orcid": "0000-0003-2598-8150"},
        "marcel-bollmann",
    ),
    #### ORCID in the ingestion material, no match in our `people.yaml`
    (  # Person should be created
        {"first": "Matt", "last": "Post"},
        {"orcid": "0000-0002-1297-6794"},
        "matt-post",
    ),
    (  # It shouldn't matter if other persons with the same name exist, only ORCID matters
        {"first": "Yang", "last": "Liu"},
        {"orcid": "0000-0003-4154-7507"},
        "yang-liu",  # this ID is actually not defined in people.yaml!
    ),
    (  # When generated ID is already taken, append the last four digits of ORCID
        {"first": "Marcel", "last": "Bollmann"},
        {"orcid": "0000-0003-3750-1098"},
        "marcel-bollmann-1098",
    ),
    #### Edge cases
    (  # If function is already called with an ID for some reason, nothing happens
        {"first": "Marcel", "last": "Bollmann"},
        {"id": "marcel-bollmann"},
        "marcel-bollmann",
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


def test_ingest_namespec_should_warn(index):
    index.reset()
    index._load_people_index()
    # This person exists (as verified), but without an ORCID, so ingesting them
    # _with_ an ORCID will create a new ID, but should emit a warning
    name = Name.from_dict({"first": "Steven", "last": "Krauwer"})
    namespec = NameSpecification(name, orcid="0000-0002-4236-2611")

    with pytest.warns(NameSpecResolutionWarning):
        index.ingest_namespec(namespec)

    assert namespec.id == "steven-krauwer-2611"


def test_ingest_namespec_returns_namespec(index):
    ns1 = NameSpecification(Name("Matt", "Post"), orcid="0000-0002-1297-6794")
    ns2 = index.ingest_namespec(ns1)
    assert ns1 is ns2


##############################################################################
### Tests for saving people.yaml
##############################################################################


def test_people_yaml_roundtrip(index, tmp_path):
    index.load()
    yaml_in = index.path
    yaml_out = tmp_path / "people.yaml"
    index.save(yaml_out)
    assert yaml_out.is_file()
    with (
        open(yaml_in, "r", encoding="utf-8") as f,
        open(yaml_out, "r", encoding="utf-8") as g,
    ):
        expected = f.read()
        out = g.read()
    assert out == expected


def test_add_fields_to_people_yaml(index, tmp_path):
    index.load()
    yaml_out = tmp_path / "people.add_fields.yaml"

    # Modifications
    person = index["marcel-bollmann"]
    person.add_name(Name("Marc Marcel", "Bollmann"))
    person.degree = "Ruhr-Universität Bochum"

    # Test that modifications are saved to people.yaml
    index.save(yaml_out)
    assert yaml_out.is_file()
    with open(yaml_out, "r", encoding="utf-8") as f:
        out = f.read()

    assert (
        """
marcel-bollmann:
  degree: Ruhr-Universität Bochum
  names:
  - {first: Marcel, last: Bollmann}
  - {first: Marc Marcel, last: Bollmann}
  orcid: 0000-0003-2598-8150"""
        in out
    )


def test_add_person_to_people_yaml_via_make_explicit(index, tmp_path):
    index.load()
    yaml_out = tmp_path / "people.make_explicit.yaml"

    # Modifications
    person = index[UNVERIFIED_PID_FORMAT.format(pid="preslav-nakov")]
    person.make_explicit("preslav-nakov")
    person.orcid = "0000-0002-3600-1510"

    # Test that modifications are saved to people.yaml
    index.save(yaml_out)
    assert yaml_out.is_file()
    with open(yaml_out, "r", encoding="utf-8") as f:
        out = f.read()

    assert (
        """
preslav-nakov:
  names:
  - {first: Preslav, last: Nakov}
  orcid: 0000-0002-3600-1510"""
        in out
    )


def test_add_person_to_people_yaml_via_create_person(index, tmp_path):
    index.load()
    yaml_out = tmp_path / "people.create_person.yaml"

    # Modifications
    index.create(
        id="preslav-nakov",
        names=[Name("Preslav", "Nakov")],
        orcid="0000-0002-3600-1510",
    )

    # Test that modifications are saved to people.yaml
    index.save(yaml_out)
    assert yaml_out.is_file()
    with open(yaml_out, "r", encoding="utf-8") as f:
        out = f.read()

    assert (
        """
preslav-nakov:
  names:
  - {first: Preslav, last: Nakov}
  orcid: 0000-0002-3600-1510"""
        in out
    )
