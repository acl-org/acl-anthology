#!/usr/bin/env python3

"""Export an event's papers as a TSV for requesting videos from Underline.

Includes all volumes in the event's collection and all colocated volumes.
Front matter, back matter, and deleted papers are excluded. Author names are
exported as published, in paper order, separated by semicolons.

Usage:
    uv run bin/export_video_request.py emnlp-2026 > emnlp-2026-videos.tsv
    uv run bin/export_video_request.py emnlp-2026 -o emnlp-2026-videos.tsv
"""

import argparse
import csv
import sys
from contextlib import nullcontext
from itertools import chain
from pathlib import Path
from typing import TextIO

from acl_anthology import Anthology
from acl_anthology.collections.types import PaperType


def export_video_request(anthology: Anthology, event_id: str, stream: TextIO) -> None:
    """Write unique papers from the event and its colocated volumes to a TSV."""
    event = anthology.get_event(event_id)
    if event is None:
        raise ValueError(f"Event {event_id} not found in the Anthology.")

    volumes = {
        volume.full_id: volume
        for volume in chain(event.collection.volumes(), event.volumes())
    }
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(("anthology_id", "title", "authors"))
    for volume in volumes.values():
        for paper in volume.papers():
            if (
                paper.is_frontmatter
                or paper.type == PaperType.BACKMATTER
                or paper.is_deleted
            ):
                continue
            writer.writerow(
                (
                    paper.full_id,
                    " ".join(paper.title.as_text().split()),
                    "; ".join(
                        " ".join(author.name.as_first_last().split())
                        for author in paper.authors
                    ),
                )
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("event", help="Event ID (e.g. emnlp-2026).")
    parser.add_argument(
        "-o", "--output", type=Path, help="Write to this file instead of STDOUT."
    )
    args = parser.parse_args()
    anthology = Anthology.from_within_repo()
    try:
        with (
            args.output.open("w", encoding="utf-8", newline="")
            if args.output
            else nullcontext(sys.stdout)
        ) as stream:
            export_video_request(anthology, args.event, stream)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
