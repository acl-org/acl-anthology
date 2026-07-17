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

"""Match author affiliations against ROR and cache coordinates + sector.

Reads affiliation strings from the Anthology's ``<author>`` tags and matches them
against the Research Organization Registry (ROR, https://ror.org). ROR is a free,
CC0 registry that provides, for each organization, its name variants, a
geolocation, and an organization type. Matching runs entirely OFFLINE against a
downloaded data dump, so there are no per-institution network calls and no rate
limits (the only download is the ~34 MB ROR dump itself, cached under
``~/.cache/acl-anthology/ror/``).

Results are written to ``data/geo/affiliation_geocache.json``. The website build
(``create_hugo_data.py``) only ever READS that file. Manual corrections live in
``data/geo/affiliation_overrides.json`` and take precedence. Re-run after new
ingestions to extend coverage:

    bin/geocode_affiliations.py --min-count 5

Unmatched affiliations are cached as ``null`` so they are not retried needlessly.
"""

import argparse
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

from acl_anthology import Anthology

REPO = Path(__file__).resolve().parent.parent
CACHE_PATH = REPO / "data" / "geo" / "affiliation_geocache.json"
ROR_CACHE_DIR = Path.home() / ".cache" / "acl-anthology" / "ror"
# Zenodo "concept" record that always resolves to the latest ROR data dump.
ZENODO_CONCEPT_URL = "https://zenodo.org/api/records/6347574"
USER_AGENT = (
    "acl-anthology-affiliation-map/2.0 (+https://github.com/acl-org/acl-anthology)"
)

# ROR organization types (an org may have several) mapped, in priority order, to
# the coarse sectors we colour on the map.
SECTOR_BY_TYPE = [
    ("education", "academic"),
    ("company", "industry"),
    ("government", "government"),
]

# Affiliation strings that are never geocodable; skip them.
JUNK = {
    "na",
    "n/a",
    "none",
    "null",
    "-",
    "--",
    "unaffiliated",
    "independent",
    "independent researcher",
    "independent scholar",
    "independent researcher.",
    "freelance",
    "retired",
}


def normalize(raw: str) -> str:
    """Collapse whitespace. This is the cache key shared with the site build."""
    return " ".join(raw.split())


def match_key(value: str) -> str:
    """Aggressively normalize a name for matching (accents, case, punctuation)."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-zA-Z]+", " ", value).strip().lower()


def is_junk(norm: str) -> bool:
    low = norm.casefold()
    return len(norm) < 3 or low in JUNK or norm.replace(".", "").isdigit()


def sector_for(types) -> str:
    for ror_type, sector in SECTOR_BY_TYPE:
        if ror_type in types:
            return sector
    return "other"


def resolve_ror_dump(refresh: bool = False) -> Path:
    """Return a path to the ROR data dump JSON, downloading it if necessary."""
    ROR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(ROR_CACHE_DIR.glob("*ror-data*.json"))
    if existing and not refresh:
        return existing[-1]

    print("Resolving latest ROR data dump from Zenodo...", file=sys.stderr)
    with urlopen(Request(ZENODO_CONCEPT_URL, headers={"User-Agent": USER_AGENT})) as r:
        meta = json.load(r)
    zip_file = next(f for f in meta["files"] if f["key"].endswith(".zip"))
    url = zip_file["links"]["self"]
    zip_path = ROR_CACHE_DIR / zip_file["key"]
    print(
        f"Downloading {zip_file['key']} ({zip_file['size'] / 1e6:.0f} MB)...",
        file=sys.stderr,
    )
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT})) as response:
        zip_path.write_bytes(response.read())
    with zipfile.ZipFile(zip_path) as archive:
        json_names = [n for n in archive.namelist() if n.endswith(".json")]
        # Prefer the v2-schema file when a dump ships both v1 and v2.
        target = next((n for n in json_names if "schema_v2" in n), None) or next(
            (n for n in json_names if "v2" in n), json_names[0]
        )
        archive.extract(target, ROR_CACHE_DIR)
    zip_path.unlink()
    return ROR_CACHE_DIR / target


def build_ror_index(dump_path: Path):
    """Build {normalized name -> org info} indexes from the ROR dump.

    Full names (display/label/alias) and acronyms are indexed separately so that
    full names win. Names shared by more than one organization are dropped, to
    avoid placing an affiliation at the wrong institution.
    """
    print(f"Loading ROR dump: {dump_path.name}", file=sys.stderr)
    records = json.loads(dump_path.read_text(encoding="utf-8"))
    full_index: dict = {}
    acronym_index: dict = {}
    for record in records:
        locations = record.get("locations") or []
        geo = locations[0].get("geonames_details") if locations else None
        if not geo or "lat" not in geo or "lng" not in geo:
            continue
        info = {
            "lat": round(float(geo["lat"]), 5),
            "lon": round(float(geo["lng"]), 5),
            "sector": sector_for(record.get("types", [])),
            "country": geo.get("country_code"),
            "ror_id": record.get("id"),
            "source": "ror",
        }
        for name in record["names"]:
            key = match_key(name["value"])
            if len(key) < 3:
                continue
            index = acronym_index if "acronym" in name["types"] else full_index
            if key in index and index[key] and index[key]["ror_id"] != info["ror_id"]:
                index[key] = None  # ambiguous name -> do not match it
            elif key not in index:
                index[key] = dict(info, name=name["value"])
    print(
        f"Indexed {sum(1 for v in full_index.values() if v)} unambiguous full names.",
        file=sys.stderr,
    )
    return full_index, acronym_index


def match_affiliation(raw: str, full_index: dict, acronym_index: dict):
    """Return org info for an affiliation string, or None if no confident match."""
    whole = match_key(raw)
    if full_index.get(whole):
        return full_index[whole]
    if acronym_index.get(whole):
        return acronym_index[whole]
    # Try comma / semicolon / slash separated segments (e.g. "Dept X, Univ Y").
    for segment in re.split(r"[;,/]", raw):
        key = match_key(segment)
        if len(key) >= 5 and full_index.get(key):
            return full_index[key]
    return None


def collect_affiliations() -> Counter:
    """Count author-slot occurrences of each normalized affiliation string."""
    anthology = Anthology.from_within_repo()
    counts: Counter = Counter()
    for paper in anthology.papers():
        for namespec in paper.authors:
            if namespec.affiliation:
                norm = normalize(namespec.affiliation)
                if norm:
                    counts[norm] += 1
    return counts


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match author affiliations against ROR and cache the results."
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=5,
        help="Only match affiliations appearing at least this many times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optionally cap the number of NEW affiliations matched this run.",
    )
    parser.add_argument(
        "--ror-file",
        type=Path,
        default=None,
        help="Path to a ROR data dump JSON (default: download/cache the latest).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force a re-download of the ROR data dump.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be matched without loading ROR or writing.",
    )
    args = parser.parse_args()

    cache: dict = {}
    if CACHE_PATH.exists():
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(cache)} cached affiliations.", file=sys.stderr)

    counts = collect_affiliations()
    print(f"Found {len(counts)} distinct affiliation strings.", file=sys.stderr)

    todo = [
        norm
        for norm, count in counts.most_common()
        if norm not in cache and count >= args.min_count and not is_junk(norm)
    ]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"{len(todo)} affiliations to match against ROR.", file=sys.stderr)

    if args.dry_run or not todo:
        for norm in todo:
            print(f"  {counts[norm]:6d}  {norm}")
        return

    dump = args.ror_file or resolve_ror_dump(refresh=args.refresh)
    full_index, acronym_index = build_ror_index(dump)

    sectors: Counter = Counter()
    matched = 0
    for norm in todo:
        info = match_affiliation(norm, full_index, acronym_index)
        cache[norm] = info
        if info:
            matched += 1
            sectors[info["sector"]] += 1
    save_cache(cache)

    print(
        f"Matched {matched}/{len(todo)} ({100 * matched / max(len(todo), 1):.0f}%). "
        f"By sector: {dict(sectors)}. Cache now holds {len(cache)} entries.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
