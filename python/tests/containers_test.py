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

import pytest

from attrs import define, field
from acl_anthology.containers import dict_type, SlottedDict


class BlankContainer(SlottedDict[str]):
    pass


@define
class DemoContainer(SlottedDict[int]):
    is_data_loaded: bool = field(init=False, repr=False, default=False)

    def load(self) -> None:
        self.data["A"] = 1
        self.data["B"] = 2
        self.is_data_loaded = True


@define
class OtherContainer(SlottedDict[int]):
    is_data_loaded: bool = field(init=False, repr=False, default=False)

    def load(self) -> None:
        self.data["B"] = 4
        self.data["C"] = 5
        self.is_data_loaded = True


@pytest.fixture
def demo():
    return DemoContainer()


@pytest.fixture
def other():
    return OtherContainer()


def test_blank_container():
    blank = BlankContainer()
    assert blank.is_data_loaded
    with pytest.raises(NotImplementedError):
        blank.load()


def test_container_load(demo):
    assert not demo.is_data_loaded
    demo.load()
    assert demo.is_data_loaded


def test_container_contains(demo):
    assert "A" in demo
    assert "B" in demo
    assert "C" not in demo


def test_container_iter(demo):
    keys = {x for x in demo}
    assert keys == set(("A", "B"))


def test_container_len(demo):
    assert len(demo) == 2


def test_container_getitem(demo):
    assert demo["A"] == 1
    assert demo["B"] == 2


def test_container_delitem(demo):
    del demo["A"]
    assert "A" not in demo
    assert "B" in demo


def test_container_ior(demo, other):
    demo |= other
    assert demo.data == {"A": 1, "B": 4, "C": 5}


def test_container_or(demo, other):
    third = demo | other
    assert third.data == {"A": 1, "B": 4, "C": 5}


def test_container_clear(demo):
    demo.clear()
    assert demo.data == {}


def test_container_copy(demo):
    other = demo.copy()
    assert other.data == demo.data


def test_container_get(demo):
    assert demo.get("A") == 1
    assert demo.get("B") == 2
    assert demo.get("C") is None
    assert demo.get("D", 42) == 42


def test_container_items(demo):
    result = {x for x in demo.items()}
    assert result == {("A", 1), ("B", 2)}


def test_container_keys(demo):
    keys = {x for x in demo.keys()}
    assert keys == set(("A", "B"))


def test_container_pop(demo):
    assert "A" in demo
    assert demo.pop("A") == 1
    assert "A" not in demo
    assert demo.pop("C") is None
    assert demo.pop("D", 42) == 42


def test_container_popitem(demo):
    assert demo.popitem() == ("B", 2)
    assert demo.popitem() == ("A", 1)


def test_container_reversed(demo):
    result = reversed(demo)
    assert list(result) == ["B", "A"]


def test_container_setdefault(demo):
    assert demo.setdefault("C", 3) == 3
    assert "C" in demo
    assert demo.setdefault("A", 3) == 1
    with pytest.raises(TypeError):
        assert demo.setdefault("X")
    assert "X" not in demo


def test_container_update(demo, other):
    demo.update(other)
    assert demo.data == {"A": 1, "B": 4, "C": 5}


def test_container_values(demo):
    values = {x for x in demo.values()}
    assert values == set((1, 2))


def test_dict_type(demo):
    assert dict_type(demo) == "int "
    blank = BlankContainer()
    assert dict_type(blank) == ""  # not determinable
