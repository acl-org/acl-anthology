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
from typing import overload, Iterator, Optional

from .utils.ids import AnthologyID, parse_id
from .collections import CollectionIndex, Collection, Volume, Paper
from .people import PersonIndex, Person, NameSpecification


NameSpecificationOrIter = NameSpecification | Iterator[NameSpecification]
PersonOrList = Person | list[Person]


class Anthology:
    """An instance of the ACL Anthology data.

    Attributes:
        datadir (PathLike[str]): The path to the data folder.
    """

    def __init__(self, datadir: PathLike[str]) -> None:
        if not Path(datadir).is_dir():
            raise FileNotFoundError(f"Not a directory: {datadir}")

        self.datadir = Path(datadir)

        self.collections = CollectionIndex(self)
        """The [CollectionIndex][acl_anthology.collections.CollectionIndex] for accessing collections, volumes, and papers."""

        self.people = PersonIndex(self)
        """The [PersonIndex][acl_anthology.people.PersonIndex] for accessing authors and editors."""

    def volumes(self, collection_id: Optional[str] = None) -> Iterator[Volume]:
        """Returns an iterator over all volumes.

        Parameters:
            collection_id: If provided, only volumes belonging to the given collection ID will be included.
        """
        if collection_id is not None:
            if (collection := self.collections.get(collection_id)) is None:
                return
            yield from iter(collection)
        else:
            for collection in self.collections:
                yield from iter(collection)

    def papers(self, full_id: Optional[AnthologyID] = None) -> Iterator[Paper]:
        """Returns an iterator over all papers.

        Parameters:
            full_id: If provided, only papers matching the given ID will be included.
        """
        if full_id is not None:
            if (element := self.get(full_id)) is None:
                return
            elif isinstance(element, Paper):
                yield from iter([element])
            elif isinstance(element, Volume):
                yield from iter(element)
            else:  # Collection
                for volume in element:
                    yield from iter(volume)
        else:
            for collection in self.collections:
                for volume in collection:
                    yield from iter(volume)

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

    @overload
    def resolve(self, name_spec: NameSpecification) -> Person:
        ...

    @overload
    def resolve(self, name_spec: Iterator[NameSpecification]) -> list[Person]:
        ...

    def resolve(self, name_spec: NameSpecificationOrIter) -> PersonOrList:
        """Resolve a name specification (e.g. as attached to papers) to a natural person.

        Parameters:
            name_spec: A name specification, or an iterator over name specifications.

        Returns:
            A single Person object if a single name specification was given, or a list of Person objects with equal length to the input iterable otherwise.

        Examples:
            >>> paper = anthology.get("C92-1025")
            >>> anthology.resolve(paper.authors)
            [Person(id='lauri-karttunen', ...), Person(id='ronald-kaplan', ...), Person(id='annie-zaenen', ...)]
        """
        if isinstance(name_spec, NameSpecification):
            return self.people.get_by_namespec(name_spec)
        return [self.people.get_by_namespec(ns) for ns in name_spec]
