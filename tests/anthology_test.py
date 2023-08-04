# Copyright 2023 Marcel Bollmann <marcel@bollmann.me>
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
from pathlib import Path
from acl_anthology import Anthology

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))
DATADIR = Path(f"{SCRIPTDIR}/toy_anthology")

# TODO: tests in this file will mostly be integration tests, which are more
# expensive to run; can this be marked somehow?


def test_instantiate():
    anthology = Anthology(datadir=DATADIR)
    assert anthology.datadir == Path(DATADIR)


def test_get_volume(anthology):
    # Fetch 2022.acl-long -- these should all be identical
    volume = anthology.get_volume("2022.acl-long")
    assert volume is not None
    assert volume.full_id == "2022.acl-long"
    assert volume is anthology.get_volume(("2022.acl", "long", None))
    assert volume is anthology.get_volume("2022.acl-long.42")
    assert volume is anthology.get("2022.acl-long")
    assert volume is anthology.get(("2022.acl", "long", None))


def test_get_paper(anthology):
    # Fetch 2022.acl-long.1
    paper = anthology.get_paper("2022.acl-long.1")
    assert paper is not None
    assert paper.id == "1"
    assert paper.full_id == "2022.acl-long.1"


def test_iter_volumes(anthology):
    # Iterate over all volumes
    expected = set(("2022.acl", "J89", "L06"))
    found = set()
    count = 0
    for volume in anthology.iter_volumes():
        count += 1
        found.add(volume.collection_id)
    assert expected == found
    assert count == 10


def test_iter_volumes_by_id(anthology):
    # Iterate over 2022.acl volumes
    expected = set(("long", "short", "demo", "tutorials", "srw"))
    found = set()
    for volume in anthology.iter_volumes("2022.acl"):
        found.add(volume.id)
    assert expected == found


def test_iter_papers(anthology):
    # Iterate over all papers
    expected = set(("2022.acl", "J89", "L06"))
    found = set()
    count = 0
    for paper in anthology.iter_papers():
        count += 1
        found.add(paper.collection_id)
    assert expected == found
    assert count == 1355


def test_iter_papers_by_collection_id(anthology):
    # Iterate over J89 papers
    count = 0
    for paper in anthology.iter_papers("J89"):
        assert paper.collection_id == "J89"
        count += 1
    assert count == 62


def test_iter_papers_by_volume_id(anthology):
    # Iterate over J89-1 papers
    expected = set(str(i) for i in range(0, 15))
    found = set()
    for paper in anthology.iter_papers("J89-1"):
        assert paper.collection_id == "J89"
        assert paper.volume_id == "1"
        found.add(paper.id)
    assert expected == found
