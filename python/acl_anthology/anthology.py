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

import gc
import itertools as it
import pkgutil
import sys
import warnings
from lxml.etree import RelaxNG
from os import PathLike
from pathlib import Path
from rich.progress import track
from slugify import slugify
from typing import cast, overload, Iterator, Optional

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from .config import config, dirs
from .exceptions import SchemaMismatchWarning
from .utils import git
from .utils.ids import AnthologyID, parse_id
from .collections import CollectionIndex, Collection, Volume, Paper, Event, EventIndex
from .people import PersonIndex, Person, Name, NameSpecification, ConvertableIntoName
from .sigs import SIGIndex
from .venues import VenueIndex


NameSpecificationOrIter = NameSpecification | Iterator[NameSpecification]
PersonOrList = Person | list[Person]


class Anthology:
    """An instance of the ACL Anthology data.

    Attributes:
        datadir (PathLike[str]): The path to the data folder.
        verbose (bool): If False, will not show progress bars during longer operations.
    """

    def __init__(self, datadir: PathLike[str], verbose: bool = True) -> None:
        if not Path(datadir).is_dir():
            raise FileNotFoundError(f"Not a directory: {datadir}")

        self.datadir = Path(datadir)
        self.verbose = verbose
        self._check_schema_compatibility()
        self._relaxng: Optional[RelaxNG] = None

        self.collections = CollectionIndex(self)
        """The [CollectionIndex][acl_anthology.collections.CollectionIndex] for accessing collections, volumes, and papers."""

        self.events = EventIndex(self, verbose)
        """The [EventIndex][acl_anthology.collections.EventIndex] for accessing events."""

        self.people = PersonIndex(self, verbose)
        """The [PersonIndex][acl_anthology.people.PersonIndex] for accessing authors and editors."""

        self.sigs = SIGIndex(self)
        """The [SIGIndex][acl_anthology.sigs.SIGIndex] for accessing SIGs."""

        self.venues = VenueIndex(self)
        """The [VenueIndex][acl_anthology.venues.VenueIndex] for accessing venues."""

    def __repr__(self) -> str:
        return f"Anthology(datadir={repr(self.datadir)}, verbose={self.verbose})"

    def _check_schema_compatibility(self) -> None:
        """
        Checks if the XML schema in the data directory is identical to
        the one in the package directory, and emits a warning if it
        is not."""
        expected_schema = pkgutil.get_data("acl_anthology", "data/schema.rnc")
        with open(self.datadir / "xml" / "schema.rnc", "rb") as f:
            datadir_schema = f.read()
        if datadir_schema != expected_schema:
            warnings.warn(SchemaMismatchWarning())

    @classmethod
    def from_repo(
        cls,
        repo_url: str = "https://github.com/acl-org/acl-anthology.git",
        path: Optional[PathLike[str]] = None,
        verbose: bool = True,
    ) -> Self:
        """Instantiates the Anthology from a Git repo.

        Arguments:
            repo_url: The URL of a Git repo with Anthology data.  If not given, defaults to the official ACL Anthology repo.
            path: The local path for the repo data.  If not given, automatically determines a path within the user's data directory.
            verbose: If False, will not show progress bars during longer operations.
        """
        if path is None:
            path = (
                dirs.user_data_path
                / "git"
                / slugify(repo_url).replace("https-github-com-", "")
            )
        else:
            path = Path(path)
        git.clone_or_pull_from_repo(repo_url, path, verbose)
        return cls(datadir=path / "data", verbose=verbose)

    def load_all(self) -> Self:
        """Load all Anthology data files.

        Calling this function is **not strictly necessary.** If you
        access Anthology data through object methods or
        [SlottedDict][acl_anthology.containers.SlottedDict]
        functionality, data will be loaded on-the-fly as required.
        However, if you know that your program will load all data files
        (particularly the XML files) eventually, for example by
        iterating over all volumes/papers, loading everything at once
        with this function can result in a considerable speed-up.
        """
        was_gc_enabled = False
        if config["disable_gc"]:
            was_gc_enabled = gc.isenabled()
            gc.disable()
        try:
            iterator = track(
                it.chain(
                    self.collections.values(),
                    (self.people, self.events, self.sigs, self.venues),
                ),
                total=len(self.collections) + 4,
                disable=(not self.verbose),
                description="Loading Anthology data...",
            )
            if self.verbose:
                self.events.verbose = False
                self.people.verbose = False
            for elem in iterator:
                elem.load()  # type: ignore
            if self.verbose:
                self.events.verbose = True
                self.people.verbose = True
        finally:
            if was_gc_enabled:
                gc.enable()
        return self

    @property
    def relaxng(self) -> RelaxNG:
        """The RelaxNG schema for the Anthology's XML data files."""
        if self._relaxng is None:
            schema = cast(bytes, pkgutil.get_data("acl_anthology", "data/schema.rnc"))
            self._relaxng = RelaxNG.from_rnc_string(schema.decode("utf-8"))
        return self._relaxng

    def volumes(self, collection_id: Optional[str] = None) -> Iterator[Volume]:
        """Returns an iterator over all volumes.

        Parameters:
            collection_id: If provided, only volumes belonging to the given collection ID will be included.
        """
        if collection_id is not None:
            if (collection := self.collections.get(collection_id)) is None:
                return
            yield from collection.volumes()
        else:
            for collection in self.collections.values():
                yield from collection.volumes()

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
                yield from element.papers()
            else:  # Collection
                for volume in element.volumes():
                    yield from volume.papers()
        else:
            for collection in self.collections.values():
                for volume in collection.volumes():
                    yield from volume.papers()

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

    def get_event(self, event_id: str) -> Optional[Event]:
        """Access an event by its ID.

        Parameters:
            event_id: An ID that refers to an event, e.g. "acl-2022".

        Returns:
            The event associated with the given ID.
        """
        return self.events.get(event_id)

    def get_person(self, person_id: str) -> Optional[Person]:
        """Access a person by their ID.

        Parameters:
            person_id: An ID that refers to a person.

        Returns:
            The person associated with the given ID.
        """
        return self.people.get(person_id)

    def find_people(self, name_def: ConvertableIntoName) -> list[Person]:
        """Find people by name.

        Parameters:
            name_def: Anything that can be resolved to a name; see below for examples.

        Returns:
            A list of [`Person`][acl_anthology.people.person.Person] objects with the given name.

        Examples:
            >>> anthology.find_people("Doe, Jane")
            >>> anthology.find_people(("Jane", "Doe"))       # same as above
            >>> anthology.find_people({"first": "Jane",
                                         "last": "Doe"})      # same as above
            >>> anthology.find_people(Name("Jane", "Doe"))   # same as above
        """
        name = Name.from_(name_def)
        return self.people.get_by_name(name)

    @overload
    def resolve(self, name_spec: NameSpecification) -> Person:  # pragma: no cover
        ...

    @overload
    def resolve(
        self, name_spec: Iterator[NameSpecification]
    ) -> list[Person]:  # pragma: no cover
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
