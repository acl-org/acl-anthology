#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2026 Marcel Bollmann <marcel@bollmann.me>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Usage: create_hugo_data.py [--importdir=DIR] [--exportdir=DIR] [options]

Creates Hugo data files containing all necessary Anthology data for the website generation.

This will write JSON data files to `{exportdir}/data/` as well as volume-level BibTeX files
to `{exportdir}/data-export/volumes/`.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../data/]
  --exportdir=DIR          Directory to write build files to.   [default: {scriptdir}/../build/]
  --bib-limit=N            Only generate bibliographic information for the first N papers per volume.
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -n, --dry-run            Do not write data files (useful for debugging).
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from collections import Counter
from functools import cache
import logging as log
import msgspec
from omegaconf import OmegaConf
import os
from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
import shutil

from acl_anthology import Anthology, config
from acl_anthology.collections.paper import PaperDeletionType
from acl_anthology.collections.volume import VolumeType
from acl_anthology.utils.logging import setup_rich_logging
from acl_anthology.utils.ids import is_verified_person_id
from acl_anthology.utils.text import (
    interpret_pages,
    month_str2num,
    remove_extra_whitespace,
)

BIBLIMIT = None
CONSOLE = Console(stderr=True)
ENCODER = msgspec.json.Encoder()
SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


def check_directory(cdir, clean=False):
    if not os.path.isdir(cdir) and not os.path.exists(cdir):
        os.makedirs(cdir)
        return True
    entries = os.listdir(cdir)
    if "_index.md" in entries:
        entries.remove("_index.md")
    if entries and not clean:
        log.critical("Directory already exists and has content files: {}".format(cdir))
        log.info(
            "Call this script with the -c/--clean flag to automatically DELETE existing files"
        )
        return False
    for entry in entries:
        entry = "{}/{}".format(cdir, entry)
        if os.path.isdir(entry):
            shutil.rmtree(entry)
        else:
            os.remove(entry)
    return True


def make_progress():
    columns = [
        TextColumn("[progress.description]{task.description:25s}"),
        BarColumn(),
        TaskProgressColumn(show_speed=True),
        TimeRemainingColumn(elapsed_when_finished=True),
    ]
    return Progress(*columns, console=CONSOLE)


@cache
def person_to_dict(person_id, ns):
    full_name = ns.name.as_full()
    if ns.variants:
        full_name = f"{full_name} ({', '.join(var.as_full() for var in ns.variants)})"
    return {
        "id": person_id,
        "first": ns.first,
        "last": ns.last,
        "full": full_name,
    }


def paper_to_dict(paper):
    """
    Turn a single paper into a dictionary as used by the Hugo templates.
    """
    data = {
        "bibkey": paper.bibkey,
        "bibtype": paper.bibtype,
        "ingest_date": paper.get_ingest_date().isoformat(),
        "paper_id": paper.id,
        "title": paper.title.as_text(),
        "title_html": remove_extra_whitespace(paper.title.as_html(allow_url=False)),
        "title_raw": paper.title.as_xml(),
        # Slightly funky logic: If there is an external URL given for a paper,
        # it will be in '.pdf', even though we use the Anthology landing page
        # (and not the PDF URL) for everything else
        "url": paper.web_url if (not paper.pdf or paper.pdf.is_local) else paper.pdf.url,
        "citation": paper.to_markdown_citation(),
        "citation_acl": paper.to_citation(),
    }
    editors = [
        person_to_dict(paper.root.resolve(ns).id, ns) for ns in paper.get_editors()
    ]
    if BIBLIMIT is None or int(paper.id) <= BIBLIMIT:
        data["bibtex"] = paper.to_bibtex(with_abstract=True)
    if paper.is_frontmatter:
        # Editors are considered authors for the frontmatter
        if editors:
            data["author"] = editors
    else:
        if paper.authors:
            data["author"] = [
                person_to_dict(paper.root.resolve(ns).id, ns) for ns in paper.authors
            ]
        if editors:
            data["editor"] = editors
    if "author" in data:
        data["author_string"] = ", ".join(author["full"] for author in data["author"])
    for key in ("doi", "issue", "journal", "note"):
        # TODO: Keys 'issue' and 'journal' are currently unused on Hugo templates
        if (value := getattr(paper, key)) is not None:
            data[key] = value
    # Frontmatter inherits DOI from volume ... not sure if it should, and this is a bit messy
    if (
        paper.is_frontmatter
        and "doi" not in data
        and (value := paper.parent.doi) is not None
    ):
        data["doi"] = value
    if (language_name := paper.language_name) is not None:
        data["language"] = language_name
    if (abstract := paper.abstract) is not None:
        data["abstract_html"] = remove_extra_whitespace(abstract.as_html())
        data["abstract_raw"] = abstract.as_xml()
    if paper.attachments:
        data["attachment"] = [
            {
                "filename": attachment[1].name,
                "type": attachment[0].capitalize() if attachment[0] else "Attachment",
                "url": attachment[1].url,
            }
            for attachment in paper.attachments
            if attachment[0] != "mrf"  # exclude <mrf>
        ]
    if paper.awards:
        data["award"] = paper.awards
    if paper.deletion:
        match paper.deletion.type:
            case PaperDeletionType.RETRACTED:
                data["retracted"] = paper.deletion.note if paper.deletion.note else " "
                data["title"] = f"[RETRACTED] {data['title']}"
                data["title_html"] = f"[RETRACTED] {data['title_html']}"
            case PaperDeletionType.REMOVED:
                data["removed"] = paper.deletion.note if paper.deletion.note else " "
                data["title"] = f"[REMOVED] {data['title']}"
                data["title_html"] = f"[REMOVED] {data['title_html']}"
    if paper.pages is not None:
        page_first, page_last = interpret_pages(paper.pages)
        data["page_first"] = page_first
        data["page_last"] = page_last
        if page_first != page_last:
            # Ensures consistent formatting of page range strings
            data["pages"] = f"{page_first}–{page_last}"
        else:
            data["pages"] = page_first
    if paper.pdf is not None:
        data["pdf"] = paper.pdf.url
        data["thumbnail"] = paper.thumbnail.url
    if paper.errata:
        data["erratum"] = [
            {
                "id": erratum.id,
                "url": erratum.pdf.url,
                "value": erratum.pdf.name,
            }
            for erratum in paper.errata
        ]
    if paper.revisions:
        data["revision"] = [
            {
                "explanation": revision.note,
                "id": revision.id,
                "url": revision.pdf.url,
                "value": revision.pdf.name,
            }
            for revision in paper.revisions
        ]
    if paper.videos:
        videos = [video.url for video in paper.videos if video.permission]
        if videos:
            data["video"] = videos
    return data


def volume_to_dict(volume):
    """
    Turn a single volume into a dictionary as used by the Hugo templates.
    """
    data = {
        "has_abstracts": volume.has_abstracts,
        "meta_date": volume.year,  # may be overwritten below
        "papers": [paper.full_id for paper in volume.papers()],
        "title": volume.title.as_text(),
        "title_html": remove_extra_whitespace(volume.title.as_html(allow_url=False)),
        "title_raw": volume.title.as_xml(),
        "year": volume.year,
        "sigs": [],
        "url": (
            volume.web_url if (not volume.pdf or volume.pdf.is_local) else volume.pdf.url
        ),
        "venues": volume.venue_ids,
    }
    for key in ("address", "doi", "isbn", "publisher"):
        if (value := getattr(volume, key)) is not None:
            data[key] = value
    if volume.month:
        data["month"] = volume.month
        if (month_str := month_str2num(volume.month)) is not None:
            data["meta_date"] = f"{volume.year}/{month_str}"
    if volume.shorttitle:
        data["shortbooktitle"] = volume.shorttitle.as_text()
    if volume.editors:
        data["editor"] = [
            person_to_dict(volume.root.resolve(ns).id, ns) for ns in volume.editors
        ]
    if events := volume.get_events():
        data["events"] = [event.id for event in events if event.is_explicit]
    if sigs := volume.get_sigs():
        data["sigs"] = [sig.acronym for sig in sigs]
    if volume.type == VolumeType.JOURNAL:
        data["meta_journal_title"] = volume.get_journal_title()
        data["meta_issue"] = volume.journal_issue
        data["meta_volume"] = volume.journal_volume
    if volume.pdf is not None:
        data["pdf"] = volume.pdf.url
    return data


def export_papers_and_volumes(anthology, builddir, dryrun):
    all_volumes = {}
    with make_progress() as progress:
        paper_count = sum(1 for _ in anthology.papers())
        task = progress.add_task("Exporting papers...", total=paper_count)
        for collection in anthology.collections.values():
            collection_papers = {}
            volume_bibtex = {}
            for volume in collection.volumes():
                # Compute volume-level information that gets appended to every paper
                # TODO: Could this be changed in the Hugo templates to
                # fetch the information from the volume, instead of duplicating
                # this information on every paper?
                # --- this also applies to some information from paper_to_dict()
                # which may be fetched from the volume if not set for the paper
                volume_bibtex[volume.full_id] = []
                volume_data = {
                    "booktitle": volume.title.as_text(),
                    "parent_volume_id": volume.full_id,
                    "year": volume.year,
                    "venue": volume.venue_ids,
                }
                for key in ("address", "publisher", "isbn", "month"):
                    if (value := getattr(volume, key)) is not None:
                        volume_data[key] = value
                if events := volume.get_events():
                    # TODO: This information is currently not used on paper templates
                    volume_data["events"] = [
                        event.id for event in events if event.is_explicit
                    ]

                # Now build the data for every paper
                for paper in volume.papers():
                    data = paper_to_dict(paper)
                    data.update(volume_data)
                    collection_papers[paper.full_id] = data
                    if "bibtex" in data:
                        volume_bibtex[volume.full_id].append(
                            paper.to_bibtex(with_abstract=False)
                        )

                # We build the volume data separately since it uses slightly
                # different fields than what gets attached to papers
                all_volumes[volume.full_id] = volume_to_dict(volume)

            if not dryrun:
                with open(f"{builddir}/data/papers/{collection.id}.json", "wb") as f:
                    f.write(ENCODER.encode(collection_papers))

                for volume_id, bibtex in volume_bibtex.items():
                    with open(
                        f"{builddir}/data-export/volumes/{volume_id}.bib", "w"
                    ) as f:
                        print("\n".join(bibtex), file=f)

            progress.update(task, advance=len(collection_papers))

    # Export volumes
    if not dryrun:
        with open(f"{builddir}/data/volumes.json", "wb") as f:
            f.write(ENCODER.encode(all_volumes))


def export_people(anthology, builddir, dryrun):
    with make_progress() as progress:
        # Just to make progress bars nicer
        ppl_count = sum(1 for _ in anthology.people.items())
        if not dryrun:
            ppl_count += 100
        task = progress.add_task("Exporting people...", total=ppl_count)

        # Here begins the actual serialization
        people = {}
        for person_id, person in anthology.people.items():
            cname = person.canonical_name
            papers = sorted(
                person.papers(),
                key=lambda paper: paper.year,
                reverse=True,
            )
            data = {
                "first": cname.first,
                "last": cname.last,
                "full": cname.as_full(),
                "slug": person_id,
                "papers": [paper.full_id for paper in papers],
                "coauthors": sorted(
                    anthology.people.find_coauthors_counter(
                        person, include_volumes=False
                    ).most_common(),
                    key=lambda item: (
                        -item[1],
                        anthology.people[item[0]].canonical_name.last,
                    ),
                ),
                "venues": sorted(
                    Counter(
                        venue for paper in papers for venue in paper.venue_ids
                    ).most_common(),
                    key=lambda item: (-item[1], item[0]),
                ),
            }
            if len(person.names) > 1:
                data["variant_entries"] = []
                diff_script_variants = []
                for n in person.names[1:]:
                    data["variant_entries"].append(
                        {"first": n.first, "last": n.last, "full": n.as_full()}
                    )
                    if n.script is not None:
                        diff_script_variants.append(n.as_full())
                if diff_script_variants and is_verified_person_id(person_id):
                    data["full"] = f"{data['full']} ({', '.join(diff_script_variants)})"
            if person.comment is not None:
                data["comment"] = person.comment
            if person.orcid is not None:
                data["orcid"] = person.orcid
            similar = anthology.people.similar.subset(person_id)
            similar.remove(person_id)
            if similar_verified := [id_ for id_ in similar if is_verified_person_id(id_)]:
                data["similar_verified"] = sorted(list(similar_verified))
                similar.difference_update(similar_verified)
            if similar:  # any remaining IDs are unverified
                data["similar_unverified"] = sorted(list(similar))
            people[person_id] = data
            progress.update(task, advance=1)

        # Generate redirects _iff_ there's a slug to a verified ID that does not
        # correspond to an existing (verified OR unverified) person ID
        extra_slugs = set(anthology.people.slugs_to_verified_ids.keys()) - set(
            pid.replace("/unverified", "") for pid in people.keys()
        )
        for slug in extra_slugs:
            ids = anthology.people.slugs_to_verified_ids[slug]
            if len(ids) > 1:
                target_id = sorted(
                    ids,
                    key=lambda pid: len(list(anthology.people[pid].anthology_items())),
                )[-1]
            else:
                target_id = list(ids)[0]
            if "aliases" in people[target_id]:
                people[target_id]["aliases"].append(slug)
            else:
                people[target_id]["aliases"] = [slug]

        if not dryrun:
            with open(f"{builddir}/data/people.json", "wb") as f:
                f.write(ENCODER.encode(people))
            progress.update(task, advance=100)


def export_venues(anthology, builddir, dryrun):
    all_venues = {}
    print("Exporting venues...")
    for venue_id, venue in anthology.venues.items():
        data = {
            "acronym": venue.acronym,
            "is_acl": venue.is_acl,
            "is_toplevel": venue.is_toplevel,
            "name": venue.name,
            # Note: 'slug' was produced with a separate function in the old
            # library, but in practice it's always just the venue_id — maybe we
            # can refactor this in the depending code as well to just use the
            # venue_id, and get rid of this attribute
            "slug": venue_id,
        }
        if venue.oldstyle_letter is not None:
            data["oldstyle_letter"] = venue.oldstyle_letter
        if venue.url is not None:
            data["url"] = venue.url
        if venue.type is not None:
            data["type"] = venue.type
        data["volumes_by_year"] = {}
        for volume in venue.volumes():
            year, volume_id = volume.year, volume.full_id
            try:
                data["volumes_by_year"][year].append(volume_id)
            except KeyError:
                data["volumes_by_year"][year] = [volume_id]
        data["years"] = sorted(list(data["volumes_by_year"].keys()))
        all_venues[venue_id] = data

    if not dryrun:
        with open(f"{builddir}/data/venues.json", "wb") as f:
            f.write(ENCODER.encode(all_venues))


def export_events(anthology, builddir, dryrun):
    # Export events
    all_events = {}
    print("Exporting events...")
    for event in anthology.events.values():
        # TODO: This should probably be refactored
        # (but functionally it's how it's done in the old library)
        main_venue, year = event.id.split("-")
        if main_venue not in anthology.venues:
            log.error(
                f"Event {event.id} has inferred venue {main_venue}, which doesn't exist"
            )
            continue

        data = {
            "venue": main_venue,
            "links": [
                {link_type.capitalize(): ref.url}
                for link_type, ref in event.links.items()
            ],
            "year": year,
        }
        if event.location:
            data["location"] = event.location
        if event.dates:
            data["dates"] = event.dates

        volume_ids = []
        for volume in event.volumes():
            # Default sort order: alphabetically by venue ID
            sort_order = min(volume.venue_ids)
            if main_venue in volume.venue_ids:
                # Volumes in main venue should come first
                sort_order = f"{volume.venue_ids.index(main_venue):04d}"
            elif ".findings" in volume.parent.id:
                # Findings should come next, but before any remaining venues
                sort_order = "0100"
            elif main_venue == volume.id:
                # This was the previous criterion for being moved "to the top"
                # of the workshop, and it may have been used intentionally for
                # that purpose (e.g. 2020.nlpcovid19-acl)?
                sort_order = "0200"
            volume_ids.append((sort_order, volume.full_id))
        data["volumes"] = [tuples[1] for tuples in sorted(volume_ids, key=lambda x: x[0])]

        if event.title is not None:
            data["title"] = event.title.as_text()
        else:
            data["title"] = f"{anthology.venues[main_venue].name} ({data['year']})"

        # Add talks data if available
        talks_data = []
        for idx, talk in enumerate(event.talks or [], 1):
            # Generate talk ID from video filename if available, otherwise use default pattern
            if "video" in talk.attachments and talk.attachments["video"].name:
                # Extract talk ID from video filename like "2022.acl-keynote.2.mp4"
                video_name = talk.attachments["video"].name
                if video_name.endswith(".mp4"):
                    # Remove .mp4 extension to get the talk ID
                    talk_id = video_name[:-4]
                else:
                    talk_id = video_name
            else:
                # Fallback to sequential numbering if no video
                talk_id = f"{event.id}.talk-{idx}"

            talk_data = {
                "id": talk_id,
                "title": talk.title.as_text(),
                "title_html": remove_extra_whitespace(
                    talk.title.as_html(allow_url=False)
                ),
                "speakers": [],  # Process speakers differently
                "type": talk.type,
            }
            # Process speakers - NameSpecification objects
            for speaker in talk.speakers:
                speaker_dict = person_to_dict(speaker.id if speaker.id else "", speaker)
                talk_data["speakers"].append(speaker_dict)
            # Add video URL if available
            if "video" in talk.attachments:
                talk_data["video_url"] = talk.attachments["video"].url
            # Add other attachments
            attachments = []
            for att_type, attachment in talk.attachments.items():
                if att_type != "video":
                    attachments.append(
                        {
                            "filename": attachment.name,
                            "type": att_type.capitalize(),
                            "url": attachment.url,
                        }
                    )
            if attachments:
                talk_data["attachments"] = attachments
            talks_data.append(talk_data)
        if talks_data:
            data["talks"] = talks_data

        all_events[event.id] = data

    if not dryrun:
        with open(f"{builddir}/data/events.json", "wb") as f:
            f.write(ENCODER.encode(all_events))


def export_talks(anthology, builddir, dryrun):
    # Export talks data
    all_talks = {}
    print("Exporting talks...")

    for event in anthology.events.values():
        if not event.talks:
            continue

        for idx, talk in enumerate(event.talks, 1):
            # Generate talk ID from video filename if available, otherwise use default pattern
            if "video" in talk.attachments and talk.attachments["video"].name:
                # Extract talk ID from video filename like "2022.acl-keynote.2.mp4"
                video_name = talk.attachments["video"].name
                if video_name.endswith(".mp4"):
                    # Remove .mp4 extension to get the talk ID
                    talk_id = video_name[:-4]
                else:
                    talk_id = video_name
            else:
                # Fallback to sequential numbering if no video
                talk_id = f"{event.id}.talk-{idx}"

            # Create talk data
            talk_data = {
                "id": talk_id,
                "event_id": event.id,
                "event_title": event.title.as_text() if event.title else f"{event.id}",
                "title": talk.title.as_text(),
                "title_html": remove_extra_whitespace(
                    talk.title.as_html(allow_url=False)
                ),
                "speakers": [],
                "type": talk.type,
            }

            # Process speakers
            for speaker in talk.speakers:
                speaker_data = person_to_dict(speaker.id if speaker.id else "", speaker)
                talk_data["speakers"].append(speaker_data)

            # Add video URL if available
            if "video" in talk.attachments:
                talk_data["video_url"] = talk.attachments["video"].url
                talk_data["video_name"] = talk.attachments["video"].name

            # Add other attachments
            attachments = []
            for att_type, attachment in talk.attachments.items():
                if att_type != "video":
                    attachments.append(
                        {
                            "filename": attachment.name,
                            "type": att_type.capitalize(),
                            "url": attachment.url,
                        }
                    )
            if attachments:
                talk_data["attachments"] = attachments

            # Add location and dates from event
            if event.location:
                talk_data["location"] = event.location
            if event.dates:
                talk_data["dates"] = event.dates

            all_talks[talk_id] = talk_data

    if not dryrun:
        with open(f"{builddir}/data/talks.json", "wb") as f:
            f.write(ENCODER.encode(all_talks))


def export_sigs(anthology, builddir, dryrun):
    all_sigs = {}
    print("Exporting SIGs...")
    for sig in anthology.sigs.values():
        data = {
            "name": sig.name,
            "slug": sig.id,
            "volumes_by_year": {},
        }
        if sig.url is not None:
            data["url"] = sig.url
        for year, meetings in sig.get_meetings_by_year().items():
            data["volumes_by_year"][year] = []
            for meeting in meetings:
                if isinstance(meeting, str):
                    data["volumes_by_year"][year].append(meeting)
                else:  # SIGMeeting
                    sigmeeting = {"name": meeting.name}
                    if meeting.url is not None:
                        sigmeeting["url"] = meeting.url
                    data["volumes_by_year"][year].append(sigmeeting)
        data["years"] = sorted(list(data["volumes_by_year"].keys()))
        all_sigs[sig.acronym] = data

    if not dryrun:
        with open(f"{builddir}/data/sigs.json", "wb") as f:
            f.write(ENCODER.encode(all_sigs))


def export_anthology(anthology, builddir, clean=False, dryrun=False):
    """
    Dumps files in build/data/*.json, which are used by Hugo templates
    to generate the website, as well as build/data-export/volumes/*.bib,
    which are used later as a basis to generate more bibliographic files.
    """
    # Create directories
    if not dryrun:
        for subdir in ("", "papers", "people"):
            target_dir = "{}/data/{}".format(builddir, subdir)
            if not check_directory(target_dir, clean=clean):
                return
        for subdir in ("", "volumes"):
            target_dir = "{}/data-export/{}".format(builddir, subdir)
            if not check_directory(target_dir, clean=clean):
                return

    export_papers_and_volumes(anthology, builddir, dryrun)
    export_people(anthology, builddir, dryrun)
    export_venues(anthology, builddir, dryrun)
    export_events(anthology, builddir, dryrun)
    export_talks(anthology, builddir, dryrun)
    export_sigs(anthology, builddir, dryrun)


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )
    if "{scriptdir}" in args["--exportdir"]:
        args["--exportdir"] = os.path.abspath(
            args["--exportdir"].format(scriptdir=scriptdir)
        )

    log_level = log.DEBUG if args["--debug"] else log.INFO
    tracker = setup_rich_logging(console=CONSOLE, level=log_level)

    if limit := args["--bib-limit"]:
        BIBLIMIT = int(limit)

    # This "freezes" the config, resulting in a massive speed-up
    OmegaConf.resolve(config)

    anthology = Anthology(datadir=args["--importdir"]).load_all()
    if tracker.highest >= log.ERROR:
        exit(1)

    export_anthology(
        anthology, args["--exportdir"], clean=args["--clean"], dryrun=args["--dry-run"]
    )
    if tracker.highest >= log.ERROR:
        exit(1)
