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

from attrs import define, field
from typing import Iterator, Optional, TYPE_CHECKING
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader  # type: ignore

if TYPE_CHECKING:
    from .anthology import Anthology


@define
class Venue:
    """A publication venue.

    Attributes:
        id: The venue ID, e.g. "acl".
        acronym: The venue's acronym, e.g. "ACL".
        name: The venue's name.  Should _not_ contain any indications of specific events; i.e., "Workshop on...", _not_ "The 1st Workshop on..."
        is_acl: True if this is a venue organized or sponsored by the ACL.
        is_toplevel: True if this venue appears on the ACL Anthology's front page.
        oldstyle_letter: First letter of old-style Anthology IDs that is associated with this venue (e.g., "P" for ACL proceedings).
        url: A website URL for the venue.
    """

    id: str
    acronym: str
    name: str
    is_acl: bool = field(default=False)
    is_toplevel: bool = field(default=False)
    oldstyle_letter: Optional[str] = field(default=None)
    url: Optional[str] = field(default=None)


class VenueIndex:
    """Index object through which venues and their associated volumes can be accessed.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
    """

    def __init__(self, parent: Anthology) -> None:
        self.parent: Anthology = parent

        self.venues: dict[str, Venue] = {}
        """A mapping of IDs to [Venue][acl_anthology.venues.Venue] instances."""

        self._load_yaml_metadata()

    def __iter__(self) -> Iterator[Venue]:
        """Returns an iterator over all venues."""
        yield from self.venues.values()

    def get(self, venue_id: str) -> Venue | None:
        """Access a venue by its ID.

        Parameters:
            venue_id: A venue ID.

        Returns:
            The venue associated with this ID, if one exists.
        """
        return self.venues.get(venue_id)

    def _load_yaml_metadata(self) -> None:
        """Loads and parses the `venues/*.yaml` files.

        Raises:
            KeyError: If a mandatory key is missing in a YAML file.
        """
        for yamlpath in self.parent.datadir.glob("yaml/venues/*.yaml"):
            venue_id = yamlpath.name[:-5]
            with open(yamlpath, "r") as f:
                kwargs = yaml.load(f, Loader=Loader)
            if "type" in kwargs:  # currently ignored
                del kwargs["type"]
            self.venues[venue_id] = Venue(venue_id, **kwargs)
