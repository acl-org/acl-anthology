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

"""CI regression benchmark: is `PersonIndex.build()` getting slower for the
*same* input?

`personindex_build_bench_test.py` times a build against the entire, real
`data/` directory, which grows over time as new volumes get ingested — so
its number is expected to increase from one month to the next regardless of
whether `python/` code changed at all. That makes it useless as a
before/after signal for automated CI regression detection: a "regression"
there might just mean someone added a new proceedings volume.

This benchmark instead builds the `PersonIndex` over a fixed, hardcoded
subset of real collections (symlinked out of the real `data/` directory, not
copied, so it always reflects their current, real content). Because the
input is pinned, its wall-clock time should stay flat commit-to-commit
unless `python/` itself got slower or faster -- which is exactly the signal
a tool like github-action-benchmark should alert on.
"""

import pytest
from git import Repo
from pathlib import Path

from acl_anthology import Anthology

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


@pytest.fixture(scope="module")
def pinned_datadir(tmp_path_factory):
    """A datadir containing only `PINNED_COLLECTIONS`' XML files, symlinked
    out of the real `data/` directory, plus everything else `PersonIndex`
    needs (`json/people.json`, `xml/schema.rnc`)."""
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
    (pinned_dir / "json" / "people.json").symlink_to(
        real_datadir / "json" / "people.json"
    )

    return pinned_dir


def build_person_index(datadir):
    # A fresh Anthology instance each round, so every round genuinely
    # re-parses all XML from scratch rather than benefiting from any
    # in-process state left over from a previous round.
    anthology = Anthology(datadir=datadir)
    anthology.people.build(show_progress=False)
    return anthology


@pytest.mark.integration
@pytest.mark.benchmark
@pytest.mark.pinned
# Same reasoning as personindex_build_bench_test.py: a couple of pinned
# collections have genuinely ambiguous same-slug co-authors on one paper.
@pytest.mark.filterwarnings("ignore::acl_anthology.exceptions.NameSpecResolutionWarning")
def test_personindex_build_pinned(benchmark, pinned_datadir):
    benchmark.pedantic(
        build_person_index,
        args=(pinned_datadir,),
        rounds=10,
        iterations=1,
        warmup_rounds=1,
    )
