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

from attr import define, field
from typing import Optional


@define
class Name:
    """A person's name.

    Attributes:
        first (Optional[str]): First name part. Can be given as `None` for people who
            only have a single name, but cannot be omitted.
        last (str): Last name part.
        id (Optional[str]): Unique ID for the individual that this name refers to.
            Defaults to `None`.
        affiliation (Optional[str]): Professional affiliation.  Defaults to `None`.
    """

    first: Optional[str]
    last: str
    id: Optional[str] = field(default=None)
    affiliation: Optional[str] = field(default=None)

    @property
    def full(self) -> str:
        if not self.first:
            return self.last
        return f"{self.first} {self.last}"
