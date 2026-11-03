#!/usr/bin/env python3
"""Ingest a reviewed JSON manifest of standalone recordings.

Usage: uv run bin/ingest_media.py MANIFEST [--dry-run]

References may be existing Anthology filenames or external URLs. This script
does not download, upload, or grant permission to redistribute recordings.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import msgspec

from acl_anthology import Anthology
from acl_anthology.collections import Paper
from acl_anthology.collections.types import PaperType, VolumeType
from acl_anthology.files import AudioReference, URLReference, VideoReference
from acl_anthology.people import Name, NameSpecification
from acl_anthology.text import MarkupText, to_markuptext
from acl_anthology.utils.ids import is_valid_collection_id, is_valid_item_id

if __package__:
    from .fixedcase.protect import protect
else:
    from fixedcase.protect import protect


class Creator(msgspec.Struct, forbid_unknown_fields=True):
    first: str
    last: str
    id: str | None = None
    orcid: str | None = None

    def namespec(self) -> NameSpecification:
        kwargs = {}
        if self.id is not None:
            kwargs["id"] = self.id
        if self.orcid is not None:
            kwargs["orcid"] = self.orcid
        return NameSpecification(Name(self.first, self.last), **kwargs)


class Recording(msgspec.Struct, forbid_unknown_fields=True):
    href: str
    permission: bool
    available: bool = True


class Link(msgspec.Struct, forbid_unknown_fields=True):
    type: str
    url: str


class MediaItem(msgspec.Struct, forbid_unknown_fields=True):
    id: str
    title: str
    type: PaperType = PaperType.MEDIA
    creators: list[Creator] = msgspec.field(default_factory=list)
    videos: list[Recording] = msgspec.field(default_factory=list)
    audios: list[Recording] = msgspec.field(default_factory=list)
    links: list[Link] = msgspec.field(default_factory=list)
    publication_date: str | None = None
    episode: str | None = None
    duration: int | None = None
    abstract: str | None = None
    license: str | None = None
    note: str | None = None
    language: str | None = None
    doi: str | None = None


class MediaManifest(msgspec.Struct, forbid_unknown_fields=True):
    collection: str
    volume: str
    title: str
    venue: str
    items: list[MediaItem]
    publisher: str | None = None
    event: str | None = None


def protected_title(text: MarkupText | str) -> MarkupText:
    """Apply the same capitalization protection as proceedings ingestion."""
    element = to_markuptext(text).to_xml("title")
    protect(element)
    return MarkupText.from_xml(element)


def ingest_media(anthology: Anthology, manifest: MediaManifest) -> list[Paper]:
    """Create media records in memory; the caller explicitly saves after validation."""
    if not is_valid_collection_id(manifest.collection):
        raise ValueError(f"Invalid collection ID: {manifest.collection}")
    if not manifest.items:
        raise ValueError("A media manifest must contain at least one item")
    if manifest.venue not in anthology.venues:
        raise ValueError(f"Unknown venue/series: {manifest.venue}")
    if manifest.event is not None and anthology.get_event(manifest.event) is None:
        raise ValueError(f"Unknown event: {manifest.event}")
    ids = [item.id for item in manifest.items]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate item IDs in media manifest")
    for item in manifest.items:
        if not is_valid_item_id(item.id) or not item.id.isdecimal() or int(item.id) < 1:
            raise ValueError(f"Invalid media item ID: {item.id}")
        if not item.type.is_media:
            raise ValueError(f"Not a media type: {item.type}")
        if not item.videos and not item.audios:
            raise ValueError(f"Media item {item.id} has no recording references")
        if not item.title.strip():
            raise ValueError(f"Media item {item.id} has an empty title")
        if any(not ref.href.strip() for ref in (*item.videos, *item.audios)):
            raise ValueError(f"Media item {item.id} has an empty recording reference")
    collection = anthology.get_collection(manifest.collection)
    if collection is None:
        collection = anthology.create_collection(manifest.collection)
    volume = collection.get(manifest.volume)
    title = protected_title(manifest.title)
    if volume is None:
        volume = collection.create_volume(
            manifest.volume,
            title=title,
            type=VolumeType.MEDIA,
            venue_ids=[manifest.venue],
            publisher=manifest.publisher,
            ingest_date=date.today(),
        )
    elif (
        volume.type != VolumeType.MEDIA
        or volume.title.as_text() != title.as_text()
        or volume.venue_ids != (manifest.venue,)
        or volume.publisher != manifest.publisher
    ):
        raise ValueError(f"Existing volume {volume.full_id} has different metadata")
    for item in manifest.items:
        if item.id in volume:
            raise ValueError(f"Item already exists: {volume.full_id}.{item.id}")
    created = []
    for item in manifest.items:
        paper = volume.create_media(
            id=item.id,
            title=protected_title(item.title),
            type=item.type,
            authors=[creator.namespec() for creator in item.creators],
            videos=[
                VideoReference(
                    ref.href, permission=ref.permission, available=ref.available
                )
                for ref in item.videos
            ],
            audios=[
                AudioReference(
                    ref.href, permission=ref.permission, available=ref.available
                )
                for ref in item.audios
            ],
            urls=[(link.type, URLReference(link.url)) for link in item.links],
            publication_date=item.publication_date,
            episode=item.episode,
            duration=item.duration,
            abstract=item.abstract,
            license=item.license,
            note=item.note,
            language=item.language,
            doi=item.doi,
            ingest_date=date.today(),
        )
        paper.title.as_html()
        if paper.abstract is not None:
            paper.abstract.as_html()
        created.append(paper)
    if manifest.event is not None:
        anthology.get_event(manifest.event).add_colocated(volume)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = msgspec.json.decode(args.manifest.read_bytes(), type=MediaManifest)
    anthology = Anthology.from_within_repo()
    items = ingest_media(anthology, manifest)
    for item in items:
        print(f"{item.full_id}: {item.title.as_text()}")
    if not args.dry_run:
        anthology.save_all()
        anthology.get_collection(manifest.collection).validate_schema()
    print(f"{'Would ingest' if args.dry_run else 'Ingested'} {len(items)} media items.")


if __name__ == "__main__":
    main()
