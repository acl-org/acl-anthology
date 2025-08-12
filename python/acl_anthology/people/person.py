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
from typing import Iterator, Optional, TYPE_CHECKING
from ..utils.attrs import auto_validate_types
from ..utils.ids import AnthologyIDTuple, build_id_from_tuple
from . import Name

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..collections import Paper, Volume


@define(field_transformer=auto_validate_types)
class Person:
    """A natural person.

    Info:
        All information about persons is currently derived from [name specifications][acl_anthology.people.name.NameSpecification] on volumes and papers, and not stored explicitly. This means that Person objects **cannot be used to make changes** to Anthology data; change the information on papers instead.

    Attributes:
        id: A unique ID for this person.
        parent: The parent Anthology instance to which this person belongs.
        names: A list of names under which this person has published.
        item_ids: A list of volume and/or paper IDs this person has authored or edited.
        comment: A comment for disambiguation purposes; can be stored in `name_variants.yaml`.
        is_explicit: True if this person has names explicitly defined in `name_variants.yaml`.  Note this does _not_ necessarily mean an explicit ID was defined for the person there.
    """

    id: str = field()
    parent: Anthology = field(repr=False, eq=False)
    names: list[Name] = field(factory=list)
    item_ids: list[AnthologyIDTuple] = field(
        factory=list, repr=lambda x: f"<list of {len(x)} AnthologyIDTuple objects>"
    )
    comment: Optional[str] = field(default=None)
    is_explicit: Optional[bool] = field(default=False)  # TODO: why can this be None?

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Person):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

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

    @canonical_name.setter
    def canonical_name(self, name: Name) -> None:
        self.set_canonical_name(name)

    def add_name(self, name: Name) -> None:
        """Add a name for this person.

        Parameters:
            name: Name that can refer to this person.
        """
        if name not in self.names:
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

    def papers(self) -> Iterator[Paper]:
        """Returns an iterator over all papers associated with this person.

        Note:
            This will return papers where this person is an author, as well as frontmatter of volumes where they are an editor. It will _not_ include all other papers in volumes they have edited.
        """
        for anthology_id in self.item_ids:
            paper_id = anthology_id[-1]
            if paper_id is not None:
                paper = self.parent.get_paper(anthology_id)
                if paper is None:
                    raise ValueError(
                        f"Person {self.id} lists associated paper {build_id_from_tuple(anthology_id)}, which doesn't exist"
                    )
                yield paper

    def volumes(self) -> Iterator[Volume]:
        """Returns an iterator over all volumes this person has edited."""
        for anthology_id in self.item_ids:
            paper_id = anthology_id[-1]
            if paper_id is None:
                volume = self.parent.get_volume(anthology_id)
                if volume is None:
                    raise ValueError(
                        f"Person {self.id} lists associated volume {build_id_from_tuple(anthology_id)}, which doesn't exist"
                    )
                yield volume
