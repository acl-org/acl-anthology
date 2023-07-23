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
from typing import Optional, TYPE_CHECKING

from ..utils.ids import parse_id, AnthologyID
from .collection import Collection
from .volume import Volume
from .paper import Paper

if TYPE_CHECKING:
    from ..anthology import Anthology


class CollectionIndex:
    """Index object through which all collections, volumes, events, and papers can be accessed.

    Attributes:
        anthology (Anthology): The parent Anthology instance to which this index belongs.
    """

    def __init__(self, anthology: Anthology) -> None:
        self._anthology = (
            anthology  # TODO: when feature-complete, check if this is actually needed
        )
        self.collections: dict[str, Collection] = {}

        self._find_collections()

    def get(self, full_id: AnthologyID) -> Optional[Collection | Volume | Paper]:
        """Access collections, volumes, and papers, depending on the provided ID.

        Parameters:
            full_id: An Anthology ID that refers to a collection, volume, or paper.

        Returns:
            The object corresponding to the given ID.
        """
        (collection_id, volume_id, paper_id) = parse_id(full_id)
        if volume_id is None:
            return self.collections.get(collection_id)
        volume = self.get_volume((collection_id, volume_id, None))
        if paper_id is None or volume is None:
            return volume
        return volume.get(paper_id)

    def get_volume(self, full_id: AnthologyID) -> Optional[Volume]:
        """Access a volume by its ID or the ID of a contained paper.

        Parameters:
            full_id: An Anthology ID that refers to a volume or paper.

        Returns:
            The volume associated with the given ID.
        """
        (collection_id, volume_id, _) = parse_id(full_id)
        collection = self.collections[collection_id]
        # Load XML file, if necessary
        if not collection.is_data_loaded:
            collection.load()
        return collection.get(volume_id)  # type: ignore

    def _find_collections(self) -> None:
        """Finds all XML data files and indexes them by their collection ID.

        This function is called automatically when the CollectionIndex is initialized.

        Note:
            Currently assumes that XML files are **always** named according to the collection ID they
            contain; i.e., a file named "L16.xml" *must* contain the collection with ID "L16".
        """
        for xmlpath in self._anthology.datadir.glob("xml/*.xml"):
            # Assumes that XML files are **always** named as their collection
            # IDs.  --- Alternatively, could peek at the first two lines of the
            # file to parse only the <collection id="..."> tag?
            collection_id = xmlpath.name[:-4]
            self.collections[collection_id] = Collection(collection_id, xmlpath)
