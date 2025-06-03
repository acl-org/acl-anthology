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
import pytest
from pathlib import Path

from acl_anthology import Anthology


# Map from [repo]/python/tests to [repo]/data
DATADIR = Path(os.path.dirname(os.path.realpath(__file__))) / ".." / ".." / "data"


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
