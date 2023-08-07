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

from attrs import define, field, Factory
from typing import Optional
from ..utils.ids import AnthologyID
from . import Name


@define
class Person:
    """A natural person.

    Attributes:
        id: A unique ID for this person.
        names: A list of names under which this person has published.
        item_ids: A set of volume and/or paper IDs this person has authored or edited.
        comment: A comment for disambiguation purposes; can be stored in `name_variants.yaml`.
    """

    id: str
    names: list[Name] = Factory(list)
    item_ids: set[AnthologyID] = Factory(set)
    comment: Optional[str] = field(default=None)

    @property
    def canonical_name(self) -> Name:
        """
        Returns:
            The canonical name for this person.
        """
        try:
            # By convention, the first entry of `self.names` is treated as the
            # canonical entry
            return self.names[0]
        except KeyError:
            raise ValueError(f"No names defined for person '{self.id}'")

    def add_name(self, name: Name) -> None:
        """Add a name for this person.

        Parameters:
            name: Name that can refer to this person.
        """
        self.names.append(name)

    def has_name(self, name: Name) -> bool:
        """
        Parameters:
            name: Name to be checked.

        Returns:
            True if the given name can refer to this person.
        """
        return name in self.names

    def set_canonical_name(self, name: Name) -> None:
        """Set the canonical name for this person.

        Parameters:
            name: Name that should be treated as canonical for this person.
        """
        try:
            self.names.pop(self.names.index(name))
        except ValueError:
            pass
        self.names.insert(0, name)
