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

import os
import pytest
from pathlib import Path
from acl_anthology import Anthology

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))
DATADIR = Path(f"{SCRIPTDIR}/.official_anthology_git")


@pytest.fixture
def anthology_from_repo():
    return Anthology.from_repo(path=DATADIR, verbose=True)


@pytest.mark.integration
def test_anthology_from_official_repo(anthology_from_repo):
    anthology = anthology_from_repo
    anthology.load_all()
    assert len(anthology.collections) > 1145
    assert anthology.get_paper("2023.acl-long.1") is not None


@pytest.mark.integration
def test_anthology_validate_schema(anthology_from_repo):
    anthology = anthology_from_repo
    for collection in anthology.collections.values():
        collection.validate_schema()
