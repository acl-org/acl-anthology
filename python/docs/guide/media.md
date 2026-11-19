# Citable media

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
- `CollectionItem` is the shared interface for persistent IDs, collection
  ownership, contributor specifications, and person links. Volumes and the
  distinct `Paper`, `Frontmatter`, and `Media` record types implement it.
  Their shared `Record` base supplies metadata views and citation machinery,
  not a shared XML tag or paper identity.
- `Media` is never a `Paper`: it serializes as `<media id="..." type="...">`.
  `MediaType` identifies its genre. `Volume.create_media()` performs the
  same normalization, ORCID ingestion, person indexing, and unique
  citation-key assignment as the other record factories.
- `Frontmatter` has its own restricted fields and `<frontmatter>` serializer.
  Its title and credited editors follow the parent volume. It is created with
  `Volume.create_frontmatter()`, not by changing a paper's type.
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

### Selecting items

`Anthology.items()` includes identified volumes and their records.
`Anthology.records()`, `Collection.records()`, `Volume.records()`, and
`Person.records()` select all bibliographic records, including frontmatter and
media. `papers()` selects printed papers only; `media()` selects media only.
Contributor pages also show edited volumes that have no frontmatter.

Use `get_record()` or `get_record_by_bibkey()` for a generic record lookup,
and `get_media()` or `get_frontmatter()` for those specific types.
`get_paper()` and `get_paper_by_bibkey()` do not return frontmatter or media.
Existing identifiers, including frontmatter's `.0`, remain unchanged.

These are intentional API changes from the former all-purpose `Paper` model.
Callers that previously used `papers()` or `get_paper()` to include frontmatter
must use the generic record APIs. Legacy `create_paper(id="0")` and the
`PaperType.FRONTMATTER` factory selector still delegate to `create_frontmatter()`;
directly constructing or retyping a `Paper` as frontmatter is not supported.

## Genres and metadata

Supported `MediaType` media genres are `MEDIA`, `TALK`, `KEYNOTE`, `PLENARY`,
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
from acl_anthology.collections.types import MediaType, VolumeType
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
    type=MediaType.KEYNOTE,
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
metadata migration, after library review. Verify hosted
filenames, including corrections from PR #5612, rather than inventing replacement
URLs for missing recordings.

```bash
uv run bin/oneoff/migrate_talks.py --dry-run
uv run bin/oneoff/migrate_talks.py
```

Legacy anonymous `<talk>` parsing remains supported for unchanged historical
collections. These compatibility objects have no persistent item ID and are
not exposed by `items()` or contributor indexing. New identified talks are
`Media` records with `MediaType.TALK` and should use `create_media()`.
No redirects from the unmerged PR's provisional `/talks/` URLs are needed:
those were never published canonical identifiers.
