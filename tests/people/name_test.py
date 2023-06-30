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

from acl_anthology.people import Name
import pytest


def test_name_firstlast():
    n1 = Name("John", "Doe")
    assert n1.first == "John"
    assert n1.last == "Doe"
    assert n1.full == "John Doe"
    n2 = Name(last="Doe", first="John")
    assert n1 == n2
    assert n2.full == "John Doe"


def test_name_onlylast():
    with pytest.raises(TypeError):
        # This is error-prone, so it should fail
        Name("Mausam")
    # Empty first name needs to be given explicitly
    n = Name(None, "Mausam")
    assert n.first is None
    assert n.last == "Mausam"
    assert n.full == "Mausam"


def test_name_with_affiliation():
    n1 = Name("John", "Doe")
    n2 = Name("John", "Doe", affiliation="University of Someplace")
    assert n1 != n2
    assert n1.full == n2.full
    assert n1.affiliation is None
    assert n2.affiliation == "University of Someplace"


def test_name_with_id():
    n1 = Name("John", "Doe")
    n2 = Name("John", "Doe", "john-doe-42")
    assert n1 != n2
    assert n1.full == n2.full
    assert n1.id is None
    assert n2.id == "john-doe-42"
