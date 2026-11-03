#!/usr/bin/env python3
"""Promote legacy event talks to persistent, citable media records.

Usage: uv run bin/oneoff/migrate_talks.py [--dry-run]

IDs are assigned once in event order, stored in the collection XML, and never
derived from recording filenames. Existing recording URLs remain unchanged.
"""

from __future__ import annotations

import argparse
from datetime import date
import logging
from pathlib import Path
import sys

from attrs import evolve

from acl_anthology import Anthology
from acl_anthology.collections import Paper
from acl_anthology.collections.types import PaperType, VolumeType
from acl_anthology.files import AudioReference, URLReference, VideoReference

log = logging.getLogger(__name__)

if __package__:
    from ..ingest_media import protected_title
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ingest_media import protected_title


def talk_type(title: str) -> PaperType:
    """Classify only explicitly named genres; otherwise retain a generic talk."""
    title = title.casefold()
    if "keynote" in title:
        return PaperType.KEYNOTE
    if "plenary" in title:
        return PaperType.PLENARY
    if "business meeting" in title:
        return PaperType.MEETING
    if title.startswith("panel"):
        return PaperType.PANEL
    if "lecture" in title:
        return PaperType.LECTURE
    if any(
        word in title
        for word in ("opening session", "closing session", "awards", "award session")
    ):
        return PaperType.CEREMONY
    return PaperType.TALK


def migrate_talks(anthology: Anthology) -> list[Paper]:
    """Migrate all legacy talks in memory; safe to rerun after saving."""
    events = [event for event in anthology.events.values() if event.talks]
    for event in events:
        if "media" in event.collection:
            raise ValueError(f"Media volume already exists in {event.collection_id}")
    created = []
    for event in events:
        venue_id, year = event.id.rsplit("-", 1)
        originals = list(event.collection.volumes())
        volume = event.collection.create_volume(
            "media",
            title=protected_title(
                f"{anthology.venues[venue_id].acronym} {year}: Talks and Meetings"
            ),
            type=VolumeType.MEDIA,
            venue_ids=[venue_id],
            publisher=originals[0].publisher if originals else None,
            month=originals[0].month if originals else None,
            address=event.location,
            ingest_date=date.today(),
        )
        for number, talk in enumerate(event.talks, 1):
            videos = []
            audios = []
            links = []
            for kind, ref in talk.attachments.items():
                if kind == "video":
                    videos.append(VideoReference(ref.name))
                elif kind == "audio":
                    audios.append(AudioReference(ref.name))
                else:
                    links.append((kind, URLReference(ref.url)))
            speakers = list(dict.fromkeys(talk.speakers))
            if len(speakers) != len(talk.speakers):
                log.warning(
                    "Collapsing identical duplicate creators on %s-media.%s",
                    event.collection_id,
                    number,
                )
            item = volume.create_media(
                id=str(number),
                title=protected_title(talk.title),
                type=PaperType(talk.type)
                if talk.type
                else talk_type(talk.title.as_text()),
                authors=[evolve(speaker, parent=None) for speaker in speakers],
                videos=videos,
                audios=audios,
                urls=links,
            )
            created.append(item)
        event.talks = []
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    anthology = Anthology.from_within_repo()
    items = migrate_talks(anthology)
    for item in items:
        print(f"{item.full_id}: {item.title.as_text()}")
    if not args.dry_run:
        anthology.save_all()
        for collection_id in {item.collection_id for item in items}:
            anthology.get_collection(collection_id).validate_schema()
    print(f"{'Would migrate' if args.dry_run else 'Migrated'} {len(items)} recordings.")


if __name__ == "__main__":
    main()
