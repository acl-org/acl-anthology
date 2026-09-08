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

"""CI regression benchmark: is `Collection.load()` getting slower for the
*same* input?

See personindex_build_pinned_bench_test.py for the rationale behind
benchmarking against a fixed-size subset of `data/` instead of the whole
thing; see conftest.py for the shared `pinned_datadir` fixture and
`PINNED_COLLECTIONS` list. See collection_load_bench_test.py for why this
calls `Collection.load()` directly rather than going through one of the
indices.
"""

import pytest

from acl_anthology import Anthology


def load_pinned_collections(datadir):
    anthology = Anthology(datadir=datadir)
    for collection in anthology.collections.values():
        collection.load()
    return anthology


@pytest.mark.integration
@pytest.mark.benchmark
@pytest.mark.pinned
def test_collection_load_pinned(benchmark, pinned_datadir):
    benchmark.pedantic(
        load_pinned_collections,
        args=(pinned_datadir,),
        rounds=10,
        iterations=1,
        warmup_rounds=1,
    )
