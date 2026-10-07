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

import attrs
from attrs import define, field, setters, validators as v, asdict
from collections import defaultdict
from msgspec import json
from pathlib import Path
from typing import Any, Iterator, Optional, TYPE_CHECKING
import sys

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

from .collections import Volume
from .containers import SlottedDict
from .utils.attrs import attach_custom_repr, into_str_tuple, repr_item_ids
from .utils.ids import AnthologyID, AnthologyIDTuple, build_id_from_tuple
from .utils.similarity import SimilarityGroups
from .venues import Venue

if TYPE_CHECKING:
    from _typeshed import StrPath
    from .anthology import Anthology
    from .collections.volume import Volume


SIG_INDEX_FILE = "json/sigs.json"


def _update_venues(
    sig: SIG, attr: attrs.Attribute[Any], value: tuple[str, ...]
) -> tuple[str, ...]:
    """Update reverse-mapping from venues based on a SIG's `venue_ids`.

    Intended to be called from `on_setattr` of an [attrs.field][].
    """
    venue_index = sig.root.venues
    if not venue_index.is_data_loaded:
        return value

    old_value = getattr(sig, attr.name)
    for venue in set(old_value) - set(value):
        # Venues that are being removed from this SIG
        venue_index[venue]._sig_ids.discard(sig.id)

    for venue in set(value) - set(old_value):
        # Venues that are being added to this volume
        try:
            venue_index[venue]._sig_ids.add(sig.id)
        except KeyError:
            raise ValueError(f"Tried setting venue that doesn't exist: {venue}")
    return value


@attach_custom_repr
@define
class SIG:
    """A special interest group (SIG).

    Attributes:
        id: The SIG ID, e.g. "sigsem".
        parent: The parent SIGIndex instance.
        acronym: The SIG's acronym or short name, e.g. "SIGSEM".
        name: The SIG's full name.
        url: A website URL for the SIG.
        description: A description text that appears on the website and may contain Markdown.
        related_ids: A list of SIG IDs that should be considered related to this one.  Do **not** use this to _find_ related SIGs; that should be done via [`SIGIndex.related`][acl_anthology.sigs.SIGIndex].
        external_meetings: A list of SIGMeeting instances recording meetings that are not part of the Anthology.
        venue_ids: A list of venues associated with this SIG, to be used as an aid during ingestion.  See also [venues()][acl_anthology.sigs.SIG.venues].
        item_ids: An unordered set of volume IDs associated with this venue.
    """

    id: str = field(converter=str, metadata={"repr_omits_field_name": True})
    parent: SIGIndex = field(repr=False, eq=False)
    acronym: str = field(converter=str)
    name: str = field(converter=str)
    url: Optional[str] = field(default=None, validator=v.optional(v.instance_of(str)))
    description: Optional[str] = field(
        default=None, validator=v.optional(v.instance_of(str))
    )
    related_ids: list[str] = field(factory=list)
    external_meetings: list[SIGMeeting] = field(
        factory=list,
        repr=lambda x: f"<list[str | SIGMeeting] with {len(x)} item{'' if len(x) == 1 else 's'}>",
    )
    venue_ids: tuple[str, ...] = field(
        default=(),
        converter=into_str_tuple,
        on_setattr=[
            setters.convert,
            setters.validate,
            _update_venues,
        ],
    )
    item_ids: set[AnthologyIDTuple] = field(
        factory=set, converter=set, repr=repr_item_ids, eq=False
    )

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.parent.parent

    def get_meetings_by_year(self) -> dict[str, list[str | SIGMeeting]]:
        """Get all associated meetings, grouped by year.

        Returns:
            A dictionary where keys are strings representing years, and values are meetings of this SIG in that year.
        """
        by_year: dict[str, list[str | SIGMeeting]] = defaultdict(list)
        for volume in self.volumes():
            by_year[volume.year].append(volume.full_id)
        for meeting in self.external_meetings:
            by_year[meeting.year].append(meeting)
        return by_year

    @deprecated("SIG.save() is deprecated in favor of SIGIndex.save()")
    def save(self, path: Optional[StrPath] = None) -> None:  # pragma: no cover
        """Saves this SIG."""
        if path is None:
            raise UserWarning(
                "Providing a 'path' argument to SIG.save() has no effect anymore"
            )

        self.parent.save()

    def volumes(self) -> Iterator[Volume]:
        """Iterate over all volumes that are associated with this SIG."""
        for anthology_id in self.item_ids:
            volume = self.root.get_volume(anthology_id)
            if volume is None:  # pragma: no cover
                raise ValueError(
                    f"SIG {self.id} lists associated volume {build_id_from_tuple(anthology_id)}, which doesn't exist"
                )
            yield volume

    def add_venue(self, venue: str | Venue) -> None:
        """Associate a venue with this SIG.

        If the venue is already associated with this SIG, this will do nothing.

        Arguments:
            venue: A Venue object, or a string representing a venue ID.

        Raises:
            ValueError: If a string was given, but the venue does not exist.
        """
        if isinstance(venue, str):
            venue_id = venue
            if venue_id not in self.root.venues:
                raise ValueError(f"Venue doesn't exist: '{venue_id}'")
        else:
            venue_id = venue.id
        if venue_id in self.venue_ids:
            return
        self.venue_ids += (venue_id,)

    def remove_venue(self, venue: str | Venue) -> None:
        """Remove a venue association from this SIG.

        If the venue is not associated with this SIG, this will do nothing.

        Arguments:
            venue: A Venue object, or a string representing a venue ID.
        """
        venue_id = venue.id if isinstance(venue, Venue) else venue
        if venue_id in self.venue_ids:
            self.venue_ids = tuple(x for x in self.venue_ids if x != venue_id)

    def venues(self) -> list[Venue]:
        """A list of venues associated with this SIG.

        Note:
            This is only used as an aid during ingestion; these associations are _not_ propagated automatically to volumes (i.e. volumes belonging to this SIG are not automatically associated with these venues, too).
        """
        try:
            return [self.root.venues[vid] for vid in self.venue_ids]
        except KeyError as exc:  # pragma: no cover
            exc.add_note(
                f"Most likely, venue ID '{exc.args[0]}' is not defined in venues.json"
            )
            raise exc


@attach_custom_repr
@define(unsafe_hash=True)
class SIGMeeting:
    """A meeting of a SIG that doesn't have a volume in the Anthology.

    Attributes:
        year: The year of the meeting.
        name: The name of the event/proceedings.
        url: A website URL for the meeting.
    """

    year: str
    name: str
    url: Optional[str] = field(default=None)


@attach_custom_repr
@define
class SIGIndex(SlottedDict[SIG]):
    """Index object through which SIGs and their associated volumes can be accessed.

    Provides dictionary-like functionality mapping SIG IDs to [SIG][acl_anthology.sigs.SIG] objects.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        path: The path to `sigs.json`.
        no_item_ids: If set to True, skips parsing all XML files, which means the reverse-indexing of Volumes via `Venue.item_ids` will not be available.
        related: A [SimilarityGroups][acl_anthology.utils.similarity.SimilarityGroups] structure of SIGs with some relationship to each other.
        is_data_loaded: A flag indicating whether the data file has been loaded and the index has been built.
    """

    parent: Anthology = field(repr=False, eq=False)
    path: Path = field(init=False)
    no_item_ids: bool = field(repr=False, default=False)
    _related: SimilarityGroups = field(init=False, repr=False, factory=SimilarityGroups)
    is_data_loaded: bool = field(
        init=False, default=False, metadata={"repr_omit_if": True}
    )

    @path.default
    def _path(self) -> Path:
        return self.parent.datadir / Path(SIG_INDEX_FILE)

    @property
    def related(self) -> SimilarityGroups:
        if not self.is_data_loaded:
            self.load()
        return self._related

    def load(self) -> None:
        """Load and parse the `sigs.json` file.

        Raises:
            KeyError: If a mandatory key is missing in a SIG entry.
        """
        # This function exists so we can later add the option to read the index
        # from a cache if it doesn't need re-building.
        if self.is_data_loaded:
            return

        with open(self.path, "rb") as f:
            data = json.decode(f.read())

        for sig_id, params in data.items():
            if "external_meetings" in params:
                params["external_meetings"] = [
                    SIGMeeting(**meeting) for meeting in params["external_meetings"]
                ]
            self.data[sig_id] = SIG(id=sig_id, parent=self, **params)

        self.build()
        self.is_data_loaded = True

    def create(self, id: str, acronym: str, name: str, **kwargs: Any) -> SIG:
        """Create a new venue and add it to the index.

        Parameters:
            id: The ID of the new SIG.
            acronym: The acronym of the new SIG.
            name: The name of the new SIG.
            **kwargs: Any valid optional attribute of [SIG][acl_anthology.sigs.SIG], with the exception of `item_ids`, which cannot be set.

        Returns:
            The created [SIG][acl_anthology.sigs.SIG] object.

        Raises:
            KeyError: If an invalid attribute is supplied in `**kwargs`.
        """
        if "item_ids" in kwargs:
            raise KeyError(
                "Cannot specify `item_ids` for SIG; add its ID to the volume(s) instead."
            )  # pragma: no cover

        kwargs["parent"] = self
        sig = SIG(id=id, acronym=acronym, name=name, **kwargs)
        self.data[id] = sig
        return sig

    def reset(self) -> None:
        """Reset the index."""
        self.data = {}
        self._related = SimilarityGroups()
        self.is_data_loaded = False

    def build(self) -> None:
        """Load the entire Anthology data and build an index of SIGs.

        Raises:
            ValueError: If a volume lists a SIG ID that doesn't exist (i.e., isn't defined in `sigs.json`).
        """
        for sig_id, sig in self.data.items():
            for related_id in sig.related_ids:
                self._related.merge(sig_id, related_id)
        if self.no_item_ids:
            return
        for volume in self.parent.volumes():
            for sig_id in volume.sig_ids:
                try:
                    self.data[sig_id].item_ids.add(volume.full_id_tuple)
                except KeyError:  # pragma: no cover
                    raise ValueError(
                        f"Volume {volume.full_id} lists associated SIG {sig_id}, which doesn't exist"
                    )

    def save(self, path: Optional[StrPath] = None) -> None:
        """Save the `sigs.json` file.

        Arguments:
            path: The filename to save to. If None, defaults to the parent Anthology's `sigs.json` file.
        """
        if path is None:  # pragma: no cover
            self.parent._warn_if_in_default_path()
            path = self.path

        data = {}
        for sig_id, venue in sorted(self.items(), key=lambda x: x[0]):
            # Serialize everything except "id", "item_ids", "parent" and default values
            data[sig_id] = asdict(
                venue,
                filter=lambda a, v: a.name not in ("id", "item_ids", "parent")
                and v != a.default
                and not (isinstance(v, list) and len(v) == 0),
            )

        with open(path, "wb") as f:
            f.write(json.format(json.encode(data)))
            f.write(b"\n")

    @deprecated("SIGIndex.by_volume() is deprecated; use Volume.sigs() instead")
    def by_volume(self, volume: Volume | AnthologyID) -> list[SIG]:  # pragma: no cover
        """Find SIGs associated with a volume."""
        if not isinstance(volume, Volume):
            if (vol := self.parent.get_volume(volume)) is None:
                raise ValueError(f"Volume {volume} doesn't exist")
            volume = vol

        return volume.sigs()
