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

"""Macro benchmark: how long does parsing every XML collection file take
against the real, complete Anthology data?

This calls `Collection.load()` directly, without touching `PersonIndex`,
`VenueIndex`, or `SIGIndex` at all -- it isolates the raw cost of XML
parsing and Volume/Paper construction from the extra resolution logic those
indices layer on top. Comparing this benchmark's number against theirs
shows how much of their cost is "parsing XML" versus "resolving against
JSON metadata".

Uses this repo's own, full `data/` directory rather than the small fixture
under `tests/data/` (same as `anthology_integration_test.py`), which is why
this also carries the `integration` marker.
"""

import pytest

from acl_anthology import Anthology


def load_all_collections():
    # A fresh Anthology instance each round, so every round genuinely
    # re-parses all XML from scratch rather than benefiting from any
    # in-process state left over from a previous round.
    anthology = Anthology.from_within_repo()
    for collection in anthology.collections.values():
        collection.load()
    return anthology


@pytest.mark.integration
@pytest.mark.benchmark
def test_collection_load(benchmark):
    benchmark.pedantic(
        load_all_collections,
        rounds=5,
        iterations=1,
        warmup_rounds=1,
    )
