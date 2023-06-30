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

"""Classes and functions for text markup manipulation."""

from __future__ import annotations

import lxml
from attrs import define, field
from copy import deepcopy


@define
class MarkupText:
    """Text with optional markup.

    This class **should not be instantiated directly,** but only through
    its class method constructors.  This is because the internal
    representation of the markup text may change at any time.
    """

    _content: lxml.etree._Element = field()

    @classmethod
    def from_xml(cls, element: lxml.etree._Element) -> MarkupText:
        return cls(deepcopy(element))
