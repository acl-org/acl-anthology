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


def test_name_instantiation():
    # Tests that common ways to instantiate a name should work
    n0 = Name("Doe")
    assert n0.first is None
    assert n0.last == "Doe"
    n1 = Name("Doe", "John")
    n2 = Name(first="John", last="Doe")
    assert n1.first == "John"
    assert n1.last == "Doe"
    assert n1 == n2
    n3 = Name("Doe", "John", "john-doe-42", affiliation="University of Someplace")
    assert n3.id == "john-doe-42"
    assert n3.affiliation == "University of Someplace"
