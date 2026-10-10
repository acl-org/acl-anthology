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

from attrs import define, field, validators as v, asdict
from collections import defaultdict
from msgspec import json
from pathlib import Path
from typing import Any, Iterator, Optional, TYPE_CHECKING
import sys

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

from .utils.attrs import attach_custom_repr, auto_validate_types, repr_item_ids
from .utils.ids import AnthologyIDTuple, build_id_from_tuple
from .constants import RE_VENUE_ID
from .containers import SlottedDict

if TYPE_CHECKING:
    from _typeshed import StrPath
    from .anthology import Anthology
    from .collections import Volume
    from .sigs import SIG


VENUE_INDEX_FILE = "json/venues.json"


@attach_custom_repr
@define(field_transformer=auto_validate_types)
class Venue:
    """A publication venue.

    Attributes:
        id: The venue ID, e.g. "acl".
        parent: The parent VenueIndex instance to which this venue belongs.
        acronym: The venue's acronym, e.g. "ACL".
        name: The venue's name.  Should _not_ contain any indications of specific events; i.e., "Workshop on...", _not_ "The 1st Workshop on..."
        is_acl: True if this is a venue organized or sponsored by the ACL.
        is_toplevel: True if this venue appears on the ACL Anthology's front page.
        item_ids: An unordered set of volume IDs associated with this venue.
        oldstyle_letter: First letter of old-style Anthology IDs that is associated with this venue (e.g., "P" for ACL proceedings).
        url: A website URL for the venue.
        description: A description text that appears on the website and may contain Markdown.
        related_ids: A list of venue IDs that should be considered related to this one.  This induces a symmetric relationship.  To _find_ related venues, use [`Venue.related()`][acl_anthology.venues.Venue.related].
        type: The venue classification, currently "journal" or "workshop".
    """

    id: str = field(
        converter=str,
        validator=v.matches_re(RE_VENUE_ID),
        metadata={"repr_omits_field_name": True},
    )
    parent: VenueIndex = field(repr=False, eq=False)
    acronym: str = field(converter=str)
    name: str = field(converter=str)
    is_acl: bool = field(default=False, converter=bool)
    is_toplevel: bool = field(default=False, converter=bool)
    item_ids: set[AnthologyIDTuple] = field(
        factory=set, converter=set, repr=repr_item_ids, eq=False
    )
    oldstyle_letter: Optional[str] = field(
        default=None, validator=v.optional(v.matches_re("^[A-Z]$"))
    )
    url: Optional[str] = field(default=None, validator=v.optional(v.instance_of(str)))
    description: Optional[str] = field(
        default=None, validator=v.optional(v.instance_of(str))
    )
    related_ids: list[str] = field(factory=list)
    type: Optional[str] = field(default=None, validator=v.optional(v.instance_of(str)))
    # SIG–Venue associations are stored in SIGs, so this attribute is populated by SIG/SIGIndex
    _sig_ids: set[str] = field(factory=set, converter=set, repr=False, eq=False)

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.parent.parent

    @deprecated("Venue.save() is deprecated in favor of VenueIndex.save()")
    def save(self, path: Optional[StrPath] = None) -> None:  # pragma: no cover
        """Saves this venue."""
        if path is None:
            raise UserWarning(
                "Providing a 'path' argument to Venue.save() has no effect anymore"
            )

        self.parent.save()

    def volumes(self) -> Iterator[Volume]:
        """Returns an iterator over all volumes associated with this venue."""
        for anthology_id in self.item_ids:
            volume = self.root.get_volume(anthology_id)
            if volume is None:  # pragma: no cover
                raise ValueError(
                    f"Venue {self.id} lists associated volume {build_id_from_tuple(anthology_id)}, which doesn't exist"
                )
            yield volume

    def related(self) -> list[Venue]:
        """
        Returns:
            A list of venues marked as being related to this venue.
        """
        try:
            return [
                self.parent[related_id] for related_id in self.parent.related[self.id]
            ]
        except KeyError as exc:
            exc.add_note(
                f"Most likely, venue ID '{exc.args[0]}' is not defined in venues.json"
            )
            raise exc

    def sigs(self) -> list[SIG]:
        """
        Returns:
            A list of SIGs normally associated with this venue, to be used as a hint at ingestion time.

        Note:
            This is only used as an aid during ingestion; these associations are _not_ propagated automatically to volumes (i.e. volumes belonging to this venue are not automatically associated with these SIGs, too).

            To change the association of a venue to a SIG, modify [SIG.venue_ids][acl_anthology.sigs.SIG.venue_ids].
        """
        try:
            return [self.root.sigs[sig] for sig in self._sig_ids]
        except KeyError as exc:  # pragma: no cover
            exc.add_note(
                f"Most likely, SIG ID '{exc.args[0]}' is not defined in sigs.json"
            )
            raise exc


@attach_custom_repr
@define
class VenueIndex(SlottedDict[Venue]):
    """Index object through which venues and their associated volumes can be accessed.

    Provides dictionary-like functionality mapping venue IDs to [Venue][acl_anthology.venues.Venue] objects.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        path: The path to `venues.json`.
        no_item_ids: If set to True, skips parsing all XML files, which means the reverse-indexing of Volumes via `Venue.item_ids` will not be available.
        related: A dictionary mapping venue IDs to a set of related venue IDs.
        is_data_loaded: A flag indicating whether the data file has been loaded and the index has been built.
    """

    parent: Anthology = field(repr=False, eq=False)
    path: Path = field(init=False)
    no_item_ids: bool = field(repr=False, default=False)
    _related: dict[str, set[str]] = field(
        init=False, repr=False, factory=lambda: defaultdict(set)
    )
    is_data_loaded: bool = field(
        init=False, default=False, metadata={"repr_omit_if": True}
    )

    @path.default
    def _path(self) -> Path:
        return self.parent.datadir / Path(VENUE_INDEX_FILE)

    @property
    def related(self) -> dict[str, set[str]]:
        if not self.is_data_loaded:
            self.load()
        return self._related

    def load(self) -> None:
        """Load and parse the `venues.json` file.

        Raises:
            KeyError: If a mandatory key is missing in a venue entry.
        """
        # This function exists so we can later add the option to read the index
        # from a cache if it doesn't need re-building.
        if self.is_data_loaded:
            return

        with open(self.path, "rb") as f:
            data = json.decode(f.read())

        for venue_id, params in data.items():
            self.data[venue_id] = Venue(id=venue_id, parent=self, **params)

        self.build()
        self.is_data_loaded = True

    def create(self, id: str, acronym: str, name: str, **kwargs: Any) -> Venue:
        """Create a new venue and add it to the index.

        Parameters:
            id: The ID of the new venue.
            acronym: The acronym of the new venue.
            name: The name of the new venue.
            **kwargs: Any valid optional attribute of [Venue][acl_anthology.venues.Venue], with the exception of `item_ids` and `oldstyle_letter`, which cannot be set.

        Returns:
            The created [Venue][acl_anthology.venues.Venue] object.

        Raises:
            KeyError: If an invalid attribute is supplied in `**kwargs`.
        """
        if "item_ids" in kwargs:
            raise KeyError(
                "Cannot specify `item_ids` for Venue; add its ID to the volume(s) instead."
            )  # pragma: no cover
        if "oldstyle_letter" in kwargs:
            raise KeyError(
                "Cannot specify a new venue with an old-style letter."
            )  # pragma: no cover

        kwargs["parent"] = self
        venue = Venue(id=id, acronym=acronym, name=name, **kwargs)
        self.data[id] = venue
        return venue

    def reset(self) -> None:
        """Reset the index."""
        self.data = {}
        self._related = defaultdict(set)
        self.is_data_loaded = False

    def build(self) -> None:
        """Load the entire Anthology data and build an index of venues.

        Raises:
            ValueError: If a volume lists a venue ID that doesn't exist (i.e., isn't defined in `venues.json`).
        """
        for venue_id, venue in self.data.items():
            for related_id in venue.related_ids:
                self._related[venue_id].add(related_id)
                self._related[related_id].add(venue_id)
        if self.no_item_ids:
            return
        for sig_id, sig in self.parent.sigs.items():
            for venue_id in sig.venue_ids:
                try:
                    self.data[venue_id]._sig_ids.add(sig_id)
                except KeyError:  # pragma: no cover
                    raise ValueError(
                        f"SIG {sig.id} lists associated venue {venue_id}, which doesn't exist"
                    )
        for volume in self.parent.volumes():
            for venue_id in volume.venue_ids:
                try:
                    self.data[venue_id].item_ids.add(volume.full_id_tuple)
                except KeyError:  # pragma: no cover
                    raise ValueError(
                        f"Volume {volume.full_id} lists associated venue {venue_id}, which doesn't exist"
                    )

    def save(self, path: Optional[StrPath] = None) -> None:
        """Save the `venues.json` file.

        Arguments:
            path: The filename to save to. If None, defaults to the parent Anthology's `venues.json` file.
        """
        if path is None:  # pragma: no cover
            self.parent._warn_if_in_default_path()
            path = self.path

        data = {}
        for venue_id, venue in sorted(self.items(), key=lambda x: x[0]):
            # Serialize everything except "id", "item_ids", "parent" and default values
            data[venue_id] = asdict(
                venue,
                filter=lambda a, v: a.name not in ("id", "item_ids", "parent", "_sig_ids")
                and v != a.default
                and not (isinstance(v, list) and len(v) == 0),
            )

        with open(path, "wb") as f:
            f.write(json.format(json.encode(data)))
            f.write(b"\n")
