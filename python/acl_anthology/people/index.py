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

from attrs import define, field, asdict
from collections import defaultdict
import itertools as it
from os import PathLike
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
from ..exceptions import AnthologyException, AmbiguousNameError, NameIDUndefinedError
from ..utils.logging import get_logger
from . import Person, Name, NameSpecification

if TYPE_CHECKING:
    from ..anthology import Anthology
    from ..collections import Paper, Volume

log = get_logger()
VARIANTS_FILE = "yaml/name_variants.yaml"


@define
class PersonIndex(SlottedDict[Person]):
    """Index object through which all persons (authors/editors) can be accessed.

    Provides dictionary-like functionality mapping person IDs to [Person][acl_anthology.people.person.Person] objects.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        verbose: If False, will not show progress bar when building the index from scratch.
        name_to_ids: A mapping of [Name][acl_anthology.people.name.Name] instances to person IDs.
        similar: A [disjoint-set structure][scipy.cluster.hierarchy.DisjointSet] of persons with similar names.
        is_data_loaded: A flag indicating whether the index has been constructed.
    """

    parent: Anthology = field(repr=False, eq=False)
    verbose: bool = field(default=True)
    name_to_ids: dict[Name, list[str]] = field(
        init=False, repr=False, factory=lambda: defaultdict(list)
    )
    similar: DisjointSet = field(init=False, repr=False, factory=DisjointSet)
    is_data_loaded: bool = field(init=False, repr=False, default=False)

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

        See [get_or_create_person()][acl_anthology.people.index.PersonIndex.get_or_create_person] for exceptions that can be raised by this function.

        Parameters:
            name_spec: A name specification.

        Returns:
            The person associated with this name specification.
        """
        if not self.is_data_loaded:
            self.load()
        return self.get_or_create_person(name_spec, create=False)

    def find_coauthors(self, person: str | Person) -> list[Person]:
        """Find all persons who co-authored or co-edited items with the given person.

        Parameters:
            person: A person ID _or_ Person instance.

        Returns:
            A list of all persons who are co-authors; can be empty.
        """
        if not self.is_data_loaded:
            self.load()
        if isinstance(person, str):
            person = self.data[person]
        coauthors = set()
        for item_id in person.item_ids:
            item = cast("Volume | Paper", self.parent.get(item_id))
            coauthors |= set(
                self.get_or_create_person(ns, create=False).id for ns in item.editors
            )
            if hasattr(item, "authors"):
                coauthors |= set(
                    self.get_or_create_person(ns, create=False).id for ns in item.authors
                )
        coauthors.remove(person.id)
        return [self.data[pid] for pid in coauthors]

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
        self.similar = DisjointSet()
        self.is_data_loaded = False

    def build(self, show_progress: bool = False) -> None:
        """Load the entire Anthology data and build an index of persons.

        Important:
            Exceptions raised during the index creation are sent to the logger, and **not** re-raised.
            Use the [SeverityTracker][acl_anthology.utils.logging.SeverityTracker] to check if an exception occurred.
        """
        self.reset()
        # Load variant list, so IDs defined there are added first
        self._load_variant_list()
        # Go through every single volume/paper and add authors/editors
        iterator = track(
            self.parent.collections.values(),
            total=len(self.parent.collections),
            disable=(not show_progress),
            description="Building person index...",
        )
        for collection in iterator:
            for volume in collection.volumes():
                context: Paper | Volume = volume
                try:
                    for name_spec in volume.editors:
                        person = self.get_or_create_person(name_spec)
                        person.item_ids.add(volume.full_id_tuple)
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
                            person = self.get_or_create_person(name_spec)
                            person.item_ids.add(paper.full_id_tuple)
                except Exception as exc:
                    note = f"Raised in {context.__class__.__name__} {context.full_id}; {name_spec}"
                    # If this is merged into a single if-statement (with "or"),
                    # the type checker complains ¯\_(ツ)_/¯
                    if isinstance(exc, AnthologyException):
                        exc.add_note(note)
                    elif sys.version_info >= (3, 11):
                        exc.add_note(note)
                    log.exception(exc)
        self.is_data_loaded = True

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

    def get_or_create_person(
        self, name_spec: NameSpecification, create: bool = True
    ) -> Person:
        """Get the person represented by a name specification, or create a new one if needed.

        Parameters:
            name_spec: The name specification on the paper, volume, etc.
            create: If False, will not create a new Person object, but instead raise `NameIDUndefinedError` if no person matching `name_spec` exists.  Defaults to True.

        Returns:
            The person represented by `name_spec`.  This will try to use the `id` attribute if it is set, look up the name in the index otherwise, or try to find a matching person by way of an ID clash.  If all of these fail, it will create a new person and return that.

        Raises:
            AmbiguousNameError: If there are multiple known IDs for the given name, but there is no explicit `id` attribute.
            NameIDUndefinedError: If there is an explicit `id` attribute, but the ID has not been defined.
        """
        name = name_spec.name
        if (pid := name_spec.id) is not None:
            try:
                person = self.data[pid]
                person.add_name(name)
            except KeyError:
                exc1 = NameIDUndefinedError(
                    name_spec, f"Name '{name}' used with ID '{pid}' that doesn't exist"
                )
                exc1.add_note("Did you forget to define the ID in name_variants.yaml?")
                raise exc1
        elif pid_list := self.name_to_ids[name]:
            if len(pid_list) > 1:
                exc2 = AmbiguousNameError(
                    name,
                    f"Name '{name.as_first_last()}' is ambiguous, but was used without an ID",
                )
                exc2.add_note(f"Known IDs are: {', '.join(pid_list)}")
                raise exc2
            pid = pid_list[0]
            person = self.data[pid]
        else:
            pid = self.generate_id(name)
            try:
                # If the auto-generated ID already exists, we assume it's the same person
                person = self.data[pid]
                # If the name scores higher than the current canonical one, we
                # also assume we should set this as the canonical one
                if name.score() > person.canonical_name.score():
                    person.set_canonical_name(name)
                else:
                    person.add_name(name)
                self.name_to_ids[name].append(pid)
            except KeyError:
                if create:
                    # If it doesn't, only then do we create a new perosn
                    person = Person(id=pid, parent=self.parent, names=[name])
                    self.add_person(person)
                else:
                    raise NameIDUndefinedError(
                        name_spec,
                        f"Name '{name}' generated ID '{pid}' that doesn't exist",
                    )
        return person

    @staticmethod
    def generate_id(name: Name) -> str:
        """Generates and returns an ID from the given name.

        Warning:
            This **intentionally doesn't guarantee uniqueness** of the generated ID.
            If two names generate identical IDs with this method, we assume they
            refer to the same person.  This happens e.g. when there are missing
            accents in one version, or when we have an inconsistent first/last split
            for multiword names.  These cases have in practice always referred to
            the same person.
        """
        return name.slugify()

    def _load_variant_list(self) -> None:
        """Loads and parses the `name_variant.yaml` file.

        Raises:
            AmbiguousNameError: If there are ambiguous "canonical" names without explicit, unique IDs for each one.
        """
        filename = self.parent.datadir / Path(VARIANTS_FILE)
        merge_list: list[tuple[str, str]] = []
        with open(filename, "r", encoding="utf-8") as f:
            variant_list = yaml.load(f, Loader=Loader)
        for entry in variant_list:
            # Every entry must have a "canonical" name
            canonical = Name.from_dict(entry["canonical"])
            # If it doesn't define an ID, we have to create one
            if (pid := entry.get("id")) is None:
                pid = self.generate_id(canonical)
                if pid in self.data:
                    raise AmbiguousNameError(
                        canonical,
                        (
                            f"While parsing {filename}: "
                            f"name '{canonical.as_first_last()}' is ambiguous, but the "
                            f"automatically generated ID '{pid}' already exists."
                        ),
                    )
            # Parse all the variant names, and make sure canonical stays at index 0
            names = [canonical] + [
                Name.from_dict(var) for var in entry.get("variants", [])
            ]
            # Now we can create a new person from this entry...
            person = Person(
                id=pid,
                parent=self.parent,
                names=names,
                comment=entry.get("comment", None),
            )
            # ...and add it to the index
            self.add_person(person)
            for similar_id in entry.get("similar", []):
                merge_list.append((pid, similar_id))

        # Process IDs with similar names
        for name, pid_list in self.name_to_ids.items():
            for pid in pid_list[1:]:
                self.similar.merge(pid_list[0], pid)
        for a, b in merge_list:
            self.similar.merge(a, b)

    def save(self, path: PathLike[str]) -> None:
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
                attrib["items"] = list(person.item_ids)
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
