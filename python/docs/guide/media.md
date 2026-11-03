# Citable media

!!! warning "Prototype: the library model is still under review"

    This implementation still represents media as paper records. The [CollectionItem refactor (#8000)](https://github.com/acl-org/acl-anthology/issues/8000) and a distinct media representation must be resolved before migrating publication metadata. The metadata migration is reviewed in a separate, dependent PR.

## Design

Standalone recordings are **citable records in dedicated media volumes**.
For example, `2023.acl-media.1` is an item in the `media` volume of `2023.acl`,
and its landing page is `/2023.acl-media.1/`. A podcast can have annual
collections such as the fictional `2026.fictionalpodcast`, containing an `episodes` volume.
The existing venue index also serves as the index of a recurring media series.

This replaces the event-only approach proposed in
[PR #5612](https://github.com/acl-org/acl-anthology/pull/5612):

- IDs are explicitly persisted, not reconstructed from a filename or a talk's
  position at build time. Replacing a recording, editing a title, or reordering
  entries must not change its ID. Never reuse an ID for a different item.
- Audio and video are formats, independent of genre: a meeting, keynote,
  panel, or podcast episode can have either or both, and multiple recordings.
- The existing bibliographic record class, `Paper`, is retained for API
  compatibility. `PaperType` identifies the genre; `is_media` distinguishes
  standalone recordings from scholarly papers. `Volume.create_media()` performs
  the same name normalization, ORCID ingestion, person indexing, and unique
  citation-key assignment as `create_paper()`.
- Citations point to the landing page, not a mutable recording URL. BibTeX
  uses portable `@misc` entries, CSL uses `speech`, `broadcast` (podcasts), or
  `motion_picture` (generic video), and human-readable citations identify the
  genre, format, series, and episode when available. They do not claim that a
  recording is a proceedings paper.
- Pages reuse the existing citation/export infrastructure, including volume
  and consolidated BibTeX, MODS, and Endnote. Media additionally offer CSL-JSON
  and Schema.org metadata.
- Recordings are discoverable from `/media/`, event pages, series/volume pages,
  and a separate section on each contributor's person page. Paper counts,
  publication-year authorship metrics, and paper coauthor lists exclude media.
- A recording of an existing paper remains attached to that paper. Do not
  create a second citable record solely because a paper has a presentation.
  The API permits media in a proceedings volume for exceptional mixed
  collections, but dedicated media volumes are the authoring convention.

The shared model avoids a second, incompatible identifier and author system,
without requiring a breaking rename of the library's `Paper` API.
Existing `papers()` iterators include **all citable records**, as do `get()`
and citation-key lookups. Filter `not item.is_media` when counting papers, or
use `Anthology.media()`, `Volume.media()`, `Event.media()`, and `Person.media()`
to select recordings.

## Genres and metadata

Supported `PaperType` media genres are `MEDIA`, `TALK`, `KEYNOTE`, `PLENARY`,
`PANEL`, `MEETING`, `PODCAST`, `TUTORIAL`, `INTERVIEW`, `LECTURE`, and `CEREMONY`.
These cover invited and presidential addresses, business meetings, fireside
chats, oral histories, award sessions, and opening/closing sessions as well.

Use the credited creators, in source order, as `authors`. For a podcast this
may include hosts and guests; use the episode's own attribution rather than
guessing roles or identities. Names resolve through the ordinary verified and
unverified person system. An organizer or institution can be the `publisher`;
meetings without individually credited creators are supported.

Optional metadata includes:

| API field | Meaning |
|-----------|---------|
| `publication_date` | Exact public release date, `YYYY-MM-DD`. This determines the media citation year even when a recording is released after the event's year. Do not invent a day from an event's date range. |
| `episode` | Source episode identifier, independent of the Anthology item number; e.g. `"142"` or `"S2E4"`. |
| `duration` | Positive integer duration in seconds. |
| `license` | URL describing a known license. Absence does not imply an open license. |
| `language` | Recording language, using the existing language-code convention. |
| `abstract` | Reviewed description or summary, not an automatically generated transcript. |
| `urls` | Typed links, e.g. `slides`, `transcript`, `captions`, `paper`, `source`, or `website`. |
| `doi` | An already assigned DOI, if applicable. Conference DOI automation deliberately skips media. |

### Recording references and permissions

`VideoReference` and `AudioReference` accept an existing Anthology filename
(including its extension) or an absolute URL. Local references resolve through
`video_location_template` and `audio_location_template`. Files do not have to
be renamed to match a new record's ID, especially when preserving legacy URLs.

Only references with `permission=True` and `available=True` are published in Hugo data, players,
links, and structured metadata. `permission=False` retains metadata without
exposing the recording URL. The record and its citation can remain available.
Permission to display a link or embed is not a license to redistribute a file.
Obtain the necessary permission before uploading or mirroring recordings.
Use stable public URLs, not credentials, signed download URLs, or expiring tokens.

Native players support common audio/video file formats; recognized HTTPS
YouTube and Vimeo URLs use provider embeds, and other URLs remain usable links.
Players never autoplay. Captions, transcripts, and slides can be linked even
when no recording is available. If all recordings are unavailable, the page
says so explicitly.

Availability is independent of permission: `available=False` preserves a
missing recording's locator and citation without rendering a broken player
or claiming permission was withheld. Restore it to `True` after recovering
the file or verifying a replacement. Builds do not make network requests to
check recordings; availability is curated metadata.

## Creating records with the library

Run scripts inside the checkout with `uv run`:

```python
from acl_anthology import Anthology
from acl_anthology.collections.types import PaperType, VolumeType
from acl_anthology.files import VideoReference
from acl_anthology.people import Name, NameSpecification

anthology = Anthology.from_within_repo()
collection = anthology.get_collection("2026.acl")
volume = collection.create_volume(
    "media",
    title="ACL 2026: Talks and Meetings",
    type=VolumeType.MEDIA,
    venue_ids=["acl"],
)
item = volume.create_media(
    id="1",
    title="An invited presentation",
    type=PaperType.KEYNOTE,
    authors=[NameSpecification(Name("Example", "Speaker"))],
    videos=[VideoReference("2026.acl-media.1.mp4", permission=True)],
)
anthology.save_all()
```

The names and title above are placeholders, not actual conference metadata.
For ingestion, prefer the manifest workflow below: it additionally applies
the same fixed-case title protection as proceedings ingestion.

## Ingesting a podcast or other series

Register a new series once through the public venue API, after reviewing its
metadata. The following series and its metadata are entirely fictional:

```python
anthology.venues.create(
    "fictionalpodcast",
    acronym="Fictional Podcast",
    name="Fictional Podcast",
    type="media",
)
anthology.save_all()
```

Then prepare a reviewed JSON manifest. This **fabricated example** demonstrates
the shape; replace it with verified episode metadata and recording references:

```json
{
  "collection": "2026.fictionalpodcast",
  "volume": "episodes",
  "title": "Fictional Podcast (2026)",
  "venue": "fictionalpodcast",
  "items": [
    {
      "id": "1",
      "title": "An example episode about NLP",
      "type": "podcast",
      "creators": [{"first": "Example", "last": "Speaker"}],
      "publication_date": "2026-01-15",
      "episode": "142",
      "duration": 3600,
      "audios": [
        {"href": "https://example.org/episode-142.mp3", "permission": true}
      ],
      "links": [
        {"type": "source", "url": "https://example.org/episodes/142"}
      ]
    }
  ]
}
```

```bash
uv run bin/ingest_media.py episodes.json --dry-run
uv run bin/ingest_media.py episodes.json
```

`publisher` and an existing `event` ID are optional top-level fields. The
latter explicitly links the volume to that event, useful for colocated media.
`videos` and `audios` accept arrays with the same `href`/`permission` shape,
plus optional `available` (default `true`).
Creators can include an existing verified `id` and/or an `orcid`.

The importer rejects unknown fields, missing permission decisions, duplicate
or existing IDs, unknown venues/events, invalid genres/dates, and conflicting
volume metadata. It appends to a matching media volume, never silently
overwrites entries, and saves only after all entries have been constructed.
It does not fetch podcast feeds, download/upload recordings, invent attribution,
or grant redistribution rights. A reviewed metadata manifest keeps archive
curation separate from a changing feed or podcast-hosting service.

## Legacy event talks

`bin/oneoff/migrate_talks.py` promotes the old `<event><talk>` entries into one
`media` volume per collection. It assigns numeric IDs once, keeps titles,
creators, links, and original recording filenames, and removes only the
promoted event-talk entries. Explicitly named genres are preserved/classified;
otherwise entries remain generic talks. It preflights volume collisions and
is a no-op after a successful migration. Identical duplicate creator entries
are collapsed, without removing distinct name specifications.

Recording-file corrections and availability flags belong in the separate
metadata migration, after the library representation is settled. Verify hosted
filenames, including corrections from PR #5612, rather than inventing replacement
URLs for missing recordings.

```bash
uv run bin/oneoff/migrate_talks.py --dry-run
uv run bin/oneoff/migrate_talks.py
```

Legacy `<talk>` parsing remains supported for library compatibility, but new
recordings should use `create_media()` rather than anonymous event talks.
No redirects from the unmerged PR's provisional `/talks/` URLs are needed:
those were never published canonical identifiers.
