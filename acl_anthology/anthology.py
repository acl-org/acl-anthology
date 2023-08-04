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

from os import PathLike
from pathlib import Path
from typing import Optional

from .utils.ids import AnthologyID, parse_id
from .collections import CollectionIndex, Collection, Volume, Paper
from .people import PersonIndex


class Anthology:
    """TODO"""

    def __init__(self, datadir: str | PathLike[str]) -> None:
        if not Path(datadir).is_dir():
            raise ValueError(f"Not a directory: {datadir}")  # TODO exception type

        self._datadir = Path(datadir)
        self.collections = CollectionIndex(self)
        self.people = PersonIndex(self)

    @property
    def datadir(self) -> Path:
        return self._datadir

    def get(self, full_id: AnthologyID) -> Optional[Collection | Volume | Paper]:
        """Access collections, volumes, and papers, depending on the provided ID.

        Parameters:
            full_id: An Anthology ID that refers to a collection, volume, or paper.

        Returns:
            The object corresponding to the given ID.
        """
        (collection_id, volume_id, paper_id) = parse_id(full_id)
        collection = self.collections.get(collection_id)
        if collection is None or volume_id is None:
            return collection
        volume = collection.get(volume_id)
        if volume is None or paper_id is None:
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
        collection = self.collections.get(collection_id)
        if collection is None or volume_id is None:
            return None
        return collection.get(volume_id)

    def get_paper(self, full_id: AnthologyID) -> Optional[Paper]:
        """Access a paper by its ID.

        Parameters:
            full_id: An Anthology ID that refers to a paper.

        Returns:
            The volume associated with the given ID.
        """
        (collection_id, volume_id, paper_id) = parse_id(full_id)
        volume = self.get_volume((collection_id, volume_id, None))
        if volume is None or paper_id is None:
            return None
        return volume.get(paper_id)
