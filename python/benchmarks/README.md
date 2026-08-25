# Benchmarks

These are [pytest-benchmark](https://pytest-benchmark.readthedocs.io/) tests.
They are not part of the regular test suite (`testpaths` in `pyproject.toml`
only covers `tests/`), so they only run when you point pytest at this
directory explicitly.

Two kinds of benchmarks live here, distinguished by markers:

- **Micro benchmarks** (`benchmark` marker only) compare small alternative
  implementations against tiny, in-repo fixtures — e.g. "is it faster to
  parse this XML element with `.findtext()` or by iterating its children?".
  They run in a second or two each.
- **Macro benchmarks** (`benchmark` + `integration` markers) time an
  operation against this repo's own, full Anthology data (e.g.
  `PersonIndex.build()`) rather than a small fixture, and can take a while
  to run — that's the point, they're what a future optimization (e.g. an
  on-disk cache for `PersonIndex`) would be measured against.

## Running

```sh
# Fast micro benchmarks only
just benchmark

# Slow macro benchmarks against the full Anthology data
just benchmark-integration

# Equivalent, if you want to pass pytest-benchmark flags directly
uv run pytest benchmarks/ -m "benchmark and not integration" --benchmark-only
uv run pytest benchmarks/ -m "benchmark and integration" --benchmark-only
```

Each parametrized benchmark function shows up as one row per variant in the
result table (min/max/mean/stddev/median/ops), grouped by test name — this is
what replaces richbench's side-by-side comparison tables.

## Tracking results over time

Unlike the richbench scripts these replace, pytest-benchmark can persist
results and diff against them, which is the main tool against these
benchmarks quietly going stale:

```sh
# Save this run under a named baseline
uv run pytest benchmarks/ -m "benchmark and not integration" --benchmark-only \
    --benchmark-autosave

# Compare a later run against it
uv run pytest benchmarks/ -m "benchmark and not integration" --benchmark-only \
    --benchmark-compare=0001 --benchmark-compare-fail=mean:10%
```

Results are written to `.benchmarks/` (gitignored) by default. If you want a
durable baseline to compare future changes against — e.g. before/after
numbers for a specific optimization — save the relevant `.json` file
somewhere it won't be cleaned up, or attach it to the PR/issue discussing the
change, rather than relying on `.benchmarks/` surviving.

## Adding a new benchmark

- Micro: use a `benchmark` fixture-taking test, `@pytest.mark.benchmark`,
  and `@pytest.mark.parametrize` over the variants being compared. See
  `xml_parsing_bench_test.py` for an example.
- Macro (uses the full Anthology data instead of a fixture): also add
  `@pytest.mark.integration`, and prefer
  `benchmark.pedantic(fn, rounds=..., iterations=1)` over the plain
  `benchmark(fn)` fixture call so you control exactly how many times an
  expensive operation runs, rather than letting pytest-benchmark's
  auto-calibration decide. See `personindex_build_bench_test.py`.
