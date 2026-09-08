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

"""Macro benchmark: how long does it take to serialize `people.json` back
out, given the full, real Anthology data?

Uses this repo's own, full `data/` directory rather than the small fixture
under `tests/data/` (same as `anthology_integration_test.py`), which is why
this also carries the `integration` marker.
"""

import pytest

from acl_anthology import Anthology


@pytest.fixture(scope="module")
def full_anthology():
    anthology = Anthology.from_within_repo()
    anthology.people.load()
    return anthology


@pytest.mark.integration
@pytest.mark.benchmark
# See personindex_build_bench_test.py for why this is ignored: a few papers
# in the real corpus have genuinely ambiguous same-slug co-authors, which
# people.load() warns about and continues past.
@pytest.mark.filterwarnings("ignore::acl_anthology.exceptions.NameSpecResolutionWarning")
def test_people_save(benchmark, full_anthology, tmp_path):
    target = tmp_path / "people.json"
    benchmark.pedantic(
        full_anthology.people.save,
        args=(target,),
        rounds=5,
        iterations=1,
        warmup_rounds=1,
    )
