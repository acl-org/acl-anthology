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
from rich.progress import track
from typing import TYPE_CHECKING

from ..containers import SlottedDict
from ..text import MarkupText
from .event import Event

if TYPE_CHECKING:
    from ..anthology import Anthology


@define
class EventIndex(SlottedDict[Event]):
    """Index object through which events can be accessed.

    This is a quite inefficient implementation, intended to be temporary pending the resolution of [https://github.com/acl-org/acl-anthology/issues/2743][].  As most events are currently implicitly created, it requires loading the entire Anthology data.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        verbose: If True, will show progress bar when building the index from scratch.
        is_data_loaded: A flag indicating whether the index has been constructed.
    """

    parent: Anthology = field(repr=False, eq=False)
    verbose: bool = field(default=False)
    is_data_loaded: bool = field(init=False, repr=False, default=False)

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
            if (event := collection.get_event()) is not None:
                self.data[event.id] = event

            for volume in collection.volumes():
                for venue_id in volume.venue_ids:
                    event_id = f"{venue_id}-{volume.year}"
                    if (event := self.data.get(event_id)) is None:
                        venue_name = self.parent.venues[venue_id].name
                        event_name = f"{venue_name} ({volume.year})"
                        self.data[event_id] = Event(
                            event_id,
                            collection,
                            is_explicit=False,
                            colocated_ids=[volume.full_id],
                            title=MarkupText.from_string(event_name),
                        )
                    elif volume.full_id not in event.colocated_ids:
                        event.colocated_ids.append(volume.full_id)

        self.is_data_loaded = True
