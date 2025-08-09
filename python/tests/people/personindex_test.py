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
from acl_anthology.exceptions import NameSpecResolutionError, PersonDefinitionError
from acl_anthology.people import Name, NameLink, NameSpecification, Person, PersonIndex


@pytest.fixture
def index(anthology_stub):
    return PersonIndex(anthology_stub)


@pytest.fixture
def index_with_toy_anthology(anthology):
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


def test_build_personindex(index_with_toy_anthology):
    index = index_with_toy_anthology
    assert not index.is_data_loaded
    index.build(show_progress=False)
    assert index.is_data_loaded
    assert "yang-liu-microsoft" in index
    assert Name("Nicoletta", "Calzolari") in index.by_name
    assert "0000-0003-2598-8150" in index.by_orcid


def test_build_personindex_automatically(index_with_toy_anthology):
    index = index_with_toy_anthology
    assert not index.is_data_loaded
    persons = index.get_by_name(Name("Nicoletta", "Calzolari"))
    assert index.is_data_loaded
    assert len(persons) == 1


def test_canonical_name_never_has_script(index_with_toy_anthology):
    index = index_with_toy_anthology
    for person in index.values():
        assert person.canonical_name.script is None


def test_get_person_coauthors(index_with_toy_anthology):
    index = index_with_toy_anthology
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


def test_get_person_coauthors_counter(index_with_toy_anthology):
    index = index_with_toy_anthology
    coauthors = index.find_coauthors_counter("unverified/kathleen-dahlgren")
    assert len(coauthors) == 1
    assert coauthors["unverified/joyce-mcdowell"] == 1

    person = index.get_by_name(Name("Preslav", "Nakov"))[0]
    coauthors = index.find_coauthors_counter(person)
    assert len(coauthors) == 2
    assert coauthors["unverified/joyce-mcdowell"] == 0
    assert coauthors["unverified/aline-villavicencio"] == 2


def test_get_by_namespec(index_with_toy_anthology):
    index = index_with_toy_anthology
    ns1 = NameSpecification(Name("Yang", "Liu"))
    ns2 = NameSpecification(Name("Yang", "Liu"), id="yang-liu-microsoft")
    with pytest.raises(NameSpecResolutionError):
        index.get_by_namespec(ns1)
    person = index.get_by_namespec(ns2)
    assert person.id == "yang-liu-microsoft"
    assert person.canonical_name == Name("Yang", "Liu")


def test_get_by_name_variants(index_with_toy_anthology):
    # It should be possible to find a person by a name variant
    index = index_with_toy_anthology
    persons = index.get_by_name(Name("洋", "刘"))
    assert len(persons) == 1
    assert persons[0].id == "yang-liu-ict"


def test_get_by_orcid(index_with_toy_anthology):
    index = index_with_toy_anthology
    person = index.get_by_orcid("0000-0003-2598-8150")
    assert person is not None
    assert person.id == "marcel-bollmann"
    assert index.get_by_orcid("0000-0000-0000-0000") is None


##############################################################################
### Tests for name resolution logic
##############################################################################

# Format: (Name, NameSpecification attributes, expected ID or Exception)
test_cases_resolve_namespec = (
    #### "No match" cases
    (  # Name does not exist in people.yaml
        {"first": "Matthew", "last": "Stevens"},
        {},
        "unverified/matthew-stevens",
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
        "unverified/pranav-anand",
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
        "unverified/yang-liu",
    ),
    (  # ... will resolve to known person with explicit ID
        {"first": "Yang", "last": "Liu"},
        {"id": "yang-liu-icsi"},
        "yang-liu-icsi",
    ),
    (  # ... affiliation is NOT used in any way for name resolution
        {"first": "Yang", "last": "Liu"},
        {"affiliation": "Microsoft Cognitive Services Research"},
        "unverified/yang-liu",
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
def test_resolve_namespec(
    name_dict, namespec_params, expected_result, index_with_toy_anthology
):
    index = index_with_toy_anthology
    index._load_people_index()
    name = Name.from_dict(name_dict)
    namespec = NameSpecification(name, **namespec_params)

    if isinstance(expected_result, str):
        person = index.resolve_namespec(namespec, allow_creation=True)
        assert person.has_name(name)
        assert person.id == expected_result
    elif isinstance(expected_result, type):
        with pytest.raises(expected_result):
            index.resolve_namespec(namespec, allow_creation=True)
    else:
        raise ValueError(
            f"Test cannot take expected result of type {type(expected_result)}"
        )


def test_resolve_namespec_disallow_creation(index_with_toy_anthology):
    index = index_with_toy_anthology
    index._load_people_index()
    # If we would map to an unverified ID but allow_creation is False, should raise
    with pytest.raises(NameSpecResolutionError):
        index.resolve_namespec(
            NameSpecification(Name("Matthew", "Stevens")), allow_creation=False
        )


def test_resolve_namespec_name_scoring_for_unverified_ids(index):
    # Person does not exist, will create an unverified ID
    person1 = index.resolve_namespec(
        NameSpecification(Name("Rene", "Muller")), allow_creation=True
    )
    assert person1.id == "unverified/rene-muller"
    assert person1.canonical_name == Name("Rene", "Muller")
    # Name resolves to the same person as above
    person2 = index.resolve_namespec(
        NameSpecification(Name("René", "Müller")), allow_creation=True
    )
    assert person2.id == "unverified/rene-muller"
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
def test_check_namelink_after_resolve_namespec(
    name_dict, expected_namelink, index_with_toy_anthology
):
    index = index_with_toy_anthology
    index._load_people_index()
    name = Name.from_dict(name_dict)
    namespec = NameSpecification(name)
    person = index.resolve_namespec(namespec, allow_creation=True)

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
def test_ingest_namespec(
    name_dict, namespec_params, expected_result, index_with_toy_anthology
):
    index = index_with_toy_anthology
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


def test_ingest_namespec_returns_namespec(index_with_toy_anthology):
    ns1 = NameSpecification(Name("Matt", "Post"), orcid="0000-0002-1297-6794")
    ns2 = index_with_toy_anthology.ingest_namespec(ns1)
    assert ns1 is ns2


##############################################################################
### Tests for saving people.yaml
##############################################################################


def test_people_roundtrip_yaml(index_with_toy_anthology, tmp_path):
    index = index_with_toy_anthology
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
