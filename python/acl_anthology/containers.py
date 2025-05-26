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

import sys
from attrs import define, field
from collections.abc import ItemsView, KeysView, ValuesView
from copy import copy
from typing import TypeVar, Generic, Iterator, Optional

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

T = TypeVar("T")
U = TypeVar("U")


def dict_type(x: dict[str, T]) -> str:
    if not x:
        return ""
    value = next(iter(x.values()))
    return f"{value.__class__.__name__} "


@define
class SlottedDict(Generic[T]):
    """A generic slotted class for dictionary-like behavior.

    This class implements all [functions that `dict` objects](https://docs.python.org/3/library/stdtypes.html#mapping-types-dict) provide, automatically loading underlying data sources if required, then "forwarding" the functions to the wrapped `self.data` dictionary.

    Keys of this dictionary are always strings (e.g., paper IDs or person IDs), while the type of values depends on the subclass.

    Attributes:
        data: The wrapped data dictionary.
        is_data_loaded: Flag that defaults to True. Subclasses can set this to False to indicate that [`self.load()`][acl_anthology.containers.SlottedDict.load] must be called before any data can be accessed; in that case, they also have to implement the `load` function.
    """

    # TODO: We would probably like to take is_data_loaded into account, but
    # that's not really possible
    data: dict[str, T] = field(
        init=False,
        repr=lambda x: f"<dict of {len(x)} {dict_type(x)}item{'' if len(x) == 1 else 's'}>",
        factory=dict,
    )
    is_data_loaded: bool = field(init=False, repr=False, default=True)

    def __contains__(self, key: str) -> bool:
        if not self.is_data_loaded:
            self.load()
        return key in self.data

    def __iter__(self) -> Iterator[str]:
        if not self.is_data_loaded:
            self.load()
        return self.data.__iter__()

    def __len__(self) -> int:
        if not self.is_data_loaded:
            self.load()
        return len(self.data)

    def __getitem__(self, key: str) -> T:
        if not self.is_data_loaded:
            self.load()
        return self.data[key]

    def __delitem__(self, key: str) -> None:
        if not self.is_data_loaded:
            self.load()
        del self.data[key]

    def __setitem__(self, key: str, value: T) -> None:
        if not self.is_data_loaded:
            self.load()
        self.data[key] = value

    def __ior__(self, other: Self) -> Self:
        if not self.is_data_loaded:
            self.load()
        if not other.is_data_loaded:
            other.load()
        self.data |= other.data
        return self

    def __or__(self, other: Self) -> Self:
        if not self.is_data_loaded:
            self.load()
        if not other.is_data_loaded:
            other.load()
        new_instance = copy(self)
        new_instance.data = self.data | other.data
        return new_instance

    def __reversed__(self) -> Iterator[str]:
        if not self.is_data_loaded:
            self.load()
        return reversed(self.data)

    def clear(self) -> None:
        self.is_data_loaded = True  # No need to load data if it's cleared
        self.data.clear()

    def copy(self) -> Self:
        if not self.is_data_loaded:
            self.load()
        return copy(self)

    def get(self, key: str, default: Optional[U] = None) -> T | U | None:
        if not self.is_data_loaded:
            self.load()
        return self.data.get(key, default)

    def items(self) -> ItemsView[str, T]:
        if not self.is_data_loaded:
            self.load()
        return self.data.items()

    def keys(self) -> KeysView[str]:
        if not self.is_data_loaded:
            self.load()
        return self.data.keys()

    def pop(self, key: str, default: Optional[U] = None) -> T | U | None:
        if not self.is_data_loaded:
            self.load()
        return self.data.pop(key, default)

    def popitem(self) -> tuple[str, T]:
        if not self.is_data_loaded:
            self.load()
        return self.data.popitem()

    def setdefault(self, key: str, default: T) -> T:
        if not self.is_data_loaded:
            self.load()
        if key in self.data:
            return self.data[key]
        return self.data.setdefault(key, default)

    def update(self, other: Self) -> None:
        if not self.is_data_loaded:
            self.load()
        if not other.is_data_loaded:
            other.load()
        self.data.update(other.data)

    def values(self) -> ValuesView[T]:
        if not self.is_data_loaded:
            self.load()
        return self.data.values()

    def load(self) -> None:
        """Load the data.  Must be implemented by all inheriting classes _if_ they set `is_data_loaded=False`.

        Raises:
            NotImplementedError:
        """
        raise NotImplementedError()
