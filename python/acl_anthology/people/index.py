# Copyright 2023-2026 Marcel Bollmann <marcel@bollmann.me>
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
from collections import Counter, defaultdict
import itertools as it
from pathlib import Path
from rich.progress import track
from scipy.cluster.hierarchy import DisjointSet  # type: ignore
import sys
from typing import cast, Any, Iterable, Optional, TYPE_CHECKING
import warnings
import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:  # pragma: no cover
    from yaml import Loader, Dumper  # type: ignore

from ..config import primary_console
from ..containers import SlottedDict
from ..exceptions import (
    AnthologyException,
    AnthologyInvalidIDError,
    NameSpecResolutionError,
    NameSpecResolutionWarning,
    PersonDefinitionError,
)
from ..utils.ids import AnthologyIDTuple, is_verified_person_id
from ..utils.logging import get_logger
from . import Person, Name, NameLink, NameSpecification
from .name import _YAMLName

if TYPE_CHECKING:
    from _typeshed import StrPath
    from ..anthology import Anthology
    from ..collections import Paper, Volume, Collection

log = get_logger()
PEOPLE_INDEX_FILE = "yaml/people.yaml"


UNVERIFIED_PID_FORMAT = "{pid}/unverified"
"""Format string for unverified person IDs."""
# Note: Changing this will require changes in Hugo templates etc. as well!


@define
class PersonIndex(SlottedDict[Person]):
    """Index object through which all persons (authors/editors) can be accessed.

    Provides dictionary-like functionality mapping person IDs to [Person][acl_anthology.people.person.Person] objects.

    Info:
        All information about persons is currently derived from [name specifications][acl_anthology.people.name.NameSpecification] on volumes and papers, and not stored explicitly. This means:

        1. Loading this index requires parsing the entire Anthology data.
        2. Nothing in this index should be modified to make changes to Anthology data; change the information on papers instead.

        See the [guide on accessing author/editor information](../guide/accessing-authors.md) for more information.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        path: The path to `people.yaml`.
        by_orcid: A mapping of ORCIDs (as strings) to person IDs.
        by_name: A mapping of [Name][acl_anthology.people.name.Name] instances to lists of person IDs.
        slugs_to_verified_ids: A mapping of strings (representing slugified names) to lists of person IDs.
        similar: A [disjoint-set structure][scipy.cluster.hierarchy.DisjointSet] of persons with similar names.
        is_data_loaded: A flag indicating whether the index has been constructed.
    """

    parent: Anthology = field(repr=False, eq=False)
    path: Path = field(init=False)
    _by_orcid: dict[str, str] = field(init=False, repr=False, default={})
    _by_name: dict[Name, list[str]] = field(
        init=False, repr=False, factory=lambda: defaultdict(list)
    )
    _slugs_to_verified_ids: dict[str, set[str]] = field(
        init=False, repr=False, factory=lambda: defaultdict(list)
    )
    _similar: DisjointSet = field(init=False, repr=False, factory=DisjointSet)
    is_data_loaded: bool = field(init=False, repr=True, default=False)

    @path.default
    def _path(self) -> Path:
        return self.parent.datadir / Path(PEOPLE_INDEX_FILE)

    @property
    def by_orcid(self) -> dict[str, str]:
        if not self.is_data_loaded:
            self.load()
        return self._by_orcid

    @property
    def by_name(self) -> dict[Name, list[str]]:
        if not self.is_data_loaded:
            self.load()
        return self._by_name

    @property
    def similar(self) -> DisjointSet:
        if not self.is_data_loaded:
            self.load()
        return self._similar

    @property
    def slugs_to_verified_ids(self) -> dict[str, set[str]]:
        if not self.is_data_loaded:
            self.load()
        return self._slugs_to_verified_ids

    def get_by_name(self, name: Name) -> list[Person]:
        """Access persons by their name.

        Parameters:
            name: A personal name.

        Returns:
            A list of all persons with that name; can be empty.
        """
        if not self.is_data_loaded:
            self.load()
        return [self.data[pid] for pid in self._by_name[name]]

    def get_by_namespec(self, name_spec: NameSpecification) -> Person:
        """Access persons by their name specification.

        See [resolve_namespec()][acl_anthology.people.index.PersonIndex.resolve_namespec] for exceptions that can be raised by this function.

        Parameters:
            name_spec: A name specification.

        Returns:
            The person associated with this name specification.
        """
        if not self.is_data_loaded:
            self.load()
        return self.resolve_namespec(name_spec)

    def get_by_orcid(self, orcid: str) -> Person | None:
        """Access persons by their ORCID.

        Parameters:
            orcid: A string representing an ORCID.

        Returns:
            The person with that ORCID, if it exists, otherwise None.
        """
        if not self.is_data_loaded:
            self.load()
        if orcid in self._by_orcid:
            return self.data[self._by_orcid[orcid]]
        return None

    def find_coauthors(
        self, person: str | Person, include_volumes: bool = True
    ) -> list[Person]:
        """Find all persons who co-authored or co-edited items with the given person.

        Parameters:
            person: A person ID _or_ Person instance.
            include_volumes: If set to False, will not consider co-editorship on volumes, unless they have frontmatter.

        Returns:
            A list of all persons who are co-authors; can be empty.
        """
        coauthors = self.find_coauthors_counter(person, include_volumes=include_volumes)
        return [self.data[pid] for pid in coauthors]

    def find_coauthors_counter(
        self, person: str | Person, include_volumes: bool = True
    ) -> Counter[str]:
        """Find the count of co-authored or co-edited items per person.

        Parameters:
            person: A person ID _or_ Person instance.
            include_volumes: If set to False, will not consider co-editorship on volumes, unless they have frontmatter.

        Returns:
            A Counter mapping **IDs** of other persons Y to the number of papers this person has co-authored with Y.
        """
        if not self.is_data_loaded:
            self.load()
        if isinstance(person, str):
            person = self.data[person]
        coauthors: Counter[str] = Counter()
        for item_id in person.item_ids:
            item = cast("Volume | Paper", self.parent.get(item_id))
            if (
                not include_volumes
                and item.full_id_tuple[-1] is None  # item is a Volume
                and not cast("Volume", item).has_frontmatter
            ):
                continue
            coauthors.update(self.resolve_namespec(ns).id for ns in item.editors)
            if hasattr(item, "authors"):
                coauthors.update(self.resolve_namespec(ns).id for ns in item.authors)
        del coauthors[person.id]
        return coauthors

    def load(self) -> None:
        """Loads or builds the index."""
        # This function exists so we can later add the option to read the index
        # from a cache if it doesn't need re-building.
        if self.is_data_loaded:  # pragma: no cover
            return
        self.build(show_progress=self.parent.verbose)

    def reset(self) -> None:
        """Resets the index."""
        self.data = {}
        self._by_orcid = {}
        self._by_name = defaultdict(list)
        self._slugs_to_verified_ids = defaultdict(set)
        self._similar = DisjointSet()
        self.is_data_loaded = False

    def build(self, show_progress: bool = False) -> None:
        """Load the entire Anthology data and build an index of persons.

        Important:
            Exceptions raised during the index creation are sent to the logger, and only a generic exception is raised at the end.
        """
        self.reset()
        self._load_people_index()
        # Go through every single volume/paper and add authors/editors
        if not show_progress:
            iterator: Iterable[Collection] = self.parent.collections.values()
        else:
            iterator = track(
                self.parent.collections.values(),
                total=len(self.parent.collections),
                description="Building person index...",
                console=primary_console,
            )
        raised_exception = False
        for collection in iterator:
            for volume in collection.volumes():
                context: Paper | Volume = volume
                try:
                    self._add_to_index(
                        volume.editors, volume.full_id_tuple, during_build=True
                    )
                    for paper in volume.papers():
                        context = paper
                        name_specs = (
                            # Associate explicitly given authors/editors with the paper
                            it.chain(paper.authors, paper.editors)
                            # For frontmatter, also associate the volume editors with it
                            if not paper.is_frontmatter
                            else paper.get_editors()
                        )
                        self._add_to_index(
                            name_specs, paper.full_id_tuple, during_build=True
                        )
                except Exception as exc:  # pragma: no cover
                    note = f"Raised in {context.__class__.__name__} {context.full_id}"
                    # If this is merged into a single if-statement (with "or"),
                    # the type checker complains ¯\_(ツ)_/¯
                    if isinstance(exc, AnthologyException):
                        exc.add_note(note)
                    elif sys.version_info >= (3, 11):
                        exc.add_note(note)
                    log.exception(exc)
                    raised_exception = True
        if raised_exception:
            raise Exception(
                "An exception was raised while building PersonIndex; check the logger for details."
            )  # pragma: no cover
        self.is_data_loaded = True

    def _load_people_index(self) -> None:
        """Load and parse the `people.yaml` file.

        Raises:
            AnthologyInvalidIDError: If `people.yaml` contains a malformed person ID; or if a person is listed without any names.
        """
        with open(self.path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=Loader)

        for pid, entry in data.items():
            if not is_verified_person_id(pid):
                raise AnthologyInvalidIDError(
                    pid, f"Invalid person ID in people.yaml: {pid}"
                )  # pragma: no cover
            self.add_person(
                Person(
                    id=pid,
                    parent=self.parent,
                    names=[Name.from_dict(n) for n in entry.pop("names")],
                    orcid=entry.pop("orcid", None),
                    comment=entry.pop("comment", None),
                    degree=entry.pop("degree", None),
                    similar_ids=entry.pop("similar", []),
                    disable_name_matching=entry.pop("disable_name_matching", False),
                    is_explicit=True,
                )
            )

            # Check for unprocessed keys to catch errors
            if entry:
                log.warning(
                    f"people.yaml: entry '{pid}' has unknown keys: {entry.keys()}"
                )  # pragma: no cover

    def add_person(self, person: Person) -> None:
        """Add a new person to the index.

        Parameters:
            person: The person to add, which should not exist in the index yet.

        Raises:
            AnthologyInvalidIDError: If a person with the same ID or ORCID already exists in the index.
        """
        if (pid := person.id) in self.data:
            raise AnthologyInvalidIDError(
                pid, f"A Person with ID '{pid}' already exists in the index"
            )
        self.data[pid] = person
        self._similar.add(pid)
        if person.orcid is not None:
            if person.orcid in self._by_orcid:
                raise ValueError(
                    f"ORCID '{person.orcid}' already assigned to person '{self._by_orcid[person.orcid]}'"
                )
            self._by_orcid[person.orcid] = pid
        for name in person.names:
            self._add_name(pid, name, during_build=True)
        for similar_id in person.similar_ids:
            self._similar.add(similar_id)  # might not have been added yet
            self._similar.merge(pid, similar_id)

    def create(
        self,
        id: str,
        names: list[Name],
        **kwargs: Any,
    ) -> Person:
        """Create a new explicit person and add it to the index.

        Parameters:
            id: The ID of the new person.
            names: A list of names for the new person; must contain at least one.
            **kwargs: Any valid list or optional attribute of [Person][acl_anthology.people.person.Person].

        Returns:
            The created [Person][acl_anthology.people.person.Person] object.

        Raises:
            AnthologyInvalidIDError: If a person with the given ID already exists, or the ID is not a well-formed verified-person ID.
            ValueError: If the list of names is empty.
        """
        if not self.is_data_loaded:
            self.load()
        if id in self.data:
            raise AnthologyInvalidIDError(
                id, f"A Person with ID '{id}' already exists in the index"
            )
        if not is_verified_person_id(id):
            raise AnthologyInvalidIDError(id, f"Not a valid verified-person ID: {id}")
        if not names:
            raise ValueError("List of names cannot be empty")

        kwargs["parent"] = self.parent
        kwargs["is_explicit"] = True

        person = Person(id=id, names=names, **kwargs)
        self.add_person(person)
        return person

    def _update_id(self, old_id: str, new_id: str) -> None:
        """Update a person ID in the index.

        Will change all indices to remove the old ID and replace it with the new one.  Will be called automatically from Person; do not call manually.

        Parameters:
            old_id: A person ID that already exists in the index.
            new_id: The new person ID it should be changed to, which mustn't exist in the index.

        Raises:
            KeyError: If the new ID already exists.
        """
        if not self.is_data_loaded:
            return
        if new_id in self.data:
            raise KeyError(
                f"Tried to add ID '{new_id}' to PersonIndex which already exists"
            )
        person = self.data.pop(old_id)
        self.data[new_id] = person
        # Note: cannot remove from DisjointSet
        self._similar.add(new_id)
        self._similar.merge(old_id, new_id)
        if person.orcid is not None:
            self._by_orcid[person.orcid] = new_id
        for name in person.names:
            self._remove_name(old_id, name)
            self._add_name(new_id, name)

    def _update_orcid(self, pid: str, old: Optional[str], new: Optional[str]) -> None:
        """Update a person's ORCID in the index.

        Will be called automatically from Person; do not call manually.
        """
        if not self.is_data_loaded:
            return
        if old is not None and old in self._by_orcid:
            del self._by_orcid[old]
        if new is not None:
            self._by_orcid[new] = pid

    def _add_name(self, pid: str, name: Name, during_build: bool = False) -> None:
        """Add a name for a person to the index.

        Will be called automatically from Person; do not call manually.
        """
        if not (during_build or self.is_data_loaded):
            return
        name_list = self._by_name[name]
        if pid in name_list:
            return
        if name_list:
            # Merging is transitive, so it's enough to merge with the last one
            self._similar.merge(pid, name_list[-1])
        name_list.append(pid)
        if is_verified_person_id(pid):
            verified_id_set = self._slugs_to_verified_ids[name.slugify()]
            if pid not in verified_id_set:
                for other_id in verified_id_set:
                    # Merging is transitive, so it's enough to merge with the last one
                    self._similar.merge(pid, other_id)
                    break
                verified_id_set.add(pid)

    def _remove_name(self, pid: str, name: Name) -> None:
        """Remove a name for a person from the index.

        Will be called automatically from Person; do not call manually.
        """
        if not self.is_data_loaded:
            return
        try:
            self._by_name[name].remove(pid)
            if is_verified_person_id(pid):
                self._slugs_to_verified_ids[name.slugify()].remove(pid)
        except KeyError:
            pass

    def ingest_namespec(self, name_spec: NameSpecification) -> NameSpecification:
        """Update a name specification for ingestion, potentially filling in the ID field.

        If the name specification contains an ORCID but doesn't have an ID yet, this will find the person with this ORCID and fill in their ID; if it doesn't exist yet, it will create a new person with a "verified" ID and fill in the new, generated ID.  The supplied name specification will be modified in-place, but also returned.

        Parameters:
            name_spec: The name specification on the paper, volume, etc.

        Returns:
            The name specification as it should be used for the new ingestion material.
        """
        if name_spec.orcid is None or name_spec.id is not None:
            return name_spec

        if (person := self.get_by_orcid(name_spec.orcid)) is not None:
            name_spec.id = person.id
            # Make sure the name used here is listed for this person
            person.add_name(name_spec.name)
        else:
            # Need to create a new person; generate name slug for the ID
            pid = name_spec.name.slugify()
            if pid in self.data:
                # ID is already in use; add last four digits of ORCID to disambiguate
                pid = f"{pid}-{name_spec.orcid[-4:].lower()}"

            self.add_person(
                Person(
                    id=pid,
                    parent=self.parent,
                    names=[name_spec.name] + name_spec.variants,
                    orcid=name_spec.orcid,
                    is_explicit=True,
                )
            )
            name_spec.id = pid

        return name_spec

    def resolve_namespec(
        self, name_spec: NameSpecification, allow_creation: bool = False
    ) -> Person:
        """Resolve a name specification to a person, potentially creating a new unverified person instance.

        Parameters:
            name_spec: The name specification on the paper, volume, etc.
            allow_creation: If True, will instantiate a new Person object with an unverified ID if no person matching `name_spec` exists.  Defaults to False.

        Returns:
            The person represented by `name_spec`.  If `name_spec.id` is set, this will determine the person to resolve to.  Otherwise, the slugified name will be used to find a matching person; an explicitly-defined (verified) person can be returned if exactly one such person exists and does not have `disable_name_matching` set.  In all other cases, it will resolve to an unverified person.

        Raises:
            NameSpecResolutionError: If `name_spec` cannot be resolved to a Person and `allow_creation` is False.
            PersonDefinitionError: If `name_spec.id` is set, but either the ID or the name used with the ID has not been defined in `people.yaml`. (Inherits from NameSpecResolutionError)
        """
        name = name_spec.name
        if (pid := name_spec.id) is not None:
            # Explicit ID given – should be explicitly defined in people.yaml
            if pid not in self.data or not (person := self.data[pid]).is_explicit:
                raise PersonDefinitionError(
                    name_spec, f"ID '{pid}' wasn't defined in people.yaml"
                )
            if not person.has_name(name):
                raise PersonDefinitionError(
                    name_spec,
                    f"ID '{pid}' was used with name '{name}' that wasn't defined in people.yaml",
                )
            if name_spec.orcid is not None and name_spec.orcid != person.orcid:
                raise PersonDefinitionError(
                    name_spec,
                    f"ID '{pid}' was used with ORCID '{name_spec.orcid}', but people.yaml has '{person.orcid}'",
                )
        else:
            # No explicit ID given
            if name_spec.orcid is not None:
                exc1 = NameSpecResolutionError(
                    name_spec,
                    "NameSpecification defines an ORCID without an ID",
                )
                exc1.add_note(
                    "To specify an ORCID on a paper, the person needs to have an entry in `people.yaml` and be used with an explicit ID."
                )
                raise exc1

            # Generate slug for name matching
            slug = name.slugify()

            # Check if the slugified name matches any verified IDs
            matching_ids = list(self._slugs_to_verified_ids.get(slug, []))
            if (
                len(matching_ids) == 1
                and not (person := self.data[matching_ids[0]]).disable_name_matching
            ):
                # Slug unambiguously maps to person and name matching not disabled
                pid = person.id
                if not person.has_name(name):
                    person.add_name(name, inferred=True)
                    self._add_name(pid, name, during_build=True)

            else:
                # Resolve to unverified ID
                pid = UNVERIFIED_PID_FORMAT.format(pid=slug)

                if pid in self.data:
                    # Unverified ID already exists; assume it's the same person
                    person = self.data[pid]
                    if not person.has_name(name):
                        # If the name scores higher than the current canonical
                        # one, we also assume we should set this as the
                        # canonical one
                        if name.score() > person.canonical_name.score():
                            person._set_canonical_name(name, inferred=True)
                        else:
                            person.add_name(name, inferred=True)
                        self._add_name(pid, name, during_build=True)
                elif allow_creation:
                    # Unverified ID doesn't exist yet; create it
                    person = Person(
                        id=pid, parent=self.parent, names=[(name, NameLink.INFERRED)]
                    )
                    self.add_person(person)
                else:
                    raise NameSpecResolutionError(
                        name_spec,
                        f"NameSpecification resolved to ID '{pid}' which doesn't exist",
                    )

        # Make sure that name variants specified here are registered
        for name in name_spec.variants:
            if not person.has_name(name):
                person.add_name(name, inferred=True)
            if name not in self._by_name:
                self._by_name[name].append(pid)
        return person

    def _add_to_index(
        self,
        namespecs: Iterable[NameSpecification],
        item_id: AnthologyIDTuple,
        during_build: bool = False,
    ) -> None:
        """Add persons to the index.

        This function should not be called manually.  It exists for internal use when registering new volumes or papers.  It encapsulates the resolution of all namespecs on an item, both to reduce repetition and to enable checks, e.g. that an item does not have two namespecs that resolve to the same person (which would indicate a logical error that we can't easily catch elsewhere).

        Arguments:
            namespecs: The NameSpecifications to register.
            item_id: The item to register for the NameSpecifications.
            during_build: If True, we are calling this during build and should not expect the index to be fully loaded yet.
        """
        if not (during_build or self.is_data_loaded):
            return

        seen_ids = set()
        for namespec in namespecs:
            person = self.resolve_namespec(namespec, allow_creation=True)
            person.item_ids.append(item_id)
            if person.id in seen_ids:
                message = f"More than one NameSpecification resolves to '{person.id}' on the same item ({item_id})"
                if person.is_explicit:
                    raise NameSpecResolutionError(namespec, message)
                else:
                    warnings.warn(NameSpecResolutionWarning(namespec, message))
            seen_ids.add(person.id)

    def save(self, path: Optional[StrPath] = None) -> None:
        """Save the `people.yaml` file.

        Arguments:
            path: The filename to save to. If None, defaults to the parent Anthology's `people.yaml` file.
        """
        if path is None:  # pragma: no cover
            self.parent._warn_if_in_default_path()
            path = self.path

        data = {}
        for person in self.values():
            if not person.is_explicit:
                continue

            attrib: dict[str, Any] = {
                "names": [
                    _YAMLName(name)
                    for (name, link_type) in person._names
                    if link_type == NameLink.EXPLICIT
                ],
                "comment": person.comment,
                "degree": person.degree,
                "disable_name_matching": person.disable_name_matching,
                "orcid": person.orcid,
                "similar": person.similar_ids,
            }
            data[person.id] = {k: v for k, v in attrib.items() if v}

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, Dumper=Dumper)
