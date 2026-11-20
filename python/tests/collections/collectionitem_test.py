# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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
from attrs import define

from acl_anthology.collections import Paper, Volume
from acl_anthology.collections.collectionitem import CollectionItem, ContainerItem
from acl_anthology.exceptions import AnthologyInvalidIDError


def test_collectionitem_cannot_be_instantiated(anthology):
    collection = anthology.get_collection("2022.facl")
    with pytest.raises(TypeError, match="abstract"):
        CollectionItem("1", collection, title="Foo")
    with pytest.raises(TypeError, match="abstract"):
        ContainerItem("1", collection, title="Foo")


def test_collectionitem_subclass_must_implement_abstract_members(anthology):
    @define
    class IncompleteItem(CollectionItem["Volume"]):
        @property
        def collection(self):
            return self.parent.parent

    volume = anthology.get_volume("2022.facl-long")
    with pytest.raises(TypeError, match="full_id_tuple"):
        IncompleteItem("1", volume, title="Foo")


def test_collectionitem_hierarchy():
    assert issubclass(Paper, CollectionItem)
    assert not issubclass(Paper, ContainerItem)
    assert issubclass(Volume, CollectionItem)
    assert issubclass(Volume, ContainerItem)


@pytest.mark.parametrize(
    "full_id, collection_id",
    (
        ("2022.facl-long", "2022.facl"),
        ("2022.facl-long.1", "2022.facl"),
        ("K06-1", "K06"),
        ("K06-1001", "K06"),
    ),
)
def test_collectionitem_shared_attributes(anthology, full_id, collection_id):
    item = anthology.get(full_id)
    assert isinstance(item, CollectionItem)
    assert item.full_id == full_id
    assert item.collection_id == collection_id
    assert item.collection is anthology.get_collection(collection_id)
    assert item.root is anthology
    assert item.title


def test_collectionitem_title_is_keyword_only(anthology):
    volume = anthology.get_volume("2022.facl-long")
    with pytest.raises(TypeError):
        Paper("42", volume, "nn-1900-minimal", "A minimal example")


def test_paper_invalid_id_names_class(anthology):
    volume = anthology.get_volume("2022.facl-long")
    with pytest.raises(AnthologyInvalidIDError, match="Not a valid Paper ID"):
        Paper("in valid", volume, bibkey="nn-1900-foo", title="Foo")


def test_volume_invalid_id_names_class(anthology):
    collection = anthology.get_collection("2022.facl")
    with pytest.raises(AnthologyInvalidIDError, match="Not a valid Volume ID"):
        Volume("in valid", collection, "proceedings", booktitle="Foo", year="2022")
