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

from acl_anthology import Anthology

# See conftest.py for `pinned_datadir` (the fixed-size subset of `data/`
# shared by all `*_pinned_bench_test.py` files) and `PINNED_COLLECTIONS`.


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
