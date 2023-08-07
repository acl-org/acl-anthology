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

from __future__ import annotations
from typing import Iterator, Optional, TYPE_CHECKING

from .collection import Collection

if TYPE_CHECKING:
    from ..anthology import Anthology


class CollectionIndex:
    """Index object through which all collections, volumes, events, and papers can be accessed.

    Attributes:
        parent (Anthology): The parent Anthology instance to which this index belongs.
    """

    def __init__(self, parent: Anthology) -> None:
        self.parent = (
            parent  # TODO: when feature-complete, check if this is actually needed
        )
        self.collections: dict[str, Collection] = {}

        self._find_collections()

    def __iter__(self) -> Iterator[Collection]:
        """Returns an iterator over all collections."""
        return iter(self.collections.values())

    def __len__(self) -> int:
        """Returns the number of collections."""
        return len(self.collections)

    def get(self, collection_id: str) -> Optional[Collection]:
        """Access a collection in this index by its ID.

        Parameters:
            collection_id: The collection ID (e.g. "W16").
        """
        return self.collections.get(collection_id)

    def _find_collections(self) -> None:
        """Finds all XML data files and indexes them by their collection ID.

        This function is called automatically when the CollectionIndex is initialized.

        Note:
            Currently assumes that XML files are **always** named according to the collection ID they
            contain; i.e., a file named "L16.xml" *must* contain the collection with ID "L16".
        """
        for xmlpath in self.parent.datadir.glob("xml/*.xml"):
            # Assumes that XML files are **always** named as their collection
            # IDs.  --- Alternatively, could peek at the first two lines of the
            # file to parse only the <collection id="..."> tag?
            collection_id = xmlpath.name[:-4]
            self.collections[collection_id] = Collection(collection_id, xmlpath)
