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

import os
import filecmp
import pytest
from lxml import etree
from pathlib import Path

from acl_anthology import Anthology
from acl_anthology.sigs import SIG
from acl_anthology.venues import Venue
from acl_anthology.utils import xml


# Map from [repo]/python/tests to [repo]/data
DATADIR = Path(os.path.dirname(os.path.realpath(__file__))) / ".." / ".." / "data"


def pytest_generate_tests(metafunc):
    # Discovers all XML files in DATADIR and parametrizes tests
    if "full_anthology_collection_id" in metafunc.fixturenames:
        metafunc.parametrize(
            "full_anthology_collection_id",
            [xmlpath.name[:-4] for xmlpath in sorted(DATADIR.glob("xml/*.xml"))],
        )
    # Discovers all venue YAML files in DATADIR and parametrizes tests
    if "full_anthology_venue_id" in metafunc.fixturenames:
        metafunc.parametrize(
            "full_anthology_venue_id",
            [
                yamlpath.name[:-5]
                for yamlpath in sorted(DATADIR.glob("yaml/venues/*.yaml"))
            ],
        )
    # Discovers all SIG YAML files in DATADIR and parametrizes tests
    if "full_anthology_sig_id" in metafunc.fixturenames:
        metafunc.parametrize(
            "full_anthology_sig_id",
            [yamlpath.name[:-5] for yamlpath in sorted(DATADIR.glob("yaml/sigs/*.yaml"))],
        )


@pytest.fixture(scope="module")
def full_anthology():
    return Anthology(datadir=DATADIR)


@pytest.mark.integration
def test_anthology_from_repo(tmp_path):
    # Test that we can instantiate from the GitHub repo
    _ = Anthology.from_repo(path=tmp_path, verbose=True)


@pytest.mark.integration
def test_full_anthology_should_validate_schema(full_anthology):
    for collection in full_anthology.collections.values():
        collection.validate_schema()


@pytest.mark.integration
@pytest.mark.parametrize("minimal_diff", (True, False))
def test_full_anthology_roundtrip_xml(
    full_anthology, full_anthology_collection_id, tmp_path, minimal_diff
):
    # Test for equivalence when loading & immediately saving the XML files
    collection = full_anthology.collections[full_anthology_collection_id]
    outfile = tmp_path / f"{full_anthology_collection_id}.generated.xml"
    # Load & save collection
    collection.load()
    collection.save(path=outfile, minimal_diff=minimal_diff)
    # Compare
    assert outfile.is_file()

    if not minimal_diff:
        # Test for logical equivalence
        expected = etree.parse(collection.path)
        result = etree.parse(outfile)
        xml.assert_equals(result.getroot(), expected.getroot())

    else:
        # Test for byte-level equivalence
        if not filecmp.cmp(outfile, collection.path):
            # Assertion likely to fail, but assert on the lines so we see an
            # actual diff in the pytest output
            with (
                open(outfile, "r", encoding="utf-8") as f,
                open(collection.path, "r", encoding="utf-8") as g,
            ):
                out_lines, exp_lines = f.readlines(), g.readlines()

            # A few old files do not have the <?xml ...> declaration; ignore that
            if not exp_lines[0].startswith("<?xml"):
                out_lines.pop(0)  # this *will* start with <?xml ...>

            assert exp_lines == out_lines


@pytest.mark.integration
def test_full_anthology_roundtrip_venue_yaml(
    full_anthology, full_anthology_venue_id, tmp_path
):
    # Test for equivalence when loading & immediately saving the venue YAML files
    venue = full_anthology.venues[full_anthology_venue_id]
    outfile = tmp_path / f"{full_anthology_venue_id}.yaml"
    # Save venue (it's already loaded when accessing it)
    venue.save(path=outfile)
    # Compare
    assert outfile.is_file()
    out = Venue.load_from_yaml(outfile, full_anthology)
    # Test for logical equivalence only
    assert out == venue


@pytest.mark.integration
def test_full_anthology_roundtrip_sig_yaml(
    full_anthology, full_anthology_sig_id, tmp_path
):
    # Test for equivalence when loading & immediately saving the SIG YAML files
    sig = full_anthology.sigs[full_anthology_sig_id]
    outfile = tmp_path / f"{full_anthology_sig_id}.yaml"
    # Save SIG (it's already loaded when accessing it)
    sig.save(path=outfile)
    # Compare
    assert outfile.is_file()
    out = SIG.load_from_yaml(full_anthology.sigs, outfile)
    # Test for logical equivalence only, ignoring order of meetings for now
    for attrib in ("id", "acronym", "name", "url"):
        assert getattr(out, attrib) == getattr(sig, attrib)
    assert set(out.meetings) == set(sig.meetings)
