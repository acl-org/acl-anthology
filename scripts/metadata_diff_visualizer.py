#!/usr/bin/env python3

import argparse
import difflib
from pathlib import Path
import sys

import yaml


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def yaml_to_lines(data):
    return yaml.safe_dump(data, sort_keys=False, indent=2).splitlines()


def compare_files(before_path: Path, after_path: Path):
    before = load_yaml(before_path)
    after = load_yaml(after_path)
    before_lines = yaml_to_lines(before)
    after_lines = yaml_to_lines(after)
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=str(before_path),
        tofile=str(after_path),
        lineterm="",
    )
    return list(diff)


def write_report(lines, output_path: Path):
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote diff report to {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize differences between two Anthology metadata files.")
    parser.add_argument("before", help="Path to the original YAML file.")
    parser.add_argument("after", help="Path to the updated YAML file.")
    parser.add_argument("--output", default="metadata-diff.txt", help="Path to write the diff report.")
    args = parser.parse_args()

    diff_lines = compare_files(Path(args.before), Path(args.after))
    if not diff_lines:
        print("No differences found.")
        return 0

    write_report(diff_lines, Path(args.output))
    print("Metadata diff report generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
