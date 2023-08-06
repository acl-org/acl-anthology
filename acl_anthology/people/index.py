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

from pathlib import Path
from typing import TYPE_CHECKING
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader  # type: ignore

from . import Person, Name

if TYPE_CHECKING:
    from ..anthology import Anthology

VARIANTS_FILE = "yaml/name_variants.yaml"


class PersonIndex:
    """Index object through which all persons (authors/editors) can be accessed.

    Attributes:
        parent (Anthology): The parent Anthology instance to which this index belongs.
    """

    def __init__(self, parent: Anthology) -> None:
        self.parent = parent

        self.people: dict[str, Person] = {}
        """A mapping of IDs to [Person][acl_anthology.people.person.Person] instances."""

        self.is_built = False
        """A flag indicating whether the index has been constructed."""

    def build_index(self) -> None:
        """Load the entire Anthology data and build an index of persons."""
        raise NotImplementedError()

    @staticmethod
    def generate_id(name: Name) -> str:
        """Generates and returns an ID from the given name.

        This **intentionally doesn't guarantee uniqueness** of the generated ID.
        If two names generate identical IDs with this method, we assume they
        refer to the same person.  This happens e.g. when there are missing
        accents in one version, or when we have an inconsistent first/last split
        for multiword names.  These cases have in practice always referred to
        the same person.
        """
        return name.slugify()

    def _load_variant_list(self) -> None:
        filename = self.parent.datadir / Path(VARIANTS_FILE)
        with open(filename, "r") as f:
            variant_list = yaml.load(f, Loader=Loader)
        for entry in variant_list:
            # Every entry must have a "canonical" name
            canonical = Name.from_dict(entry["canonical"])
            # If it doesn't define an ID, we have to create one
            if (pid := entry.get("id")) is None:
                pid = self.generate_id(canonical)
            # Parse all the variant names, and make sure canonical stays at index 0
            names = [canonical] + [
                Name.from_dict(var) for var in entry.get("variants", [])
            ]
            # Now we can create a new person from this entry...
            person = Person(id=pid, names=names)
            # ...and add it to the index
            self.people[pid] = person
            # TODO: process the "similar" key
