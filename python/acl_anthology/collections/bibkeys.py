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

from __future__ import annotations

from attrs import define, field
from rich.progress import track
from typing import TYPE_CHECKING

from ..containers import SlottedDict
from .paper import Paper

if TYPE_CHECKING:
    from .index import CollectionIndex


@define
class BibkeyIndex(SlottedDict[Paper]):
    """Index object which collects citation keys for all papers.

    Provides dictionary-like functionality mapping bibkeys to [Paper][acl_anthology.collections.collection.Paper] objects in the Anthology.

    Attributes:
        parent: The parent CollectionIndex instance to which this index belongs.
        is_data_loaded: A flag indicating whether the XML directory has already been indexed.
    """

    parent: CollectionIndex = field(repr=False, eq=False)
    is_data_loaded: bool = field(init=False, repr=True, default=False)

    def load(self) -> None:
        """Loads an index of bibkeys."""
        # This function exists so we can later add the option to read the index
        # from a cache if it doesn't need re-building.
        if self.is_data_loaded:
            return
        self.build()
        self.is_data_loaded = True

    def reset(self) -> None:
        """Resets the index."""
        self.data = {}
        self.is_data_loaded = False

    def build(self, show_progress: bool = False) -> None:
        """Load the entire Anthology data and build an index of bibkeys.

        Raises:
            ValueError: If a non-unique bibkey is encountered.
        """
        self.reset()
        # Go through every single paper
        iterator = track(
            self.parent.values(),
            total=len(self.parent),
            disable=(not show_progress),
            description="Building bibkey index...",
        )
        for collection in iterator:
            for paper in collection.papers():
                if paper.bibkey in self.data:
                    raise ValueError(
                        f"Paper {paper.full_id} has bibkey {paper.bibkey}, which is already assigned to paper {self.data[paper.bibkey].full_id}"
                    )
                self.data[paper.bibkey] = paper
        self.is_data_loaded = True
