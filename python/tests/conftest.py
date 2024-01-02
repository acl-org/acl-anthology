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

import logging
import os
import pytest
from pathlib import Path

pytest.register_assert_rewrite("acl_anthology.utils.xml")

from acl_anthology import Anthology  # noqa: E402

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def datadir():
    return Path(f"{SCRIPTDIR}/toy_anthology")


class AnthologyStub:
    datadir = Path(f"{SCRIPTDIR}/toy_anthology")


@pytest.fixture
def anthology(datadir, caplog):
    logging.captureWarnings(True)
    anthology = Anthology(datadir)
    yield anthology
    for when in ("setup", "call"):
        warnings = [
            x.message for x in caplog.get_records(when) if x.levelno == logging.WARNING
        ]
        if warnings:
            pytest.fail(f"Tests on toy_anthology logged warning(s): {warnings}")


@pytest.fixture
def anthology_stub():
    return AnthologyStub()
