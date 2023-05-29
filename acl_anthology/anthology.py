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

from pathlib import Path
from .papers import PaperIndex


class Anthology:
    def __init__(self, datadir):
        if not Path(datadir).is_dir():
            raise ValueError(f"Not a directory: {datadir}")  # TODO exception type

        self._datadir = datadir
        self.papers = PaperIndex(self)

    @property
    def datadir(self):
        return self._datadir
