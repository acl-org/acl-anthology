#!/usr/bin/env python3

"""Backfill paper-author OpenReview IDs from an aclpub2 papers.yml file."""

import argparse
import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml

from acl_anthology import Anthology
from acl_anthology.people import Name
from acl_anthology.text import MarkupText


TYPOGRAPHIC_PUNCTUATION = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "ʼ": "'",
        "‐": "-",
        "‑": "-",
        "–": "-",
        "—": "-",
    }
)
ORCID_PATTERN = re.compile(r"\d{4}-\d{4}-\d{4}-[\dX]{4}", re.IGNORECASE)


def canonicalize(value: str) -> str:
    """Normalize text for strict-but-format-insensitive comparisons."""
    normalized = unicodedata.normalize("NFKC", value).translate(TYPOGRAPHIC_PUNCTUATION)
    return " ".join(normalized.split()).casefold()


def source_title(paper: dict[str, Any]) -> str:
    title = paper.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"Source paper {paper.get('id')!r} has no title")
    return MarkupText.from_latex_maybe(title).as_text()


def source_author_name(author: dict[str, Any]) -> str:
    first = " ".join(
        str(author[field]).strip()
        for field in ("first_name", "middle_name")
        if author.get(field)
    )
    last = str(author.get("last_name") or "").strip()
    if not last:
        full = str(author.get("name") or "").strip()
        if not full:
            raise ValueError(f"Source author has no usable name: {author!r}")
        return Name(None, full).latex_normalize().as_first_last()
    return Name(first or None, last).latex_normalize().as_first_last()


def source_openreview_id(author: dict[str, Any]) -> str | None:
    explicit_value = author.get("openreview")
    value = explicit_value or author.get("username")
    if value is None:
        return None
    value = str(value).strip()
    if explicit_value is None and not value.startswith("~"):
        return None
    if not value.startswith("~") or any(character.isspace() for character in value):
        raise ValueError(f"Invalid OpenReview profile ID: {value!r}")
    return value


def source_orcid(author: dict[str, Any]) -> str | None:
    value = author.get("orcid")
    if value is None:
        return None
    match = ORCID_PATTERN.search(str(value))
    return match.group().upper() if match is not None else None


def parse_author_mappings(values: list[str]) -> dict[tuple[int, int], int]:
    mappings = {}
    for value in values:
        try:
            paper_number, source_author_number, target_author_number = (
                int(part) for part in value.split(":")
            )
        except ValueError as error:
            raise ValueError(
                f"Invalid author mapping {value!r}; expected PAPER:SOURCE:TARGET"
            ) from error
        key = (paper_number, source_author_number)
        if key in mappings:
            raise ValueError(f"Duplicate author mapping for {key}: {value!r}")
        mappings[key] = target_author_number
    return mappings


def parse_extra_target_authors(values: list[str]) -> set[tuple[int, int]]:
    extra_authors = set()
    for value in values:
        try:
            paper_number, target_author_number = (int(part) for part in value.split(":"))
        except ValueError as error:
            raise ValueError(
                f"Invalid extra target author {value!r}; expected PAPER:TARGET"
            ) from error
        key = (paper_number, target_author_number)
        if key in extra_authors:
            raise ValueError(f"Duplicate extra target author: {value!r}")
        extra_authors.add(key)
    return extra_authors


def parse_extra_source_authors(values: list[str]) -> set[tuple[int, int]]:
    extra_authors = set()
    for value in values:
        try:
            paper_number, source_author_number = (int(part) for part in value.split(":"))
        except ValueError as error:
            raise ValueError(
                f"Invalid extra source author {value!r}; expected PAPER:SOURCE"
            ) from error
        key = (paper_number, source_author_number)
        if key in extra_authors:
            raise ValueError(f"Duplicate extra source author: {value!r}")
        extra_authors.add(key)
    return extra_authors


def audit(source_path: Path, volume_id: str) -> None:
    """Report every title and author alignment difference in one volume."""
    source_data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(source_data, list):
        raise ValueError(f"Expected a paper list in {source_path}")

    anthology = Anthology.from_within_repo()
    volume = anthology.get_volume(volume_id)
    if volume is None:
        raise ValueError(f"Unknown Anthology volume: {volume_id}")

    expected_paper_ids = set()
    title_differences = 0
    author_differences = 0
    for paper_number, source_paper in enumerate(source_data, start=1):
        if not source_paper.get("archival", True):
            continue
        expected_paper_ids.add(str(paper_number))
        paper_id = f"{volume_id}.{paper_number}"
        target_paper = anthology.get_paper(paper_id)
        if target_paper is None:
            print(f"MISSING PAPER {paper_id}")
            continue

        expected_title = source_title(source_paper)
        actual_title = target_paper.title.as_text()
        if canonicalize(expected_title) != canonicalize(actual_title):
            title_differences += 1
            print(
                f"TITLE {paper_number} (--allow-title-mismatch {paper_number}):\n"
                f"  source: {expected_title}\n"
                f"  target: {actual_title}"
            )

        source_authors = source_paper.get("authors", [])
        unmatched_source_numbers = set(range(1, len(source_authors) + 1))
        unmatched_target_numbers = set(range(1, len(target_paper.authors) + 1))
        made_match = True
        while made_match:
            made_match = False
            for source_author_number in sorted(unmatched_source_numbers):
                source_author = source_authors[source_author_number - 1]
                expected_name = source_author_name(source_author)
                orcid = source_orcid(source_author)
                orcid_matches = [
                    target_number
                    for target_number in unmatched_target_numbers
                    if orcid is not None
                    and target_paper.authors[target_number - 1].orcid == orcid
                ]
                candidates = orcid_matches or [
                    target_number
                    for target_number in unmatched_target_numbers
                    if canonicalize(expected_name)
                    == canonicalize(
                        target_paper.authors[target_number - 1].name.as_first_last()
                    )
                ]
                if len(candidates) == 1:
                    unmatched_source_numbers.remove(source_author_number)
                    unmatched_target_numbers.remove(candidates[0])
                    made_match = True
                    break

        if unmatched_source_numbers or unmatched_target_numbers:
            author_differences += 1
            source_names = [
                (number, source_author_name(source_authors[number - 1]))
                for number in sorted(unmatched_source_numbers)
            ]
            target_names = [
                (number, target_paper.authors[number - 1].name.as_first_last())
                for number in sorted(unmatched_target_numbers)
            ]
            print(
                f"AUTHORS {paper_number}:\n"
                f"  unmatched source: {source_names}\n"
                f"  unmatched target: {target_names}"
            )

    actual_paper_ids = {paper.id for paper in volume.papers() if paper.id != "0"}
    if expected_paper_ids != actual_paper_ids:
        missing = sorted(expected_paper_ids - actual_paper_ids, key=int)
        extra = sorted(actual_paper_ids - expected_paper_ids, key=int)
        print(f"PAPER SET: missing={missing}, extra={extra}")
    print(
        f"Audit complete for {volume_id}: {title_differences} title differences, "
        f"{author_differences} papers with author differences."
    )


def backfill(
    source_path: Path,
    volume_id: str,
    apply: bool,
    allowed_title_mismatches: set[str],
    author_mappings: dict[tuple[int, int], int],
    extra_source_authors: set[tuple[int, int]],
    extra_target_authors: set[tuple[int, int]],
    allowed_orcid_mismatches: set[tuple[int, int]],
    allowed_invalid_openreview_ids: set[tuple[int, int]],
    allowed_missing_target_papers: set[str],
    allowed_extra_target_papers: set[str],
) -> None:
    source_data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(source_data, list):
        raise ValueError(f"Expected a paper list in {source_path}")

    anthology = Anthology.from_within_repo()
    volume = anthology.get_volume(volume_id)
    if volume is None:
        raise ValueError(f"Unknown Anthology volume: {volume_id}")

    expected_paper_ids = set()
    seen_title_mismatches = set()
    seen_author_mappings = set()
    seen_extra_source_authors = set()
    seen_extra_target_authors = set()
    seen_orcid_mismatches = set()
    seen_invalid_openreview_ids = set()
    updates = []
    aligned_author_count = 0
    reordered_author_count = 0
    for paper_number, source_paper in enumerate(source_data, start=1):
        if not source_paper.get("archival", True):
            continue

        paper_id = f"{volume_id}.{paper_number}"
        expected_paper_ids.add(str(paper_number))
        target_paper = anthology.get_paper(paper_id)
        if target_paper is None:
            if str(paper_number) in allowed_missing_target_papers:
                print(f"Reviewed source-only paper: {paper_id}")
                continue
            raise ValueError(f"Source paper has no Anthology counterpart: {paper_id}")

        expected_title = source_title(source_paper)
        actual_title = target_paper.title.as_text()
        if canonicalize(expected_title) != canonicalize(actual_title):
            if str(paper_number) not in allowed_title_mismatches:
                raise ValueError(
                    f"Title mismatch for {paper_id}:\n"
                    f"  source: {expected_title}\n"
                    f"  target: {actual_title}\n"
                    f"Review the ordered authors, then pass "
                    f"--allow-title-mismatch {paper_number} if this is a correction."
                )
            seen_title_mismatches.add(str(paper_number))
            print(
                f"Reviewed title difference for {paper_id}:\n"
                f"  source: {expected_title}\n"
                f"  target: {actual_title}"
            )

        source_authors = source_paper.get("authors", [])
        paper_extra_source_authors = {
            source_author_number
            for mapped_paper, source_author_number in extra_source_authors
            if mapped_paper == paper_number
        }
        paper_extra_target_authors = {
            target_author_number
            for mapped_paper, target_author_number in extra_target_authors
            if mapped_paper == paper_number
        }
        if len(source_authors) - len(paper_extra_source_authors) + len(
            paper_extra_target_authors
        ) != len(target_paper.authors):
            raise ValueError(
                f"Author count mismatch for {paper_id}: "
                f"source={len(source_authors)}, target={len(target_paper.authors)}, "
                f"reviewed source-only={len(paper_extra_source_authors)}, "
                f"reviewed target-only={len(paper_extra_target_authors)}"
            )

        matches = {}
        unmatched_target_numbers = set(range(1, len(target_paper.authors) + 1))
        for source_author_number in paper_extra_source_authors:
            if not 1 <= source_author_number <= len(source_authors):
                raise ValueError(
                    f"Source-only author is out of range for {paper_id}: "
                    f"{source_author_number}"
                )
            seen_extra_source_authors.add((paper_number, source_author_number))
            print(
                f"Reviewed source-only author for {paper_id}, author "
                f"{source_author_number}: "
                f"{source_author_name(source_authors[source_author_number - 1])}"
            )
        for target_author_number in paper_extra_target_authors:
            if target_author_number not in unmatched_target_numbers:
                raise ValueError(
                    f"Target-only author is out of range for {paper_id}: "
                    f"{target_author_number}"
                )
            unmatched_target_numbers.remove(target_author_number)
            seen_extra_target_authors.add((paper_number, target_author_number))
            print(
                f"Reviewed target-only author for {paper_id}, author "
                f"{target_author_number}: "
                f"{target_paper.authors[target_author_number - 1].name.as_first_last()}"
            )
        for (
            mapped_paper,
            source_author_number,
        ), target_author_number in author_mappings.items():
            if mapped_paper != paper_number:
                continue
            if not 1 <= source_author_number <= len(source_authors):
                raise ValueError(
                    f"Source author out of range in mapping "
                    f"{paper_number}:{source_author_number}:{target_author_number}"
                )
            if target_author_number not in unmatched_target_numbers:
                raise ValueError(
                    f"Target author is duplicated or out of range in mapping "
                    f"{paper_number}:{source_author_number}:{target_author_number}"
                )
            matches[source_author_number] = target_author_number
            unmatched_target_numbers.remove(target_author_number)
            seen_author_mappings.add((paper_number, source_author_number))

        for source_author_number, source_author in enumerate(source_authors, start=1):
            if (
                source_author_number in matches
                or source_author_number in paper_extra_source_authors
            ):
                continue
            expected_name = source_author_name(source_author)
            orcid = source_orcid(source_author)
            orcid_matches = [
                target_number
                for target_number in unmatched_target_numbers
                if orcid is not None
                and target_paper.authors[target_number - 1].orcid == orcid
            ]
            if len(orcid_matches) > 1:
                raise ValueError(
                    f"Ambiguous ORCID match for {paper_id}, source author "
                    f"{source_author_number}: {orcid}"
                )
            if orcid_matches:
                target_author_number = orcid_matches[0]
            else:
                name_matches = [
                    target_number
                    for target_number in unmatched_target_numbers
                    if canonicalize(expected_name)
                    == canonicalize(
                        target_paper.authors[target_number - 1].name.as_first_last()
                    )
                ]
                if len(name_matches) != 1:
                    target_names = [
                        target_paper.authors[target_number - 1].name.as_first_last()
                        for target_number in sorted(unmatched_target_numbers)
                    ]
                    raise ValueError(
                        f"Could not uniquely align {paper_id}, source author "
                        f"{source_author_number} ({expected_name!r}); unmatched target "
                        f"authors: {target_names}. Pass --map-author "
                        f"{paper_number}:{source_author_number}:TARGET after review."
                    )
                target_author_number = name_matches[0]
                target_orcid = target_paper.authors[target_author_number - 1].orcid
                if (
                    orcid is not None
                    and target_orcid not in (None, orcid)
                    and (paper_number, source_author_number)
                    not in allowed_orcid_mismatches
                ):
                    raise ValueError(
                        f"Conflicting ORCIDs for {paper_id}, source author "
                        f"{source_author_number}: source={orcid}, target={target_orcid}"
                    )
            matches[source_author_number] = target_author_number
            unmatched_target_numbers.remove(target_author_number)

        if unmatched_target_numbers:
            raise ValueError(
                f"Unmatched target authors for {paper_id}: "
                f"{sorted(unmatched_target_numbers)}"
            )

        for source_author_number, source_author in enumerate(source_authors, start=1):
            if source_author_number in paper_extra_source_authors:
                continue
            target_author_number = matches[source_author_number]
            target_author = target_paper.authors[target_author_number - 1]
            expected_name = source_author_name(source_author)
            actual_name = target_author.name.as_first_last()
            orcid = source_orcid(source_author)
            if (
                orcid is not None
                and target_author.orcid is not None
                and target_author.orcid != orcid
            ):
                key = (paper_number, source_author_number)
                if key not in allowed_orcid_mismatches:
                    raise ValueError(
                        f"Conflicting ORCIDs for {paper_id}, source author "
                        f"{source_author_number}: source={orcid}, "
                        f"target={target_author.orcid}"
                    )
                seen_orcid_mismatches.add(key)
                print(
                    f"Reviewed ORCID mismatch for {paper_id}, source author "
                    f"{source_author_number}: source={orcid}, "
                    f"target={target_author.orcid}"
                )
            if canonicalize(expected_name) != canonicalize(actual_name):
                print(
                    f"Reviewed author mapping for {paper_id}, source author "
                    f"{source_author_number} -> target author {target_author_number}:\n"
                    f"  source: {expected_name}\n"
                    f"  target: {actual_name}"
                )
            if source_author_number != target_author_number:
                reordered_author_count += 1

            try:
                openreview_id = source_openreview_id(source_author)
            except ValueError:
                key = (paper_number, source_author_number)
                if key not in allowed_invalid_openreview_ids:
                    raise
                seen_invalid_openreview_ids.add(key)
                print(
                    f"Reviewed invalid OpenReview ID for {paper_id}, source author "
                    f"{source_author_number}"
                )
                continue
            if (
                openreview_id is not None
                and target_author.openreview is not None
                and target_author.openreview != openreview_id
            ):
                raise ValueError(
                    f"Conflicting OpenReview IDs for {paper_id}, source author "
                    f"{source_author_number}: "
                    f"source={openreview_id!r}, target={target_author.openreview!r}"
                )
            if openreview_id is not None and target_author.openreview is None:
                updates.append((target_author, openreview_id))
            aligned_author_count += 1

    actual_paper_ids = {paper.id for paper in volume.papers() if paper.id != "0"}
    missing = expected_paper_ids - actual_paper_ids
    extra = actual_paper_ids - expected_paper_ids
    if missing != allowed_missing_target_papers or extra != allowed_extra_target_papers:
        raise ValueError(
            f"Paper set mismatch for {volume_id}: "
            f"missing={sorted(missing, key=int)}, extra={sorted(extra, key=int)}; "
            f"reviewed missing={sorted(allowed_missing_target_papers, key=int)}, "
            f"reviewed extra={sorted(allowed_extra_target_papers, key=int)}"
        )
    for paper_id in sorted(allowed_extra_target_papers, key=int):
        print(f"Reviewed target-only paper: {volume_id}.{paper_id}")

    unused_title_allowances = allowed_title_mismatches - seen_title_mismatches
    if unused_title_allowances:
        raise ValueError(
            f"Allowed title mismatches did not differ: "
            f"{sorted(unused_title_allowances, key=int)}"
        )
    unused_author_mappings = set(author_mappings) - seen_author_mappings
    if unused_author_mappings:
        raise ValueError(f"Unused author mappings: {sorted(unused_author_mappings)}")
    unused_extra_source_authors = extra_source_authors - seen_extra_source_authors
    if unused_extra_source_authors:
        raise ValueError(
            f"Unused source-only author allowances: {sorted(unused_extra_source_authors)}"
        )
    unused_extra_target_authors = extra_target_authors - seen_extra_target_authors
    if unused_extra_target_authors:
        raise ValueError(
            f"Unused target-only author allowances: {sorted(unused_extra_target_authors)}"
        )
    unused_orcid_mismatches = allowed_orcid_mismatches - seen_orcid_mismatches
    if unused_orcid_mismatches:
        raise ValueError(
            f"Unused ORCID mismatch allowances: {sorted(unused_orcid_mismatches)}"
        )
    unused_invalid_openreview_ids = (
        allowed_invalid_openreview_ids - seen_invalid_openreview_ids
    )
    if unused_invalid_openreview_ids:
        raise ValueError(
            f"Unused invalid OpenReview ID allowances: "
            f"{sorted(unused_invalid_openreview_ids)}"
        )

    print(
        f"Aligned {len(expected_paper_ids)} papers and {aligned_author_count} authors "
        f"for {volume_id} ({reordered_author_count} reordered author positions); "
        f"{len(updates)} OpenReview IDs to add."
    )
    if not apply:
        print("Dry run only; pass --apply to save the aligned volume.")
        return

    for target_author, openreview_id in updates:
        target_author.openreview = openreview_id
    anthology.save_all()
    print(f"Saved {len(updates)} OpenReview IDs for {volume_id}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to one aclpub2 papers.yml")
    parser.add_argument("volume_id", help="Target Anthology volume ID")
    parser.add_argument(
        "--allow-title-mismatch",
        action="append",
        default=[],
        metavar="PAPER_NUMBER",
        help="Allow one reviewed title correction when authors align",
    )
    parser.add_argument(
        "--map-author",
        action="append",
        default=[],
        metavar="PAPER:SOURCE:TARGET",
        help="Map one reviewed source author to a differently named target author",
    )
    parser.add_argument(
        "--allow-extra-source-author",
        action="append",
        default=[],
        metavar="PAPER:SOURCE",
        help="Allow one reviewed source author that is absent from the XML",
    )
    parser.add_argument(
        "--allow-extra-target-author",
        action="append",
        default=[],
        metavar="PAPER:TARGET",
        help="Allow one reviewed XML author that is absent from the source",
    )
    parser.add_argument(
        "--allow-invalid-openreview",
        action="append",
        default=[],
        metavar="PAPER:SOURCE",
        help="Skip one reviewed malformed source OpenReview profile ID",
    )
    parser.add_argument(
        "--allow-orcid-mismatch",
        action="append",
        default=[],
        metavar="PAPER:SOURCE",
        help="Allow one reviewed source/Anthology ORCID conflict",
    )
    parser.add_argument(
        "--allow-missing-target-paper",
        action="append",
        default=[],
        metavar="PAPER_NUMBER",
        help="Allow one reviewed source paper that is absent from the Anthology",
    )
    parser.add_argument(
        "--allow-extra-target-paper",
        action="append",
        default=[],
        metavar="PAPER_NUMBER",
        help="Allow one reviewed Anthology paper that is absent from the source",
    )
    parser.add_argument(
        "--apply", action="store_true", help="Save changes after full-volume validation"
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Report all alignment differences without validating or saving IDs",
    )
    args = parser.parse_args()
    if args.audit:
        if args.apply:
            parser.error("--audit and --apply cannot be used together")
        audit(args.source, args.volume_id)
        return
    backfill(
        args.source,
        args.volume_id,
        args.apply,
        set(args.allow_title_mismatch),
        parse_author_mappings(args.map_author),
        parse_extra_source_authors(args.allow_extra_source_author),
        parse_extra_target_authors(args.allow_extra_target_author),
        parse_extra_source_authors(args.allow_orcid_mismatch),
        parse_extra_source_authors(args.allow_invalid_openreview),
        set(args.allow_missing_target_paper),
        set(args.allow_extra_target_paper),
    )


if __name__ == "__main__":
    main()
