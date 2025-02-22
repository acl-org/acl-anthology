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

import pytest
from acl_anthology.collections import CollectionIndex


def test_get_collection(anthology_stub):
    index = CollectionIndex(anthology_stub)
    # Fetch 2022.acl
    collection = index.get("2022.acl")
    assert collection is not None
    assert collection.id == "2022.acl"


def test_create_collection(anthology_stub):
    index = CollectionIndex(anthology_stub)
    # Create 2099.acl
    collection = index.create("2099.acl")
    assert collection.id == "2099.acl"
    assert collection.parent is index
    assert collection.id in index


def test_create_collection_should_raise(anthology_stub):
    index = CollectionIndex(anthology_stub)
    # 2022.acl already exists
    with pytest.raises(ValueError):
        index.create("2022.acl")
    # Collections can't be created with old-style IDs
    with pytest.raises(ValueError):
        index.create("P50")
