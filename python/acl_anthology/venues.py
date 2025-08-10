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

from attrs import define, field, validators as v, asdict
from pathlib import Path
from typing import Iterator, Optional, TYPE_CHECKING
import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:  # pragma: no cover
    from yaml import Loader, Dumper  # type: ignore

from .utils.attrs import auto_validate_types
from .utils.ids import AnthologyIDTuple, build_id_from_tuple
from .containers import SlottedDict

if TYPE_CHECKING:
    from _typeshed import StrPath
    from .anthology import Anthology
    from .collections import Volume


@define(field_transformer=auto_validate_types)
class Venue:
    """A publication venue.

    Attributes:
        id: The venue ID, e.g. "acl".
        parent: The parent Anthology instance to which this venue belongs.
        acronym: The venue's acronym, e.g. "ACL".
        name: The venue's name.  Should _not_ contain any indications of specific events; i.e., "Workshop on...", _not_ "The 1st Workshop on..."
        path: The path of the YAML file representing this venue.
        is_acl: True if this is a venue organized or sponsored by the ACL.
        is_toplevel: True if this venue appears on the ACL Anthology's front page.
        item_ids: A list of volume IDs associated with this venue.
        oldstyle_letter: First letter of old-style Anthology IDs that is associated with this venue (e.g., "P" for ACL proceedings).
        url: A website URL for the venue.
    """

    id: str = field(converter=str)
    parent: Anthology = field(repr=False, eq=False)
    acronym: str = field(converter=str)
    name: str = field(converter=str)
    path: Path = field(converter=Path, eq=False)
    is_acl: bool = field(default=False, converter=bool)
    is_toplevel: bool = field(default=False, converter=bool)
    item_ids: list[AnthologyIDTuple] = field(
        factory=list,
        repr=lambda x: f"<list of {len(x)} AnthologyIDTuple objects>",
        eq=False,
    )
    oldstyle_letter: Optional[str] = field(
        default=None, validator=v.optional(v.matches_re("^[A-Z]$"))
    )
    url: Optional[str] = field(default=None, validator=v.optional(v.instance_of(str)))
    # TODO: Should we reconsider 'type'? Currently used to designate journals
    # at the venue level; but journals are also marked on the individual
    # volumes.
    type: Optional[str] = field(default=None, validator=v.optional(v.instance_of(str)))

    @classmethod
    def load_from_yaml(cls, path: StrPath, parent: Anthology) -> Venue:
        """Instantiates a venue from its YAML file.

        Arguments:
            path: The YAML file defining this venue.
            parent: The parent Anthology instance.

        Warning:
            Currently assumes that files are named `{venue_id}.yaml`.
        """
        path = Path(path)
        venue_id = path.name[:-5]
        with open(path, "r", encoding="utf-8") as f:
            kwargs = yaml.load(f, Loader=Loader)
        return cls(venue_id, parent=parent, path=path, **kwargs)

    def save(self, path: Optional[StrPath] = None) -> None:
        """Saves this venue as a YAML file.

        Arguments:
            path: The filename to save to. If None, defaults to `self.path`.
        """
        if path is None:
            path = self.path
        # Serialize everything except "id", "item_ids", "path", "parent" and default values
        values = asdict(
            self,
            filter=lambda a, v: a.name not in ("id", "item_ids", "parent", "path")
            and v != a.default,
        )
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(values, f, Dumper=Dumper)

    def volumes(self) -> Iterator[Volume]:
        """Returns an iterator over all volumes associated with this venue."""
        for anthology_id in self.item_ids:
            volume = self.parent.get_volume(anthology_id)
            if volume is None:
                raise ValueError(
                    f"Venue {self.id} lists associated volume {build_id_from_tuple(anthology_id)}, which doesn't exist"
                )
            yield volume


@define
class VenueIndex(SlottedDict[Venue]):
    """Index object through which venues and their associated volumes can be accessed.

    Provides dictionary-like functionality mapping venue IDs to [Venue][acl_anthology.venues.Venue] objects.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        no_item_ids: If set to True, skips parsing all XML files, which means the reverse-indexing of Volumes via `Venue.item_ids` will not be available.
        is_data_loaded: A flag indicating whether the venue YAML files have been loaded and the index has been built.
    """

    parent: Anthology = field(repr=False, eq=False)
    no_item_ids: bool = field(repr=False, default=False)
    is_data_loaded: bool = field(init=False, repr=True, default=False)

    def load(self) -> None:
        """Loads and parses the `venues/*.yaml` files.

        Raises:
            KeyError: If a mandatory key is missing in a YAML file.
        """
        # This function exists so we can later add the option to read the index
        # from a cache if it doesn't need re-building.
        if self.is_data_loaded:
            return
        for yamlpath in self.parent.datadir.glob("yaml/venues/*.yaml"):
            venue = Venue.load_from_yaml(yamlpath, self.parent)
            self.data[venue.id] = venue
        self.build()
        self.is_data_loaded = True

    def reset(self) -> None:
        """Resets the index."""
        self.data = {}
        self.is_data_loaded = False

    def build(self) -> None:
        """Load the entire Anthology data and build an index of venues.

        Raises:
            ValueError: If a volume lists a venue ID that doesn't exist (i.e., isn't defined in the venue YAML files).
        """
        if self.no_item_ids:
            return
        for volume in self.parent.volumes():
            for venue_id in volume.venue_ids:
                if venue_id not in self.data:
                    raise ValueError(
                        f"Volume {volume.full_id} lists associated venue {venue_id}, which doesn't exist"
                    )
                self.data[venue_id].item_ids.append(volume.full_id_tuple)

    def save(self) -> None:
        """Saves all venue metadata to `venues/*.yaml` files."""
        for venue in self.values():
            venue.save()
