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

from attrs import define, field
from collections import defaultdict
from rich.progress import track
from typing import TYPE_CHECKING

from ..containers import SlottedDict
from ..text import MarkupText
from ..utils.ids import AnthologyID, AnthologyIDTuple, parse_id
from .event import Event
from .volume import Volume

if TYPE_CHECKING:
    from ..anthology import Anthology


@define
class EventIndex(SlottedDict[Event]):
    """Index object through which events can be accessed.

    This is a quite inefficient implementation, intended to be temporary pending the resolution of [issue #2743](https://github.com/acl-org/acl-anthology/issues/2743).  As most events are currently implicitly created, it requires loading the entire Anthology data.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        verbose: If False, will not show progress bar when building the index from scratch.
        reverse: A mapping of volume IDs to a set of associated event IDs.
        is_data_loaded: A flag indicating whether the index has been constructed.
    """

    parent: Anthology = field(repr=False, eq=False)
    verbose: bool = field(default=True)
    reverse: dict[AnthologyIDTuple, set[str]] = field(
        init=False, repr=False, factory=lambda: defaultdict(set)
    )
    is_data_loaded: bool = field(init=False, repr=False, default=False)

    def by_volume(self, volume: Volume | AnthologyID) -> list[Event]:
        """Find events associated with a volume."""
        if not self.is_data_loaded:
            self.load()

        if isinstance(volume, Volume):
            volume_fid = volume.full_id_tuple
        else:
            volume_fid = parse_id(volume)

        return [self.data[event_id] for event_id in self.reverse[volume_fid]]

    def load(self) -> None:
        """Load the entire Anthology data and build an index of events."""
        if self.is_data_loaded:
            return

        iterator = track(
            self.parent.collections.values(),
            total=len(self.parent.collections),
            disable=(not self.verbose),
            description=" Building event index...",
        )
        for collection in iterator:
            if (explicit_event := collection.get_event()) is not None:
                self.data[explicit_event.id] = explicit_event
                for volume_fid in explicit_event.colocated_ids:
                    self.reverse[volume_fid].add(explicit_event.id)

            for volume in collection.volumes():
                volume_fid = volume.full_id_tuple
                if explicit_event is not None:
                    self.reverse[volume_fid].add(explicit_event.id)
                for venue_id in volume.venue_ids:
                    event_id = f"{venue_id}-{volume.year}"
                    if (event := self.data.get(event_id)) is None:
                        venue_name = self.parent.venues[venue_id].name
                        event_name = f"{venue_name} ({volume.year})"
                        self.data[event_id] = Event(
                            event_id,
                            collection,
                            is_explicit=False,
                            colocated_ids=[volume_fid],
                            title=MarkupText.from_string(event_name),
                        )
                    elif volume_fid not in event.colocated_ids:
                        event.colocated_ids.append(volume_fid)
                    self.reverse[volume_fid].add(event_id)

        self.is_data_loaded = True
