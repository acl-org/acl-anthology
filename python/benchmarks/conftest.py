# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Shared fixtures for `*_pinned_bench_test.py` benchmarks. See those files'
module docstrings for why a pinned, fixed-size subset of `data/` exists at
all: so their timing stays directly comparable commit-to-commit, unlike the
macro benchmarks against the full corpus, which are expected to drift as
more data is ingested.
"""

import pytest
from git import Repo
from pathlib import Path

# A fixed, deliberately chosen set of real collection IDs, spanning old and
# new ID schemes and a range of sizes (a couple of large modern conferences,
# some mid-sized ones, a small workshop, an old journal, and a tiny historical
# collection) for a representative mix. This list should only change when we
# deliberately decide to -- e.g. if it stops being representative -- never as
# a side effect of new data being ingested.
PINNED_COLLECTIONS = (
    "2022.acl",
    "2022.emnlp",
    "2023.eacl",
    "C16",
    "P19",
    "L06",
    "Q13",
    "J93",
    "2021.hcinlp",
    "1957.earlymt",
)


@pytest.fixture(scope="session")
def pinned_datadir(tmp_path_factory):
    """A datadir containing only `PINNED_COLLECTIONS`' XML files, symlinked
    out of the real `data/` directory (not copied, so it always reflects
    their current, real content), plus everything else an `Anthology`
    pointed at it might need (`json/people.json`, `json/venues.json`,
    `json/sigs.json`, `xml/schema.rnc`).

    Session-scoped and shared across all pinned benchmarks, since it's
    read-only and rebuilding it per test module would be pure overhead.
    """
    real_datadir = (
        Path(Repo(__file__, search_parent_directories=True).working_dir) / "data"
    )
    pinned_dir = tmp_path_factory.mktemp("pinned-anthology")

    (pinned_dir / "xml").mkdir()
    (pinned_dir / "xml" / "schema.rnc").symlink_to(real_datadir / "xml" / "schema.rnc")
    for collection_id in PINNED_COLLECTIONS:
        filename = f"{collection_id}.xml"
        (pinned_dir / "xml" / filename).symlink_to(real_datadir / "xml" / filename)

    (pinned_dir / "json").mkdir()
    for filename in ("people.json", "venues.json", "sigs.json"):
        (pinned_dir / "json" / filename).symlink_to(real_datadir / "json" / filename)

    return pinned_dir
