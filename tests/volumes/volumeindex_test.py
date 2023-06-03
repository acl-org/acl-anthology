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
from acl_anthology.volumes import VolumeIndex

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


class AnthologyFixture:
    datadir = f"{SCRIPTDIR}/../toy_anthology"


def test_get_volume():
    index = VolumeIndex(AnthologyFixture())
    # Fetch 2022.acl-main -- these should all be identical
    volume = index.get_volume("2022.acl-long")
    assert volume is not None
    assert volume is index.get_volume(("2022.acl", "long"))
    assert volume is index.get_volume(("2022.acl", "long", None))
    assert volume is index.get("2022.acl-long")
    assert volume is index.get(("2022.acl", "long", None))
