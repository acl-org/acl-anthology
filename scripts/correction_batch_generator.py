#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path
import sys

import yaml


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, indent=2)


def normalize_paper_yaml(data):
    if not isinstance(data, dict):
        return data
    ordered_keys = [
        "id",
        "title",
        "subtitle",
        "year",
        "month",
        "authors",
        "abstract",
        "attachments",
        "pdf",
        "doi",
        "url",
    ]
    normalized = {k: data[k] for k in ordered_keys if k in data}
    for k, v in data.items():
        if k not in normalized:
            normalized[k] = v
    return normalized


def apply_patch_to_file(target_path: Path, changes: dict):
    data = load_yaml(target_path)
    updated = data.copy()
    updated.update(changes)
    updated = normalize_paper_yaml(updated)
    save_yaml(target_path, updated)
    return target_path


def ensure_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def generate_batch(output_dir: Path, instructions):
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    for item in instructions:
        paper_id = item["id"]
        changes = item["changes"]
        path = output_dir / f"{paper_id}.yaml"
        ensure_dir(path)
        save_yaml(path, changes)
        generated_files.append(path)

    return generated_files


def read_instructions_from_csv(path: Path):
    items = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_id = row.get("id") or row.get("paper_id")
            if not paper_id:
                continue
            change_fields = {k: v for k, v in row.items() if k not in {"id", "paper_id"} and v}
            items.append({"id": paper_id, "changes": change_fields})
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a correction batch from a CSV or patch instruction file.")
    parser.add_argument("--output-dir", default="correction_batch", help="Directory to write generated YAML files.")
    parser.add_argument("--csv", help="CSV file containing paper ids and field updates.")
    parser.add_argument("--paper-id", help="Single paper id to generate a correction for.")
    parser.add_argument("--field", action="append", nargs=2, metavar=("KEY", "VALUE"), help="Field update to apply to the target paper.")
    parser.add_argument("--draft", action="store_true", help="Generate draft YAML files without applying them directly.")
    parser.set_defaults(func=lambda args: 1)

    args = parser.parse_args()
    if args.csv:
        instructions = read_instructions_from_csv(Path(args.csv))
        generated = generate_batch(Path(args.output_dir), instructions)
        for path in generated:
            print(f"Generated: {path}")
        return 0

    if args.paper_id and args.field:
        changes = {key: value for key, value in args.field}
        output_path = Path(args.output_dir) / f"{args.paper_id}.yaml"
        ensure_dir(output_path)
        save_yaml(output_path, normalize_paper_yaml(changes))
        print(f"Generated draft correction: {output_path}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
