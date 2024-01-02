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

from __future__ import annotations

from attrs import define, field
from typing import TYPE_CHECKING

from ..containers import SlottedDict
from .collection import Collection

if TYPE_CHECKING:
    from ..anthology import Anthology


@define
class CollectionIndex(SlottedDict[Collection]):
    """Index object through which all collections can be accessed.

    Provides dictionary-like functionality mapping collection IDs to [Collection][acl_anthology.collections.collection.Collection] objects in the Anthology.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        is_data_loaded: A flag indicating whether the XML directory has already been indexed.
    """

    parent: Anthology = field(repr=False, eq=False)
    is_data_loaded: bool = field(init=False, repr=False, default=False)

    def load(self) -> None:
        """Finds all XML data files and indexes them by their collection ID.

        Note:
            Currently assumes that XML files are **always** named according to the collection ID they
            contain; i.e., a file named "L16.xml" *must* contain the collection with ID "L16".
        """
        for xmlpath in self.parent.datadir.glob("xml/*.xml"):
            # Assumes that XML files are **always** named as their collection
            # IDs.  --- Alternatively, could peek at the first two lines of the
            # file to parse only the <collection id="..."> tag?
            collection_id = xmlpath.name[:-4]
            self.data[collection_id] = Collection(collection_id, self, xmlpath)
        self.is_data_loaded = True
