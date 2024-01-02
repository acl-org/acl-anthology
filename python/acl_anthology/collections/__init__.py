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

from .index import CollectionIndex
from .collection import Collection
from .eventindex import EventIndex
from .event import Event, Talk
from .volume import Volume
from .types import VolumeType
from .paper import Paper


__all__ = [
    "Collection",
    "CollectionIndex",
    "Event",
    "EventIndex",
    "Paper",
    "Talk",
    "Volume",
    "VolumeType",
]
