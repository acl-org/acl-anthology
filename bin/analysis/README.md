# `bin/analysis`

Scripts that compute statistics and reports over the Anthology. They are
read-only: they load the Anthology (or a `git diff`) and print reports; they do
not modify `data/`.

All scripts locate the Anthology `data/` directory relative to the repository
root by default, so they can be run from anywhere in the repo.

## Scripts

### `count_author_papers.py`

Counts papers per author for a given event, resolving author identities via the
people index. Includes the event's own collection volumes plus colocated
volumes by default (`--main-only` / `--colocated-only` to restrict).

```bash
./bin/analysis/count_author_papers.py --event acl-2026 \
    --output build/acl-2026-author-paper-counts.tsv
```

Use `--prolific-threshold N` to also report how many papers have at least one
author with more than `N` papers in the counted set.

### `ingestion_stats.py`

Computes statistics about an ingestion and prints a Markdown report to STDOUT
(new papers, first-time authors, new `people.yaml` entries, authors-per-paper
histogram, top authors, ORCID coverage). By default it discovers added volumes
via a `git diff` against a base revision. This is run from CI
(`.github/workflows/ingestion-stats.yml`) to post/update a PR comment.

```bash
# Diff against a base revision (as run in CI)
./bin/analysis/ingestion_stats.py --base origin/master

# Or pass volume IDs explicitly
./bin/analysis/ingestion_stats.py 2025.acl-long 2025.acl-short 2025.findings-acl
```

### `name_histogram.py`

Prints a histogram of how many distinct people share each name in the
Anthology.

```bash
./bin/analysis/name_histogram.py
```
