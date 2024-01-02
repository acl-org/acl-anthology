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
from collections import ChainMap, defaultdict
from os import PathLike
from pathlib import Path
from typing import Iterator, Optional, TYPE_CHECKING
import yaml

from .containers import SlottedDict
from .utils import ids

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:  # pragma: no cover
    from yaml import Loader, Dumper  # type: ignore

if TYPE_CHECKING:
    from .anthology import Anthology
    from .collections.volume import Volume


@define
class SIG:
    """A special interest group (SIG).

    Attributes:
        parent: The parent SIGIndex instance.
        id: The SIG ID, e.g. "sigsem".
        acronym: The SIG's acronym or short name, e.g. "SIGSEM".
        name: The SIG's full name.
        path: The path of the YAML file representing this SIG.
        url: A website URL for the SIG.
    """

    parent: SIGIndex = field(repr=False, eq=False)
    id: str
    acronym: str
    name: str
    path: Path
    url: Optional[str] = field(default=None)
    meetings: list[str | SIGMeeting] = field(factory=list, repr=False)

    @property
    def root(self) -> Anthology:
        """The Anthology instance to which this object belongs."""
        return self.parent.parent

    def get_meetings_by_year(self) -> dict[str, list[str | SIGMeeting]]:
        """Get all associated meetings, grouped by year.

        Returns:
            A dictionary where keys are strings representing years, and values are meetings of this SIG in that year.
        """
        by_year = defaultdict(list)
        for meeting in self.meetings:
            year = ids.infer_year(meeting) if isinstance(meeting, str) else meeting.year
            by_year[year].append(meeting)
        return by_year

    def volumes(self) -> Iterator[Volume]:
        """Iterate over all volumes that are associated with this SIG."""
        for meeting in self.meetings:
            if isinstance(meeting, str):
                volume = self.root.get_volume(meeting)
                if volume is None:
                    raise KeyError(
                        f"SIG '{self.acronym}' lists volume '{meeting}' which doesn't exist"
                    )
                yield volume

    @classmethod
    def load_from_yaml(cls, parent: SIGIndex, path: PathLike[str]) -> SIG:
        """Instantiates a SIG from its YAML file.

        Arguments:
            parent: The parent SIGIndex instance.
            path: The YAML file defining this SIG.

        Warning:
            Currently assumes that files are named `{sig_id}.yaml`.
        """
        path = Path(path)
        sig_id = path.name[:-5]
        with open(path, "r", encoding="utf-8") as f:
            kwargs = yaml.load(f, Loader=Loader)
        sig = cls(
            parent,
            id=sig_id,
            acronym=kwargs["ShortName"],
            name=kwargs["Name"],
            path=path,
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
        return sig

    def save(self, path: Optional[PathLike[str]] = None) -> None:
        """Saves this SIG as a YAML file.

        Arguments:
            path: The filename to save to. If None, defaults to `self.path`.
        """
        if path is None:
            path = self.path
        values = {
            "Name": self.name,
            "ShortName": self.acronym,
        }
        values_meetings = []
        if self.url:
            values["URL"] = self.url
        if self.meetings:
            meetings_by_year = sorted(
                self.get_meetings_by_year().items(), key=lambda x: x[0], reverse=True
            )
            for year, meetings in meetings_by_year:
                year_meetings = []
                for meeting in meetings:
                    if isinstance(meeting, str):
                        value: str | dict[str, str] = meeting
                    else:
                        value = {"Name": meeting.name}
                        if meeting.url is not None:
                            value["URL"] = meeting.url
                    year_meetings.append(value)
                values_meetings.append({int(year): year_meetings})
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(values, f, Dumper=Dumper, width=999)
            if values_meetings:
                yaml.dump({"Meetings": values_meetings}, f, Dumper=Dumper, width=999)


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
        if self.is_data_loaded:
            return
        for yamlpath in self.parent.datadir.glob("yaml/sigs/*.yaml"):
            sig = SIG.load_from_yaml(self, yamlpath)
            self.data[sig.id] = sig
        self.is_data_loaded = True
