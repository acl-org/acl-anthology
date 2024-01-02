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
from os import PathLike
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import yaml

from .containers import SlottedDict

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:  # pragma: no cover
    from yaml import Loader, Dumper  # type: ignore

if TYPE_CHECKING:
    from .anthology import Anthology


@define
class Venue:
    """A publication venue.

    Attributes:
        id: The venue ID, e.g. "acl".
        acronym: The venue's acronym, e.g. "ACL".
        name: The venue's name.  Should _not_ contain any indications of specific events; i.e., "Workshop on...", _not_ "The 1st Workshop on..."
        path: The path of the YAML file representing this venue.
        is_acl: True if this is a venue organized or sponsored by the ACL.
        is_toplevel: True if this venue appears on the ACL Anthology's front page.
        oldstyle_letter: First letter of old-style Anthology IDs that is associated with this venue (e.g., "P" for ACL proceedings).
        url: A website URL for the venue.
    """

    id: str
    acronym: str
    name: str
    path: Path
    is_acl: bool = field(default=False)
    is_toplevel: bool = field(default=False)
    oldstyle_letter: Optional[str] = field(default=None)
    url: Optional[str] = field(default=None)
    type: Optional[str] = field(default=None)  # TODO: should we deprecate this?

    @classmethod
    def load_from_yaml(cls, path: PathLike[str]) -> Venue:
        """Instantiates a venue from its YAML file.

        Arguments:
            path: The YAML file defining this venue.

        Warning:
            Currently assumes that files are named `{venue_id}.yaml`.
        """
        path = Path(path)
        venue_id = path.name[:-5]
        with open(path, "r", encoding="utf-8") as f:
            kwargs = yaml.load(f, Loader=Loader)
        return cls(venue_id, path=path, **kwargs)

    def save(self, path: Optional[PathLike[str]] = None) -> None:
        """Saves this venue as a YAML file.

        Arguments:
            path: The filename to save to. If None, defaults to `self.path`.
        """
        if path is None:
            path = self.path
        # Serialize everything except "id", "path" and default values
        values = asdict(
            self, filter=lambda a, v: a.name not in ("id", "path") and v != a.default
        )
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(values, f, Dumper=Dumper)


@define
class VenueIndex(SlottedDict[Venue]):
    """Index object through which venues and their associated volumes can be accessed.

    Provides dictionary-like functionality mapping venue IDs to [Venue][acl_anthology.venues.Venue] objects.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        is_data_loaded: A flag indicating whether the venue YAML files have been loaded.
    """

    parent: Anthology = field(repr=False, eq=False)
    is_data_loaded: bool = field(init=False, repr=False, default=False)

    def load(self) -> None:
        """Loads and parses the `venues/*.yaml` files.

        Raises:
            KeyError: If a mandatory key is missing in a YAML file.
        """
        if self.is_data_loaded:
            return
        for yamlpath in self.parent.datadir.glob("yaml/venues/*.yaml"):
            venue = Venue.load_from_yaml(yamlpath)
            self.data[venue.id] = venue
        self.is_data_loaded = True

    def save(self) -> None:
        """Saves all venue metadata to `venues/*.yaml` files."""
        for venue in self.values():
            venue.save()
