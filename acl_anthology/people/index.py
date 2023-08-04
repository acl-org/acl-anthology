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

from typing import TYPE_CHECKING

from . import Person

if TYPE_CHECKING:
    from ..anthology import Anthology


class PersonIndex:
    """Index object through which all persons (authors/editors) can be accessed.

    Attributes:
        parent (Anthology): The parent Anthology instance to which this index belongs.
    """

    def __init__(self, parent: Anthology) -> None:
        self.parent = parent
        self.people: dict[str, Person] = {}
        self.is_built = False

    def build_index(self) -> None:
        """Load the entire Anthology data and build an index of persons."""
        raise NotImplementedError()
