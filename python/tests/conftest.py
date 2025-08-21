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

import difflib
import itertools as it
import pytest
import reprlib
from unittest.mock import Mock

pytest.register_assert_rewrite("acl_anthology.utils.xml")

from acl_anthology import Anthology, config  # noqa: E402

# Disable caching by default when testing
config.disable_caching = True


class AnthologyStub:
    datadir = None
    people = Mock()


@pytest.fixture
def anthology(shared_datadir):
    anthology = Anthology(shared_datadir / "anthology")
    yield anthology


@pytest.fixture
def anthology_stub(shared_datadir):
    stub = AnthologyStub()
    stub.datadir = shared_datadir / "anthology"
    return stub


def pytest_assertrepr_compare(op, left, right):
    # Use difflib output to show diff between lists
    if isinstance(left, list) and isinstance(right, list) and op == "==":
        short = reprlib.Repr(maxlist=1, maxlevel=1)
        return [
            x
            for x in it.chain(
                [f"{short.repr(left)} == {short.repr(right)}"],
                difflib.unified_diff(
                    left, right, fromfile="left", tofile="right", n=1, lineterm=""
                ),
            )
        ]
