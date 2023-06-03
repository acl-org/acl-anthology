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
from acl_anthology.volumes import VolumeIndex, Volume

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


class AnthologyFixture:
    datadir = f"{SCRIPTDIR}/../toy_anthology"


def test_volume_attributes():
    # TODO: this is setup code
    index = VolumeIndex(AnthologyFixture())
    volume = index.get_volume("2022.acl-long")
    # this is test code
    assert isinstance(volume, Volume)
    assert volume.id == "long"
    assert volume.ingest_date == "2022-05-15"
    assert volume.address == "Dublin, Ireland"
    assert volume.publisher == "Association for Computational Linguistics"
    assert volume.month == "May"
    assert volume.year == "2022"
    assert volume.url == "2022.acl-long"
    assert volume.url_checksum == "b8317652"
    assert volume.venues == ["acl"]


def test_volume_attributes_j89():
    # TODO: this is setup code
    index = VolumeIndex(AnthologyFixture())
    volume = index.get_volume("J89-1")
    # this is test code
    assert isinstance(volume, Volume)
    assert volume.id == "1"
    assert volume.venues == ["cl"]
    assert volume.year == "1989"
