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

import os
from copy import deepcopy
from lxml import etree
from pathlib import Path

REPEAT = 1_000
SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))
XMLFILE = Path(f"{SCRIPTDIR}/../tests/toy_anthology/xml/2022.acl.xml")

# An example from 2022.acl.xml
tree = etree.parse(XMLFILE)
abstract = tree.find(".//paper[@id='174'].abstract")


def element_deepcopy():
    for _ in range(REPEAT):
        deepcopy(abstract)


def element_tostring():
    for _ in range(REPEAT):
        etree.tostring(abstract)


__benchmarks__ = [
    (
        element_deepcopy,
        element_tostring,
        "XML: deepcopy <abstract> vs. convert to string",
    ),
]
