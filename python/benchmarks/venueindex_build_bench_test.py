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

"""Macro benchmark: how long does building the full `VenueIndex` take
against the real, complete Anthology data?

`VenueIndex.build()` assumes `venues.json` has already been read into
memory -- that's what `.load()` does before calling `.build()` -- so this
benchmarks `.load()` as a whole. The json-parsing part is comparatively
tiny; the walk over every volume to assign `item_ids` (i.e. `.build()`
itself) is the actual cost this is meant to track.

Uses this repo's own, full `data/` directory rather than the small fixture
under `tests/data/` (same as `anthology_integration_test.py`), which is why
this also carries the `integration` marker.
"""

import pytest

from acl_anthology import Anthology


def build_venue_index():
    # A fresh Anthology instance each round, so every round genuinely
    # re-parses all XML from scratch rather than benefiting from any
    # in-process state left over from a previous round.
    anthology = Anthology.from_within_repo()
    anthology.venues.load()
    return anthology


@pytest.mark.integration
@pytest.mark.benchmark
def test_venueindex_build(benchmark):
    benchmark.pedantic(
        build_venue_index,
        rounds=5,
        iterations=1,
        warmup_rounds=1,
    )
