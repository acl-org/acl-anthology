#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

import yaml


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_yaml_file(path: Path):
    try:
        load_yaml(path)
    except yaml.YAMLError as exc:
        return False, str(exc)
    except UnicodeDecodeError as exc:
        return False, str(exc)
    return True, None


def iter_yaml_files(path: Path):
    if path.is_dir():
        for child in sorted(path.rglob("*.yaml")):
            if child.is_file():
                yield child
    elif path.is_file() and path.suffix == ".yaml":
        yield path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate YAML files for the ACL Anthology repository."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to validate. Directories are scanned recursively.",
    )
    args = parser.parse_args()

    failures = 0
    for root in args.paths:
        root_path = Path(root)
        if not root_path.exists():
            print(f"ERROR: path does not exist: {root_path}", file=sys.stderr)
            failures += 1
            continue

        for path in iter_yaml_files(root_path):
            ok, error = validate_yaml_file(path)
            if ok:
                print(f"OK: {path}")
            else:
                print(f"FAIL: {path}")
                print(error)
                failures += 1

    if failures:
        print(f"\nValidation completed with {failures} failure(s).", file=sys.stderr)
        return 1

    print("\nValidation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
