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

"""Macro benchmark: how long does building the full `PersonIndex` take
against the real, complete Anthology data?

`PersonIndex.build()` currently has to parse every XML collection file to
resolve author/editor namespecs, which is the cost a future on-disk cache
for the index would aim to avoid. This benchmark exists to give that work a
concrete baseline to compare against.

Uses this repo's own, full `data/` directory rather than the small fixture
under `tests/data/` (same as `anthology_integration_test.py`), which is why
this also carries the `integration` marker.
"""

import pytest

from acl_anthology import Anthology


def build_person_index():
    # A fresh Anthology instance each round, so every round genuinely
    # re-parses all XML from scratch rather than benefiting from any
    # in-process state left over from a previous round.
    anthology = Anthology.from_within_repo()
    anthology.people.build(show_progress=False)
    return anthology


@pytest.mark.integration
@pytest.mark.benchmark
# The real corpus has a few papers with two authors sharing the same
# unverified name slug (i.e. genuinely ambiguous, not a bug); build() warns
# about these and continues, but the global `filterwarnings = ["error"]` in
# pyproject.toml would otherwise turn that warning into a fatal exception.
@pytest.mark.filterwarnings("ignore::acl_anthology.exceptions.NameSpecResolutionWarning")
def test_personindex_build(benchmark):
    benchmark.pedantic(
        build_person_index,
        rounds=5,
        iterations=1,
        warmup_rounds=1,
    )
