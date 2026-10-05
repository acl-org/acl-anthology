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

"""Macro benchmark: `scipy.cluster.hierarchy.DisjointSet` vs. the candidate
`SimilarityGroups` replacement (`acl_anthology.utils.similarity`), as used by
`PersonIndex.similar`.

The add/merge trace used as the benchmark's workload is derived purely from
`PersonIndex`'s *public* data -- every person ID, plus their explicitly
recorded `similar_ids` -- rather than from internals like `_add_name()`'s
same-name/same-slug merging. This deliberately under-counts the merges a
real `PersonIndex.build()` would perform (most merges happen via automatic
name matching, not explicit `similar_ids`), but it's a fair approximation of
the *shape* of the workload (many singleton `add()`s, comparatively few
`merge()`s forming small groups) without coupling this benchmark to
`PersonIndex`'s current choice of union-find implementation -- which is
exactly what's being replaced here, so the benchmark needs to keep working
once it is.

Two things are benchmarked:

- Building the structure from scratch by replaying the trace (what happens
  every time `PersonIndex.build()` runs, i.e. every time an `Anthology` is
  loaded).
- Calling `.subset()` once per known person, mimicking
  `bin/create_hugo_data.py`'s per-person "similar IDs" lookup -- the only
  other place `PersonIndex.similar` is actually queried.

A third, unparametrized benchmark times `SimilarityGroups.remove()` alone:
`DisjointSet` has no equivalent operation (this is the whole reason a
replacement is being considered -- see docstring on `SimilarityGroups`), so
there is nothing to compare it against; it's here to establish that the
operation `DisjointSet` can't do at all is nonetheless cheap.

Note: `test_similarity_groups_subset_all`'s raw per-round timings are noisy
(occasional rounds several times slower than the rest) for *both*
implementations. The fixture keeps a full, real `Anthology` in memory, and
`.subset()` must return a fresh, independently-owned `set` on every one of
its ~70k calls here (true for both `DisjointSet` and `SimilarityGroups`
alike) -- enough new-object churn that an occasional full GC pass ends up
landing inside the timed region and scanning that entire, already-loaded
object graph. It affects both implementations similarly, so it adds noise
to the raw numbers without favoring either side; pass
`--benchmark-disable-gc` for a clean, direct comparison.
`Anthology.load_all()` disables GC by default in real usage anyway
(`disable_gc` in `acl_anthology.config`), so that's also the more realistic
setting.
"""

import pytest
import warnings
from dataclasses import dataclass
from scipy.cluster.hierarchy import DisjointSet

from acl_anthology import Anthology
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.utils.similarity import SimilarityGroups

IMPLEMENTATIONS = [DisjointSet, SimilarityGroups]
IMPLEMENTATION_IDS = ["DisjointSet", "SimilarityGroups"]


@dataclass
class SimilarityWorkload:
    # ("add", pid) / ("merge", pid, other_id) tuples, in call order, derived
    # from the real PersonIndex's public data (see module docstring).
    trace: tuple[tuple[str, ...], ...]
    # Every person ID known to the index after that build, in insertion order.
    person_ids: tuple[str, ...]


@pytest.fixture(scope="session")
def similarity_workload() -> SimilarityWorkload:
    """Builds the real, full `PersonIndex` once, then derives an add/merge
    trace from its public data alone (see module docstring for why).

    Session-scoped: the build is the expensive part (same cost as
    `personindex_build_bench_test.py`), but it's setup, not what's being
    timed -- every benchmark below replays the already-derived trace.
    """
    anthology = Anthology.from_within_repo()
    with warnings.catch_warnings():
        # Same reasoning as personindex_build_bench_test.py: a few papers in
        # the real corpus have genuinely ambiguous same-slug co-authors,
        # which build() warns about and continues past.
        warnings.simplefilter("ignore", category=NameSpecResolutionWarning)
        anthology.people.build(show_progress=False)

    trace: list[tuple[str, ...]] = []
    for pid, person in anthology.people.items():
        trace.append(("add", pid))
        for similar_id in person.similar_ids:
            trace.append(("add", similar_id))
            trace.append(("merge", pid, similar_id))

    return SimilarityWorkload(
        trace=tuple(trace), person_ids=tuple(anthology.people.data.keys())
    )


def build_from_trace(cls, trace):
    structure = cls()
    for op in trace:
        if op[0] == "add":
            structure.add(op[1])
        else:
            structure.merge(op[1], op[2])
    return structure


def query_all_subsets(structure, person_ids):
    return [structure.subset(pid) for pid in person_ids]


@pytest.mark.integration
@pytest.mark.benchmark
@pytest.mark.parametrize("cls", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_similarity_groups_build(benchmark, similarity_workload, cls):
    """Cost of constructing `similar` from scratch, i.e. what every
    `PersonIndex.build()` call pays."""
    benchmark.pedantic(
        build_from_trace,
        args=(cls, similarity_workload.trace),
        rounds=5,
        iterations=1,
        warmup_rounds=1,
    )


@pytest.mark.integration
@pytest.mark.benchmark
@pytest.mark.parametrize("cls", IMPLEMENTATIONS, ids=IMPLEMENTATION_IDS)
def test_similarity_groups_subset_all(benchmark, similarity_workload, cls):
    """Cost of looking up `.subset()` for every person, as
    `bin/create_hugo_data.py` does once per Hugo data build."""
    structure = build_from_trace(cls, similarity_workload.trace)
    benchmark.pedantic(
        query_all_subsets,
        args=(structure, similarity_workload.person_ids),
        rounds=5,
        iterations=1,
        warmup_rounds=1,
    )


@pytest.mark.integration
@pytest.mark.benchmark
def test_similarity_groups_remove_all(benchmark, similarity_workload):
    """Cost of removing every person again, one at a time.

    No `DisjointSet` counterpart exists -- it cannot remove items at all --
    so this just establishes that the operation motivating this whole
    comparison is itself cheap, not a regression risk.
    """

    def remove_all():
        structure = build_from_trace(SimilarityGroups, similarity_workload.trace)
        for pid in similarity_workload.person_ids:
            structure.remove(pid)
        return structure

    benchmark.pedantic(remove_all, rounds=5, iterations=1, warmup_rounds=1)
