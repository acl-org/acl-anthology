# Copyright 2025 Marcel Bollmann <marcel@bollmann.me>
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


from acl_anthology.collections import BibkeyIndex


def test_bibkeys_indexing(anthology):
    index = BibkeyIndex(anthology.collections)
    index.load()
    assert index.is_data_loaded
    assert len(index) > 850
    assert "feng-etal-2022-dynamic" in index
    assert index.get("feng-etal-2022-dynamic").full_id_tuple == ("2022.acl", "long", "10")
    assert "gubelmann-etal-2022-philosophically" in index
    assert index.get("gubelmann-etal-2022-philosophically").full_id_tuple == (
        "2022.naloma",
        "1",
        "5",
    )
    assert "cl-1989-linguistics-15-number-4" in index
    assert index.get("cl-1989-linguistics-15-number-4").full_id_tuple == ("J89", "4", "0")
