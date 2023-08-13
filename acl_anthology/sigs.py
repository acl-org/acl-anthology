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
from collections import ChainMap
from typing import Iterator, Optional, TYPE_CHECKING
import yaml

from .containers import SlottedDict

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader  # type: ignore

if TYPE_CHECKING:
    from .anthology import Anthology
    from .collections.volume import Volume


@define
class SIG:
    """A special interest group (SIG).

    Attributes:
        parent: The parent Anthology instance.
        id: The SIG ID, e.g. "sigsem".
        acronym: The SIG's acronym or short name, e.g. "SIGSEM".
        name: The SIG's full name.
        url: A website URL for the SIG.
    """

    parent: Anthology = field(repr=False, eq=False)
    id: str
    acronym: str
    name: str
    url: Optional[str] = field(default=None)
    meetings: list[str | SIGMeeting] = field(factory=list, repr=False)

    def volumes(self) -> Iterator[Volume]:
        for event in self.meetings:
            if isinstance(event, str):
                volume = self.parent.get_volume(event)
                if volume is None:
                    raise KeyError(
                        f"SIG '{self.acronym}' lists volume '{event}' which doesn't exist"
                    )
                yield volume


@define
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


@define
class SIGIndex(SlottedDict[SIG]):
    """Index object through which SIGs and their associated volumes can be accessed.

    Provides dictionary-like functionality mapping SIG IDs to [SIG][acl_anthology.sigs.SIG] objects.

    Attributes:
        parent: The parent Anthology instance to which this index belongs.
        is_data_loaded: A flag indicating whether the venue YAML files have been loaded.
    """

    parent: Anthology = field(repr=False, eq=False)
    is_data_loaded: bool = field(init=False, repr=False, default=False)

    def load(self) -> None:
        """Loads and parses the `sigs/*.yaml` files.

        Raises:
            KeyError: If a mandatory key is missing in a YAML file.
        """
        for yamlpath in self.parent.datadir.glob("yaml/sigs/*.yaml"):
            sig_id = yamlpath.name[:-5]
            with open(yamlpath, "r") as f:
                kwargs = yaml.load(f, Loader=Loader)
            sig = SIG(
                self.parent,
                id=sig_id,
                acronym=kwargs["ShortName"],
                name=kwargs["Name"],
                url=kwargs.get("URL"),
            )
            for year, meetings in ChainMap(*kwargs["Meetings"]).items():
                for meeting in meetings:
                    if isinstance(meeting, str):
                        sig.meetings.append(meeting)
                    else:
                        sig.meetings.append(
                            SIGMeeting(
                                str(year),
                                meeting["Name"],
                                url=meeting.get("URL"),
                            )
                        )
            self.data[sig_id] = sig
        self.is_data_loaded = True
