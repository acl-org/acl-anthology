"""Prepare video matches, verify actual-frame evidence, and save through the library."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re

from common import digest, normalize, read_json, sheet_records, write_json


def paper_link_id(url: str | None) -> str | None:
    match = re.fullmatch(r"https://aclanthology\.org/(\d{4}\.[\w-]+\.\d+)/?", url or "")
    return match[1] if match else None


def nonvideo_digest(paper) -> str:
    from lxml import etree

    element = paper.to_xml()
    for video in list(element.findall("video")):
        element.remove(video)
    return hashlib.sha256(etree.tostring(element)).hexdigest()


def candidate_matches(
    sheet: dict, provider: dict, papers: dict, titles: dict
) -> list[str]:
    supplied = paper_link_id(sheet["sheet_paper_link"])
    normalized = {normalize(sheet["sheet_title"]), normalize(provider["provider_title"])}
    if supplied in papers and normalize(papers[supplied]["title"]) in normalized:
        return [supplied]
    return sorted(
        {paper_id for title in normalized for paper_id in titles.get(title, [])}
    )


def export(report: Path):
    from acl_anthology import Anthology

    anthology = Anthology.from_within_repo()
    rows = sheet_records(report / "spreadsheet.csv")
    years = {
        paper_link_id(row["sheet_paper_link"])[:4]
        for row in rows
        if paper_link_id(row["sheet_paper_link"])
    }
    if not years:
        raise ValueError(
            "The sheet has no publication-year scope; establish one through the library."
        )
    collections = [
        collection_id
        for collection_id in anthology.collections
        if collection_id.split(".")[0] in years
    ]
    papers = {}
    titles = defaultdict(list)
    for collection_id in collections:
        collection = anthology.get_collection(collection_id)
        for volume in collection.values():
            for paper in volume.values():
                if paper.is_frontmatter:
                    continue
                authors = [
                    " ".join(filter(None, (author.name.first, author.name.last)))
                    for author in paper.authors
                ]
                videos = [
                    {"name": video.name, "permission": video.permission}
                    for video in paper.videos
                ]
                papers[paper.full_id] = {
                    "title": str(paper.title),
                    "authors": authors,
                    "existing_videos": videos,
                    "nonvideo_sha256": nonvideo_digest(paper),
                }
                titles[normalize(str(paper.title))].append(paper.full_id)
    catalog = {
        row["sheet"]["lecture_id"]: row
        for row in read_json(report / "catalog-results.json")
    }
    candidates = []
    for row in rows:
        provider = catalog[row["lecture_id"]]
        found = (
            candidate_matches(row, provider, papers, titles)
            if provider["status"] == "available"
            else []
        )
        candidates.append(
            {
                **row,
                "candidate_ids": found,
                "candidate_id": found[0] if len(found) == 1 else None,
                "supplied_id": paper_link_id(row["sheet_paper_link"]),
            }
        )
    write_json(
        report / "candidates.json",
        {
            "spreadsheet_sha256": digest(report / "spreadsheet.csv"),
            "scope": {
                "publication_years": sorted(years),
                "collections": len(collections),
            },
            "papers": papers,
            "records": candidates,
        },
    )
    print(
        "CANDIDATES",
        dict(
            Counter(
                "unique" if row["candidate_id"] else "unmatched-or-ambiguous"
                for row in candidates
            )
        ),
    )


def frame_match(text: str, paper: dict) -> bool:
    value = normalize(text)
    return normalize(paper["title"]) in value and any(
        normalize(author) in value for author in paper["authors"] if normalize(author)
    )


def review(report: Path, ocr: Path, manual: Path | None):
    candidates = read_json(report / "candidates.json")
    if digest(report / "spreadsheet.csv") != candidates["spreadsheet_sha256"]:
        raise ValueError("Spreadsheet changed since metadata matching")
    papers = candidates["papers"]
    expected = {row["lecture_id"]: row for row in candidates["records"]}
    frames = {}
    for line in ocr.read_text().splitlines():
        row = json.loads(line)
        if row.get("error"):
            raise ValueError(f"OCR failed for {row['path']}: {row['error']}")
        path = Path(row["path"])
        key = (path.parent.name, path.name)
        if key in frames:
            raise ValueError("Duplicate OCR frame")
        frames[key] = "\n".join(item["text"] for item in row["observations"])
    decisions = read_json(manual) if manual else {}
    anchors = defaultdict(list)
    for paper_id, paper in papers.items():
        title = normalize(paper["title"])
        if len(title) >= 16:
            anchors[title[:16]].append(paper_id)
    pattern = re.compile("|".join(sorted(anchors, key=len, reverse=True)))
    results = []
    for recording in read_json(report / "download-results.json"):
        lecture_id = recording["sheet"]["lecture_id"]
        candidate_id = expected[lecture_id]["candidate_id"]
        row = {
            **recording,
            "lecture_id": lecture_id,
            "paper_id": candidate_id,
            "status": "unmatched",
            "reason": "No unique exact title match in the recorded publication-year scope.",
            "evidence": [],
            "alternate_ids": [],
        }
        if recording["status"] != "downloaded":
            row["status"] = "failed"
            row["reason"] = recording["error"]
        else:
            texts = []
            for image in recording["frames"]:
                key = (lecture_id, Path(image["path"]).name)
                if key not in frames:
                    raise ValueError(f"Missing actual-frame OCR: {key}")
                text = frames[key]
                texts.append(text)
                if candidate_id and frame_match(text, papers[candidate_id]):
                    row["status"] = "verified"
                    row["reason"] = ""
                    row["evidence"].append(
                        {
                            **image,
                            "method": "Exact full title and full author in the same actual frame",
                        }
                    )
                normalized = normalize(text)
                possible = {
                    paper_id
                    for match in pattern.finditer(normalized)
                    for paper_id in anchors[match[0]]
                }
                row["alternate_ids"].extend(
                    paper_id
                    for paper_id in possible
                    if paper_id != candidate_id and frame_match(text, papers[paper_id])
                )
            row["alternate_ids"] = sorted(set(row["alternate_ids"]))
            if candidate_id and row["status"] != "verified":
                row["status"] = "needs-review"
                row["reason"] = (
                    "Exact metadata match lacks actual-frame title/author corroboration."
                )
            if row["alternate_ids"]:
                row["status"] = "needs-review"
                row["reason"] = (
                    "Another paper title/author appears; citations are not automatic reassignments."
                )
            if (
                not recording["audio_stream"]
                and recording["black_duration_ratio"] > 0.999
            ):
                row["status"] = "unusable"
                row["reason"] = (
                    "Full successful decode: black recording without an audio stream."
                )
        decision = decisions.get(lecture_id)
        if decision:
            if recording["status"] != "downloaded":
                raise ValueError("Cannot verify an undownloaded recording")
            paper_id = decision.get("paper_id")
            if not decision.get("evidence") or decision["sha256"] != recording["sha256"]:
                raise ValueError("Manual decision lacks recording-bound evidence")
            if decision["verdict"] == "verified":
                if paper_id not in papers:
                    raise ValueError(
                        "Manual target is outside the authoritative candidate index"
                    )
                row["paper_id"] = paper_id
                row["status"] = "verified"
                row["reason"] = ""
                row["evidence"] = [
                    {
                        "method": "Manual actual-content verification",
                        "description": decision["evidence"],
                    }
                ]
            elif decision["verdict"] in {"unmatched", "unusable", "needs-review"}:
                row["status"] = decision["verdict"]
                row["reason"] = decision["evidence"]
            else:
                raise ValueError("Unknown manual verdict")
        if row["paper_id"]:
            paper = papers[row["paper_id"]]
            row["expected_title"] = paper["title"]
            row["existing_videos"] = paper["existing_videos"]
            row["nonvideo_sha256"] = paper["nonvideo_sha256"]
            if any(not video["permission"] for video in paper["existing_videos"]):
                row["status"] = "withheld"
                row["reason"] = "Existing permission withholding must be preserved."
        if recording["status"] == "downloaded" and not recording["publication_allowed"]:
            row["status"] = "publication-held"
            row["reason"] = (
                "Provider marks this recording unpublished; user authorized download, not publication."
            )
        results.append(row)
    write_json(
        report / "reviewed.json",
        {
            "spreadsheet_sha256": candidates["spreadsheet_sha256"],
            "records": results,
            "counts": dict(Counter(row["status"] for row in results)),
        },
    )
    print("REVIEW", dict(Counter(row["status"] for row in results)))


def apply(report: Path, write: bool):
    from acl_anthology import Anthology
    from acl_anthology.files import VideoReference

    anthology = Anthology.from_within_repo()
    placements_path = report / "placements.json"
    placements = read_json(placements_path)
    by_paper = defaultdict(list)
    for row in placements:
        if (
            row["status"] != "verified"
            or not row["evidence"]
            or not row["publication_allowed"]
        ):
            raise ValueError("Placement lacks verified recording evidence")
        by_paper[row["paper_id"]].append(row)
    changes = {}
    added = 0
    for paper_id, rows in by_paper.items():
        paper = anthology.get_paper(paper_id)
        if paper is None:
            raise ValueError(f"Missing target paper: {paper_id}")
        before = rows[0]["existing_videos"]
        if any(row["existing_videos"] != before for row in rows):
            raise ValueError("Inconsistent original video permissions/order")
        after = list(before)
        for row in rows:
            video = {"name": row["reference_name"], "permission": True}
            if video not in after:
                after.append(video)
        actual = [
            {"name": video.name, "permission": video.permission} for video in paper.videos
        ]
        if actual not in (before, after):
            raise ValueError(f"Video metadata changed since matching: {paper_id}")
        if any(not video["permission"] for video in before):
            raise ValueError(f"Withheld target: {paper_id}")
        if any(nonvideo_digest(paper) != row["nonvideo_sha256"] for row in rows):
            raise ValueError(f"Non-video metadata changed: {paper_id}")
        added += len(after) - len(before)
        changes[paper_id] = after
        if write:
            paper.videos = tuple(VideoReference(**video) for video in after)
    if not write:
        print("DRY RUN", len(changes), "papers;", added, "references")
        return
    import subprocess

    repo = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )
    collections = sorted({paper_id.split("-")[0] for paper_id in changes})
    for collection_id in collections:
        source = repo / "data/xml" / (collection_id + ".xml")
        backup = report / "original-metadata" / source.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            with backup.open("xb") as stream:
                stream.write(source.read_bytes())
    anthology.save_all()
    saved = Anthology.from_within_repo()
    for paper_id, after in changes.items():
        paper = saved.get_paper(paper_id)
        actual = [
            {"name": video.name, "permission": video.permission} for video in paper.videos
        ]
        if (
            actual != after
            or nonvideo_digest(paper) != by_paper[paper_id][0]["nonvideo_sha256"]
        ):
            raise ValueError(f"Saved metadata invariant failed: {paper_id}")
    write_json(
        report / "metadata-validation.json",
        {
            "status": "passed",
            "placements_sha256": digest(placements_path),
            "papers_checked": len(changes),
            "references_added": added,
            "collections": collections,
            "saved_collection_sha256": {
                collection_id: digest(repo / "data/xml" / (collection_id + ".xml"))
                for collection_id in collections
            },
            "nonvideo_metadata_preserved": True,
            "existing_order_and_permissions_preserved": True,
            "repository_checks": {"status": "pending"},
        },
    )
    print("SAVED", len(changes), "papers;", added, "references")


def validate(report: Path):
    import os
    import subprocess

    path = report / "metadata-validation.json"
    validation = read_json(path)
    process = subprocess.run(
        ["just", "check"],
        env={**os.environ, "UV_FROZEN": "true", "UV_NO_SYNC": "true"},
        capture_output=True,
        text=True,
    )
    log = report / "repository-checks.log"
    log.write_text(process.stdout + process.stderr)
    validation["repository_checks"] = {
        "status": "passed" if process.returncode == 0 else "failed",
        "command": "UV_FROZEN=true UV_NO_SYNC=true just check",
        "exit_code": process.returncode,
        "log_sha256": digest(log),
    }
    write_json(path, validation)
    if process.returncode:
        raise RuntimeError(f"Repository checks failed; see {log}")
    print("REPOSITORY_CHECKS_PASSED")


def report_results(report: Path):
    catalog = {
        row["sheet"]["lecture_id"]: row
        for row in read_json(report / "catalog-results.json")
    }
    downloaded = {
        row["sheet"]["lecture_id"]: row
        for row in read_json(report / "download-results.json")
    }
    reviewed = {
        row["lecture_id"]: row for row in read_json(report / "reviewed.json")["records"]
    }
    placements = {row["lecture_id"]: row for row in read_json(report / "placements.json")}
    finalized = read_json(report / "finalized.json")
    if finalized["status"] != "complete":
        raise ValueError("Archive placement has not been finalized")
    rows = []
    for sheet in sheet_records(report / "spreadsheet.csv"):
        lecture_id = sheet["lecture_id"]
        source = downloaded.get(lecture_id, catalog[lecture_id])
        review_row = reviewed.get(lecture_id, {})
        placement = placements.get(lecture_id, {})
        status = "linked" if placement else review_row.get("status", "failed")
        rows.append(
            {
                "sheet_row": sheet["sheet_row"],
                "lecture_id": lecture_id,
                "paper_number": sheet["paper_number"],
                "sheet_title": sheet["sheet_title"],
                "provider_title": source.get("provider_title", ""),
                "supplied_paper_link": sheet["sheet_paper_link"],
                "paper_id": placement.get("paper_id", review_row.get("paper_id") or ""),
                "status": status,
                "reason": ""
                if placement
                else review_row.get("reason", source.get("error", "")),
                "source_path": source.get("source_path", ""),
                "destination_path": placement.get("destination_path", ""),
                "video_href": placement.get("reference_name", ""),
                "url": placement.get("url", ""),
                "size_bytes": source.get("source_fingerprint", {}).get("size", ""),
                "sha256": source.get("sha256", ""),
                "metadata_status": placement.get("metadata_status", ""),
                "placement": finalized["placement"] if placement else "retained",
            }
        )
    for name, selected in (
        ("videos.tsv", rows),
        ("videos-linked.tsv", [row for row in rows if row["status"] == "linked"]),
        ("videos-unmatched.tsv", [row for row in rows if row["status"] != "linked"]),
    ):
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(selected)
        (report / name).write_text(stream.getvalue())
    counts = Counter(row["status"] for row in rows)
    metadata = read_json(report / "metadata-validation.json")
    summary = {
        "spreadsheet_sha256": digest(report / "spreadsheet.csv"),
        "recordings_listed": len(rows),
        "status_counts": dict(counts),
        "unique_linked_urls": len(
            {row["url"] for row in rows if row["status"] == "linked"}
        ),
        "metadata_validation": metadata,
        "archive_finalization": finalized,
        "unmatched_sources_retained": True,
    }
    write_json(report / "summary.json", summary)
    text = [
        "# Presentation-video ingestion",
        "",
        f"- Listed recordings: **{len(rows)}**",
        f"- Successfully linked recordings: **{counts['linked']}**",
        f"- New video references: **{metadata['references_added']}**",
        f"- Matched-source placement: **{finalized['placement']}**",
        "- Unmatched, ambiguous, withheld, and unusable sources are retained.",
        "- Sheet/provider paper links are hints; exact authoritative titles and actual-frame/manual evidence determine assignments.",
        "- Non-video metadata, existing video ordering, and withheld permissions were preserved.",
        "",
        "## Status totals",
        "",
        *[f"- {status}: {count}" for status, count in sorted(counts.items())],
        "",
        "## Server audit files",
        "",
        "- `videos.tsv`: every supplied recording and its outcome.",
        "- `videos-linked.tsv`: verified paper IDs, original/canonical paths, SHA256 and placement.",
        "- `videos-unmatched.tsv`: retained or failed recordings with explicit reasons.",
        "- `moves.jsonl` and `moves/`: durable movement intents and receipts.",
        "- `summary.json`, `metadata-validation.json`, `finalized.json`: validation and totals.",
        "- `catalog/`, `downloads/`, `frames/`, `logs/`, `failures/`: provenance and failure evidence.",
        "",
        "Metadata must be merged/deployed before the production paper pages show the new links.",
        "",
    ]
    (report / "report.md").write_text("\n".join(text))
    print("REPORT", summary["status_counts"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("export", "review", "apply", "validate", "report")
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--ocr", type=Path)
    parser.add_argument("--manual", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = args.report.resolve(strict=True)
    if args.command == "export":
        export(report)
    elif args.command == "review":
        if not args.ocr:
            parser.error("--ocr is required")
        review(report, args.ocr, args.manual)
    elif args.command == "apply":
        apply(report, args.write)
    elif args.command == "validate":
        validate(report)
    else:
        report_results(report)


if __name__ == "__main__":
    main()
