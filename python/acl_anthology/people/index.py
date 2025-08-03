# Copyright 2023-2025 Marcel Bollmann <marcel@bollmann.me>
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

from attrs import define, field, asdict
from collections.abc import Iterable
from collections import Counter, defaultdict
import itertools as it
from pathlib import Path
from rich.progress import track
from scipy.cluster.hierarchy import DisjointSet  # type: ignore
import sys
from typing import cast, Any, TYPE_CHECKING
import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:  # pragma: no cover
    from yaml import Loader, Dumper  # type: ignore

from ..containers import SlottedDict
from ..exceptions import AnthologyException, NameSpecResolutionError, PersonUndefinedError
from ..utils.ids import AnthologyIDTuple, is_verified_person_id
from ..utils.logging import get_logger
from . import Person, Name, NameSpecification

if TYPE_CHECKING:
    from _typeshed import StrPath
    from ..anthology import Anthology
    from ..collections import Paper, Volume

log = get_logger()
PEOPLE_INDEX_FILE = "yaml/people.yaml"


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
        verbose: If False, will not show progress bar when building the index from scratch.
        name_to_ids: A mapping of [Name][acl_anthology.people.name.Name] instances to person IDs.
        slugs_to_verified_ids: A mapping of strings (representing slugified names) to person IDs.
        similar: A [disjoint-set structure][scipy.cluster.hierarchy.DisjointSet] of persons with similar names.
        is_data_loaded: A flag indicating whether the index has been constructed.
    """

    parent: Anthology = field(repr=False, eq=False)
    verbose: bool = field(default=True)
    name_to_ids: dict[Name, list[str]] = field(
        init=False, repr=False, factory=lambda: defaultdict(list)
    )
    slugs_to_verified_ids: dict[str, list[str]] = field(
        init=False, repr=False, factory=lambda: defaultdict(list)
    )
    similar: DisjointSet = field(init=False, repr=False, factory=DisjointSet)
    is_data_loaded: bool = field(init=False, repr=True, default=False)

    def get_by_name(self, name: Name) -> list[Person]:
        """Access persons by their name.

        Parameters:
            name: A personal name.

        Returns:
            A list of all persons with that name; can be empty.
        """
        if not self.is_data_loaded:
            self.load()
        return [self.data[pid] for pid in self.name_to_ids[name]]

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
        if self.is_data_loaded:
            return
        self.build(show_progress=self.verbose)

    def reset(self) -> None:
        """Resets the index."""
        self.data = {}
        self.name_to_ids = defaultdict(list)
        self.slugs_to_verified_ids = defaultdict(list)
        self.similar = DisjointSet()
        self.is_data_loaded = False

    def build(self, show_progress: bool = False) -> None:
        """Load the entire Anthology data and build an index of persons.

        Important:
            Exceptions raised during the index creation are sent to the logger, and only a generic exception is raised at the end.
        """
        self.reset()
        self._load_people_index()
        # Go through every single volume/paper and add authors/editors
        iterator = track(
            self.parent.collections.values(),
            total=len(self.parent.collections),
            disable=(not show_progress),
            description="Building person index...",
        )
        raised_exception = False
        for collection in iterator:
            for volume in collection.volumes():
                context: Paper | Volume = volume
                try:
                    for name_spec in volume.editors:
                        person = self.resolve_namespec(name_spec, allow_creation=True)
                        person.item_ids.append(volume.full_id_tuple)
                    for paper in volume.papers():
                        context = paper
                        name_specs = (
                            # Associate explicitly given authors/editors with the paper
                            it.chain(paper.authors, paper.editors)
                            # For frontmatter, also associate the volume editors with it
                            if not paper.is_frontmatter
                            else paper.get_editors()
                        )
                        for name_spec in name_specs:
                            person = self.resolve_namespec(name_spec, allow_creation=True)
                            person.item_ids.append(paper.full_id_tuple)
                except Exception as exc:
                    note = f"Raised in {context.__class__.__name__} {context.full_id}; {name_spec}"
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
            )
        self.is_data_loaded = True

    def _load_people_index(self) -> None:
        """Loads and parses the `people.yaml` file."""
        filename = self.parent.datadir / Path(PEOPLE_INDEX_FILE)
        merge_list: list[tuple[str, str]] = []

        with open(filename, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=Loader)

        for pid, entry in data.items():
            self.add_person(
                Person(
                    id=pid,
                    parent=self.parent,
                    names=[Name.from_dict(n) for n in entry.pop("names")],
                    orcid=entry.pop("orcid", None),
                    comment=entry.pop("comment", None),
                    degree=entry.pop("degree", None),
                    disable_name_matching=entry.pop("disable_name_matching", False),
                    is_explicit=True,
                )
            )
            for similar_id in entry.pop("similar", []):
                merge_list.append((pid, similar_id))

            # Check for unprocessed keys to catch errors
            if entry:
                log.warning(
                    f"people.yaml: entry '{pid}' has unknown keys: {entry.keys()}"
                )

        # Process IDs with similar names
        for pid_list in self.slugs_to_verified_ids.values():
            for pid in pid_list[1:]:
                self.similar.merge(pid_list[0], pid)
        for a, b in merge_list:
            self.similar.merge(a, b)

    def add_person(self, person: Person) -> None:
        """Add a new person to the index.

        Parameters:
            person: The person to add, which should not exist in the index yet.
        """
        if (pid := person.id) in self.data:
            raise KeyError(f"A Person with ID '{pid}' already exists in the index")
        self.data[pid] = person
        self.similar.add(pid)
        for name in person.names:
            self.name_to_ids[name].append(pid)
            if is_verified_person_id(pid):
                self.slugs_to_verified_ids[name.slugify()].append(pid)

    def resolve_namespec(
        self, name_spec: NameSpecification, allow_creation: bool = False
    ) -> Person:
        """Resolve a name specification to a person, potentially creating it.

        Parameters:
            name_spec: The name specification on the paper, volume, etc.
            allow_creation: If True, will instantiate a new Person object with an unverified ID if no person matching `name_spec` exists.  Defaults to False.

        Returns:
            The person represented by `name_spec`.  If `name_spec.id` is set, this will determine the person to resolve to.  Otherwise, the slugified name will be used to find a matching person; an explicitly-defined (verified) person can be returned if exactly one such person exists and does not have `disable_name_matching` set.  In all other cases, it will resolve to an unverified person.

        Raises:
            NameSpecResolutionError: If `name_spec` cannot be resolved to a Person and `allow_creation` is False.
            PersonUndefinedError: If `name_spec.id` is set, but either the ID or the name used with the ID has not been defined in `people.yaml`. (Inherits from NameSpecResolutionError)
        """
        name = name_spec.name
        if (pid := name_spec.id) is not None:
            # Explicit ID given – should be explicitly defined in people.yaml
            if pid not in self.data or not (person := self.data[pid]).is_explicit:
                raise PersonUndefinedError(
                    name_spec, f"ID '{pid}' wasn't defined in people.yaml"
                )
            if name not in person.names:
                raise PersonUndefinedError(
                    name_spec,
                    f"ID '{pid}' was used with name '{name}' that wasn't defined in people.yaml",
                )
        else:
            # No explicit ID given – generate slug for name matching
            slug = name.slugify()

            # Check if the slugified name matches any verified IDs
            matching_ids = self.slugs_to_verified_ids.get(slug, [])
            if (
                len(matching_ids) == 1
                and not (person := self.data[matching_ids[0]]).disable_name_matching
            ):
                # Slug unambiguously maps to person and name matching not disabled
                pid = person.id
                if name not in person.names:
                    # TODO – currently this loses information that this name
                    # wasn't defined explicitly in people.yaml and just matched
                    # via the slug
                    person.add_name(name)
                    self.name_to_ids[name].append(pid)

            else:
                # Resolve to unverified ID
                pid = f"unverified/{slug}"

                if pid in self.data:
                    # Unverified ID already exists; assume it's the same person
                    person = self.data[pid]
                    if name not in person.names:
                        # If the name scores higher than the current canonical
                        # one, we also assume we should set this as the
                        # canonical one
                        if name.score() > person.canonical_name.score():
                            person.set_canonical_name(name)
                        else:
                            person.add_name(name)
                        self.name_to_ids[name].append(pid)
                elif allow_creation:
                    # Unverified ID doesn't exist yet; create it
                    person = Person(id=pid, parent=self.parent, names=[name])
                    self.add_person(person)
                else:
                    raise NameSpecResolutionError(
                        name_spec,
                        f"NameSpecification resolved to ID '{pid}' which doesn't exist",
                    )

        # Make sure that name variants specified here are registered
        for name in name_spec.variants:
            # TODO – currently this loses information that this name wasn't
            # defined explicitly in people.yaml and just added through a variant
            person.add_name(name)
            if name not in self.name_to_ids:
                self.name_to_ids[name].append(pid)
        return person

    def _add_to_index(
        self, namespecs: Iterable[NameSpecification], item_id: AnthologyIDTuple
    ) -> None:
        """Add persons to the index.

        This function exists for internal use when creating new volumes or papers.  It should not be called manually.
        """
        if not self.is_data_loaded:
            return

        for namespec in namespecs:
            person = self.resolve_namespec(namespec, allow_creation=True)
            person.item_ids.append(item_id)

    def save(self, path: StrPath) -> None:
        """Save the entire index.

        CURRENTLY UNTESTED; DO NOT USE.

        Arguments:
            path: The filename to save to.
        """
        data = []
        for person in self.values():
            attrib: dict[str, Any] = {
                "id": person.id,
                "canonical": asdict(
                    person.canonical_name,
                    filter=lambda a, v: not (a.name == "script" and v is None),
                ),
            }
            if person.item_ids:
                attrib["items"] = person.item_ids
            if len(person.names) > 1:
                attrib["variants"] = [
                    asdict(
                        name, filter=lambda a, v: not (a.name == "script" and v is None)
                    )
                    for name in person.names[1:]
                ]
            similar = self.similar.subset(person.id)
            if len(similar) > 1:
                attrib["similar"] = [id_ for id_ in similar if id_ != person.id]
            if person.comment is not None:
                attrib["comment"] = person.comment
            data.append(attrib)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, Dumper=Dumper)
