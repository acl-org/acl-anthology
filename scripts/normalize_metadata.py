#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

import yaml

ORDER = [
    "id",
    "title",
    "subtitle",
    "abbr",
    "year",
    "month",
    "authors",
    "abstract",
    "attachments",
    "pdf",
    "doi",
    "url",
    "publisher",
    "venue",
    "note",
]


def normalize_document(data):
    if not isinstance(data, dict):
        return data

    normalized = {}
    for key in ORDER:
        if key in data:
            normalized[key] = data[key]

    for key, value in data.items():
        if key not in normalized:
            normalized[key] = value

    return normalized


def normalize_file(path: Path, write: bool):
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    normalized = normalize_document(data)
    if normalized == data and not write:
        return False

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(normalized, f, sort_keys=False, indent=2)

    return True


def collect_yaml_files(root: Path):
    if root.is_dir():
        for file_path in sorted(root.rglob("*.yaml")):
            yield file_path
    elif root.is_file() and root.suffix == ".yaml":
        yield root


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize Anthology YAML metadata files to a consistent key ordering."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to normalize.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write normalized YAML back to the original files.",
    )
    args = parser.parse_args()

    touched = 0
    for root in args.paths:
        root_path = Path(root)
        if not root_path.exists():
            print(f"ERROR: path does not exist: {root_path}", file=sys.stderr)
            return 1

        for path in collect_yaml_files(root_path):
            modified = normalize_file(path, args.write)
            if modified:
                print(f"Normalized: {path}")
                touched += 1
            else:
                print(f"Unchanged: {path}")

    print(f"\nProcessed {touched} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
