#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 Matt Post <post@cs.jhu.edu>
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

"""
Computes statistics about an ingestion and prints a Markdown report to STDOUT.

The report includes:
  - the number of new papers,
  - the number of new authors (people whose entire publication record is within
    the ingested volumes, i.e. first-time Anthology authors),
  - the number of new entries added to `data/yaml/people.yaml`,
  - a histogram of papers by number of authors,
  - the number of single-author papers written by those new authors,
  - the percentage of paper-author instances (by token) that have an ORCID iD.

By default, the script computes a `git diff` against a base revision (default
`origin/master`) to discover which volumes were *added* and how many new
entries were added to `data/yaml/people.yaml`. This is how it is run from CI:

    ./bin/ingestion_stats.py --base origin/master

The base revision can be changed with `--base`. Volumes can also be passed
explicitly as full volume IDs, which overrides volume detection from the diff
(the people.yaml diff is still computed against the base):

    ./bin/ingestion_stats.py 2025.acl-long 2025.acl-short 2025.findings-acl

The report is intended to be posted as a (single, updatable) PR comment.
"""

import argparse
import re
import subprocess
import sys

from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from acl_anthology import Anthology

# Matches the "+++ b/<path>/<collection>.xml" header line of a git diff.
DIFF_XML_FILE_RE = re.compile(r"^\+\+\+ b/(?:.*/)?([^/]+)\.xml\s*$")
# Matches the "+++ b/<path>" header line of a git diff.
DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.*?)\s*$")
# Matches an *added* "<volume id="...">" line in a git diff.
DIFF_VOLUME_RE = re.compile(r'^\+\s*<volume id="([^"]+)"')
# Matches an *added*, top-level (column-0) person key in people.yaml, e.g.
# "+a-pranav:". Nested keys (names:, orcid:, ...) are indented and won't match.
DIFF_PERSON_RE = re.compile(r"^\+([^\s#][^:]*):\s*$")

PEOPLE_YAML_PATH = "data/yaml/people.yaml"


def get_diff(base: str, datadir: Path) -> List[str]:
    """Computes a git diff of the ingestion against a base revision.

    The diff is limited to the XML collection files and `people.yaml` under the
    given data directory, and compares the merge-base of `base` and `HEAD`
    against `HEAD` (i.e. only changes introduced on the current branch).

    Parameters:
        base: The base git revision to diff against (e.g. "origin/master").
        datadir: Path to the Anthology data directory.

    Returns:
        The diff output as a list of lines.
    """
    repo_root = Path(__file__).resolve().parent.parent
    xml_dir = (datadir / "xml").as_posix()
    people_yaml = (datadir / "yaml" / "people.yaml").as_posix()
    result = subprocess.run(
        ["git", "diff", f"{base}...HEAD", "--", xml_dir, people_yaml],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def added_volumes_from_diff(lines: Iterable[str]) -> List[str]:
    """Extracts the full IDs of volumes added in a git diff.

    Parameters:
        lines: An iterable of git-diff lines.

    Returns:
        A list of full volume IDs (e.g. "2025.acl-long"), in order of appearance.
    """
    volume_ids: List[str] = []
    collection_id: Optional[str] = None
    for line in lines:
        file_match = DIFF_XML_FILE_RE.match(line)
        if file_match:
            collection_id = file_match.group(1)
            continue
        volume_match = DIFF_VOLUME_RE.match(line)
        if volume_match and collection_id is not None:
            volume_ids.append(f"{collection_id}-{volume_match.group(1)}")
    return volume_ids


def count_new_people_from_diff(lines: Iterable[str]) -> int:
    """Counts the number of new entries added to `people.yaml` in a git diff.

    Each new person is a top-level (column-0) key in `people.yaml`; this counts
    the added lines that introduce such a key, within the `people.yaml` section
    of the diff.

    Parameters:
        lines: An iterable of git-diff lines.

    Returns:
        The number of new person entries.
    """
    in_people_yaml = False
    count = 0
    for line in lines:
        file_match = DIFF_FILE_RE.match(line)
        if file_match:
            in_people_yaml = file_match.group(1) == PEOPLE_YAML_PATH
            continue
        if in_people_yaml and DIFF_PERSON_RE.match(line):
            count += 1
    return count


def compute_stats(
    anthology: Anthology, volume_ids: List[str], num_new_people_entries: int
) -> Dict:
    """Computes ingestion statistics over the given set of volumes.

    Parameters:
        anthology: A loaded Anthology instance.
        volume_ids: A list of full volume IDs to analyze.
        num_new_people_entries: The number of new entries added to people.yaml.

    Returns:
        A dictionary of computed statistics.
    """
    volume_set: Set[str] = set(volume_ids)

    found_volume_ids: List[str] = []
    papers = []
    for volume_id in volume_ids:
        volume = anthology.get_volume(volume_id)
        if volume is None:
            print(f"Volume {volume_id} not found in the Anthology.", file=sys.stderr)
            continue
        found_volume_ids.append(volume_id)
        for paper in volume.papers():
            if paper.is_frontmatter or paper.is_deleted:
                continue
            papers.append(paper)

    # Histogram of papers by number of authors.
    author_count_hist = Counter(len(paper.authors) for paper in papers)

    # ORCID coverage by token: each paper-author instance counts once.
    num_author_instances = 0
    num_author_instances_with_orcid = 0
    for paper in papers:
        for author in paper.authors:
            num_author_instances += 1
            if author.orcid is not None:
                num_author_instances_with_orcid += 1
    pct_author_instances_with_orcid = (
        100.0 * num_author_instances_with_orcid / num_author_instances
        if num_author_instances
        else 0.0
    )

    # People who authored a paper in the ingested set, and the papers they have
    # there. A person is "new" if *all* of their Anthology papers fall within the
    # ingested set (i.e. they are first-time authors).
    people_papers: Dict = defaultdict(list)
    for paper in papers:
        for author in paper.authors:
            person = author.resolve()
            people_papers[person].append(paper)

    def is_new_person(person) -> bool:
        return all(paper.parent.full_id in volume_set for paper in person.papers())

    new_people = {person for person in people_papers if is_new_person(person)}

    # Single-author papers whose sole author is a new person.
    single_author_new = [
        paper
        for paper in papers
        if len(paper.authors) == 1 and paper.authors[0].resolve() in new_people
    ]

    return {
        "volume_ids": found_volume_ids,
        "num_papers": len(papers),
        "num_authors": len(people_papers),
        "num_new_authors": len(new_people),
        "num_new_people_entries": num_new_people_entries,
        "num_single_author_new": len(single_author_new),
        "num_author_instances": num_author_instances,
        "num_author_instances_with_orcid": num_author_instances_with_orcid,
        "pct_author_instances_with_orcid": pct_author_instances_with_orcid,
        "author_count_hist": author_count_hist,
    }


def format_report(stats: Dict) -> str:
    """Formats the computed statistics as a Markdown report."""
    lines: List[str] = []
    lines.append("## 📊 Ingestion statistics")
    lines.append("")

    volume_ids = stats["volume_ids"]
    if not volume_ids:
        lines.append(
            "No ingested volumes were detected, so no statistics could be computed."
        )
        lines.append("")
        lines.append(
            f"New `people.yaml` entries: **{stats['num_new_people_entries']}**"
        )
        return "\n".join(lines)

    lines.append(f"Analyzed **{len(volume_ids)}** volume(s): " + ", ".join(
        f"`{vid}`" for vid in volume_ids
    ))
    lines.append("")

    lines.append("| Metric | Count |")
    lines.append("| --- | ---: |")
    lines.append(f"| New papers | {stats['num_papers']} |")
    lines.append(f"| Distinct authors | {stats['num_authors']} |")
    lines.append(f"| New authors (first time in the Anthology) | {stats['num_new_authors']} |")
    lines.append(
        f"| New `people.yaml` entries | {stats['num_new_people_entries']} |"
    )
    lines.append(
        f"| Single-author papers by new authors | {stats['num_single_author_new']} |"
    )
    lines.append(
        "| Paper-author instances with ORCID iD | "
        f"{stats['num_author_instances_with_orcid']} / {stats['num_author_instances']} "
        f"({stats['pct_author_instances_with_orcid']:.1f}%) |"
    )
    lines.append("")

    lines.append("### Papers by number of authors")
    lines.append("")
    hist = stats["author_count_hist"]
    author_counts = sorted(hist)
    if author_counts:
        # Render as a Mermaid bar chart, which GitHub renders inline in comments.
        x_axis = ", ".join(str(n) for n in author_counts)
        bar_values = ", ".join(str(hist[n]) for n in author_counts)
        max_papers = max(hist.values())
        lines.append("```mermaid")
        lines.append("xychart-beta")
        lines.append('    title "Papers by number of authors"')
        lines.append(f'    x-axis "Number of authors" [{x_axis}]')
        lines.append(f'    y-axis "Papers" 0 --> {max_papers}')
        lines.append(f"    bar [{bar_values}]")
        lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "volumes",
        nargs="*",
        help="Full volume IDs to analyze (e.g. 2025.acl-long). "
        "If omitted, volumes added in the git diff against --base are used.",
    )
    parser.add_argument(
        "--base",
        default="origin/master",
        help="Base git revision to diff against. Default: %(default)s.",
    )
    parser.add_argument(
        "--datadir",
        type=Path,
        default=Path(__file__).parent / ".." / "data",
        help="Path to the Anthology data directory. Default: %(default)s.",
    )
    args = parser.parse_args()

    diff_lines = get_diff(args.base, args.datadir)
    num_new_people_entries = count_new_people_from_diff(diff_lines)

    volume_ids = args.volumes or added_volumes_from_diff(diff_lines)

    anthology = Anthology(datadir=args.datadir)
    stats = compute_stats(anthology, volume_ids, num_new_people_entries)
    print(format_report(stats))


if __name__ == "__main__":
    main()
