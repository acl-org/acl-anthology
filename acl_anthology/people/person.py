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

from attrs import define, Factory
from . import Name


@define
class Person:
    """A person.

    Attributes:
        id (str): A unique ID for this person.
        names (list[Name]): A list of names under which this person has published.
    """

    id: str
    names: list[Name] = Factory(list)

    @property
    def canonical_name(self) -> Name:
        """The canonical name for this person."""
        try:
            # By convention, the first entry of `self.names` is treated as the
            # canonical entry
            return self.names[0]
        except KeyError:
            raise ValueError(f"No names defined for person '{self.id}'")

    def has_name(self, name: Name) -> bool:
        """Returns True if the given name can refer to this person."""
        # TODO: not sure yet how this needs to work
        # return any(n.match(name) for n in self.names)
        raise NotImplementedError()

    def set_canonical_name(self, name: Name) -> None:
        """Set the canonical name for this person."""
        raise NotImplementedError()

    def add_name(self, name: Name) -> None:
        """Adds the given name to this person."""
        self.names.append(name)
