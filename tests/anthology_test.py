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
