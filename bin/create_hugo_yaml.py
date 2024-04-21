#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2024 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: create_hugo_yaml.py [--importdir=DIR] [--exportdir=DIR] [-c] [--debug] [--dry-run]

Creates YAML files containing all necessary Anthology data for the static website generator.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../data/]
  --exportdir=DIR          Directory to write YAML files to.   [default: {scriptdir}/../build/data/]
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -n, --dry-run            Do not write YAML files (useful for debugging).
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from collections import defaultdict
import logging as log
import os
from rich.logging import RichHandler
from rich.progress import Progress
import yaml

try:
    from yaml import CSafeDumper as Dumper
except ImportError:
    from yaml import SafeDumper as Dumper

from acl_anthology import Anthology
from acl_anthology.collections.paper import PaperDeletionType
from acl_anthology.collections.volume import VolumeType
from acl_anthology.utils.logging import SeverityTracker
from acl_anthology.utils.text import interpret_pages, month_str2num
from create_hugo_pages import check_directory


SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))


def person_to_dict(person):
    name = person.canonical_name
    return {
        "id": person.id,
        "first": name.first,
        "last": name.last,
        "full": name.as_first_last(),
    }


def paper_to_dict(paper):
    """
    Turn a single paper into a dictionary suitable for YAML export as expected by Hugo.
    """
    data = {
        "author": [person_to_dict(paper.root.resolve(ns)) for ns in paper.authors],
        "bibkey": paper.bibkey,
        "bibtype": paper.bibtype,
        "editor": [person_to_dict(paper.root.resolve(ns)) for ns in paper.get_editors()],
        "paper_id": paper.id,
        "title": paper.title.as_text(),
        "title_html": paper.title.as_html(),
        "url": paper.web_url,
        "citation": paper.to_markdown_citation(),
        "citation_acl": paper.to_citation(),
    }
    data["author_string"] = ", ".join(author["full"] for author in data["author"])
    for key in ("doi", "language", "note"):
        if (value := getattr(paper, key)) is not None:
            data[key] = value
    if (abstract := paper.abstract) is not None:
        data["abstract_html"] = abstract.as_html()
    if paper.attachments:
        data["attachment"] = [
            {
                "filename": attachment[1].name,
                "type": attachment[0].capitalize(),
                "url": attachment[1].url,
            }
            for attachment in paper.attachments.items()
        ]
    if paper.awards:
        data["award"] = paper.awards
    if paper.deletion:
        match paper.deletion.type:
            case PaperDeletionType.RETRACTED:
                data["retracted"] = paper.deletion.note
                data["title"] = f"[RETRACTED] {data['title']}"
                data["title_html"] = f"[RETRACTED] {data['title_html']}"
            case PaperDeletionType.REMOVED:
                data["removed"] = paper.deletion.note
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
            data["pages"] = paper.pages
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
    if (pwc := paper.paperswithcode) is not None:
        if pwc.code is not None:
            data["pwccode"] = {
                "additional": pwc.community_code,
                "name": pwc.code[0],
                "url": pwc.code[1],
            }
        if pwc.datasets:
            data["pwcdataset"] = [
                {
                    "name": dataset[0],
                    "url": dataset[1],
                }
                for dataset in pwc.datasets
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
        data["video"] = [video.url for video in paper.videos]
    return data


def volume_to_dict(volume):
    """
    Turn a single volume into a dictionary suitable for YAML export as expected by Hugo.
    """
    data = {
        "has_abstracts": volume.has_abstracts,
        "meta_date": volume.year,  # may be overwritten below
        "papers": [paper.full_id for paper in volume.papers()],
        "title": volume.title.as_text(),
        "title_html": volume.title.as_html(),
        "year": volume.year,
        "url": volume.web_url,
        "venues": volume.venue_ids,
    }
    for key in ("address", "doi", "isbn", "publisher"):
        if (value := getattr(volume, key)) is not None:
            data[key] = value
    if volume.month:
        data["month"] = volume.month
        if (month_str := month_str2num(volume.month)) is not None:
            data["meta_date"] = f"{volume.year}/{month_str}"
    if volume.editors:
        data["editor"] = [
            person_to_dict(volume.root.resolve(ns)) for ns in volume.editors
        ]
    if events := volume.get_events():
        data["events"] = [event.id for event in events]
    if sigs := volume.get_sigs():
        data["sigs"] = [sig.acronym for sig in sigs]
    if volume.type == VolumeType.JOURNAL:
        data["meta_journal_title"] = volume.get_journal_title()
        data["meta_issue"] = volume.journal_issue
        data["meta_volume"] = volume.journal_volume
    if volume.pdf is not None:
        data["pdf"] = volume.pdf.url


def export_anthology(anthology, outdir, clean=False, dryrun=False):
    """
    Dumps files in build/yaml/*.yaml. These files are used in conjunction with the hugo
    page stubs created by create_hugo_pages.py to instantiate Hugo templates.
    """
    # Create directories
    if not dryrun:
        for subdir in ("", "papers", "people"):
            target_dir = "{}/{}".format(outdir, subdir)
            if not check_directory(target_dir, clean=clean):
                return

    # Export papers
    with Progress() as progress:
        paper_count = sum(1 for _ in anthology.papers())
        task = progress.add_task("Exporting papers to YAML...", total=paper_count)
        all_volumes = {}
        for collection in anthology.collections.values():
            collection_papers = {}
            for volume in collection.volumes():
                # Compute volume-level information that gets appended to every paper
                # TODO: Could this be changed in the Hugo templates to
                # fetch the information from the volume, instead of duplicating
                # this information on every paper?
                volume_data = {
                    "address": volume.address,
                    "booktitle": volume.title.as_text(),
                    "parent_volume_id": volume.full_id,
                    "publisher": volume.publisher,
                    "month": volume.month,
                    "year": volume.year,
                }
                if events := volume.get_events():
                    # TODO: This information is currently not used on paper templates
                    volume_data["events"] = [event.id for event in events]

                # Now build the data for every paper
                for paper in volume.papers():
                    data = paper_to_dict(paper)
                    data.update(volume_data)
                    collection_papers[paper.full_id] = data

                # We build the volume data separately since it uses slightly
                # different fields than what gets attached to papers
                all_volumes[volume.full_id] = volume_to_dict(volume)

            if not dryrun:
                with open(f"{outdir}/papers/{collection.id}.yaml", "w") as f:
                    yaml.dump(collection_papers, Dumper=Dumper, stream=f)

            progress.update(task, advance=len(collection_papers))

    # Export volumes
    with open(f"{outdir}/volumes.yaml", "w") as f:
        yaml.dump(all_volumes, Dumper=Dumper, stream=f)

    exit(35)
    ##### NOT PORTED YET BEYOND THIS POINT

    # Prepare people index
    people = defaultdict(dict)
    for id_ in anthology.people.personids():
        name = anthology.people.get_canonical_name(id_)
        log.debug("export_anthology: processing person '{}'".format(repr(name)))
        data = name.as_dict()
        data["slug"] = id_
        if id_ in anthology.people.comments:
            data["comment"] = anthology.people.comments[id_]
        if id_ in anthology.people.similar:
            data["similar"] = sorted(anthology.people.similar[id_])
        papers_for_id = anthology.people.get_papers(id_, role="author") + [
            paper
            for paper in anthology.people.get_papers(id_, role="editor")
            if anthology.papers.get(paper).is_volume
        ]
        data["papers"] = sorted(
            papers_for_id,
            key=lambda p: anthology.papers.get(p).get("year"),
            reverse=True,
        )
        data["coauthors"] = sorted(
            [[co_id, count] for (co_id, count) in anthology.people.get_coauthors(id_)],
            key=lambda p: p[1],
            reverse=True,
        )
        data["venues"] = sorted(
            [
                [venue, count]
                for (venue, count) in anthology.people.get_venues(id_).items()
            ],
            key=lambda p: p[1],
            reverse=True,
        )
        variants = [
            n
            for n in anthology.people.get_used_names(id_)
            if n.first != name.first or n.last != name.last
        ]
        if len(variants) > 0:
            data["variant_entries"] = [name.as_dict() for name in sorted(variants)]
        people[id_[0]][id_] = data

    # Prepare venue index
    venues = {}
    for main_venue, data in anthology.venues.items():
        data.get("oldstyle_letter", "W")
        data = data.copy()
        data["volumes_by_year"] = {}
        for year in sorted(data["years"]):
            # Grab just the volumes that match the current year
            filtered_volumes = list(
                filter(lambda k: volumes[k]["year"] == year, data["volumes"])
            )
            data["volumes_by_year"][year] = filtered_volumes
        if not data["volumes_by_year"]:
            log.warning(f"Venue '{main_venue}' has no volumes associated with it")

        data["years"] = sorted(list(data["years"]))

        # The export uses volumes_by_year, deleting this saves space
        del data["volumes"]

        venues[main_venue] = data

    # Prepare events index
    events = {}
    for event_name, event_data in anthology.eventindex.items():
        main_venue = event_data["venue"]
        event_data = event_data.copy()

        def volume_sorter(volume):
            """
            Puts all main volumes before satellite ones.
            Main volumes are sorted in a stabile manner as
            found in the XML. Colocated ones are sorted
            alphabetically.

            :param volume: The Anthology volume
            """
            if main_venue in volumes[volume]["venues"]:
                # sort volumes in main venue first
                return "_"
            elif deconstruct_anthology_id(volume)[1] == main_venue:
                # this puts Findings at the top (e.g., 2022-findings.emnlp will match emnlp)
                return "__"
            else:
                # sort colocated volumes alphabetically, using
                # the alphabetically-earliest volume
                return min(volumes[volume]["venues"])

        event_data["volumes"] = sorted(event_data["volumes"], key=volume_sorter)

        events[event_name] = event_data

    # Prepare SIG index
    sigs = {}
    for main_venue, sig in anthology.sigs.items():
        data = {
            "name": sig.name,
            "slug": sig.slug,
            "url": sig.url,
            "volumes_by_year": sig.volumes_by_year,
            "years": sorted([str(year) for year in sig.years]),
        }
        sigs[main_venue] = data

    # Dump all
    if not dryrun:
        with open("{}/venues.yaml".format(outdir), "w") as f:
            yaml.dump(venues, Dumper=Dumper, stream=f)
        progress.update()

        with open(f"{outdir}/events.yaml", "w") as f:
            yaml.dump(events, Dumper=Dumper, stream=f)
        progress.update()

        with open("{}/sigs.yaml".format(outdir), "w") as f:
            yaml.dump(sigs, Dumper=Dumper, stream=f)
        progress.update()

        for first_letter, people_list in people.items():
            with open("{}/people/{}.yaml".format(outdir, first_letter), "w") as f:
                yaml.dump(people_list, Dumper=Dumper, stream=f)
            progress.update()
        progress.close()


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
    tracker = SeverityTracker()
    log.basicConfig(
        format="%(message)s", level=log_level, handlers=[RichHandler(), tracker]
    )

    anthology = Anthology(datadir=args["--importdir"])
    anthology.load_all()
    export_anthology(
        anthology, args["--exportdir"], clean=args["--clean"], dryrun=args["--dry-run"]
    )

    if tracker.highest >= log.ERROR:
        exit(1)
