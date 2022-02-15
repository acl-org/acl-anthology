#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Marcel Bollmann <marcel@bollmann.me>
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
from tqdm import tqdm
import logging as log
import os
import yaml, yamlfix

try:
    from yaml import CSafeDumper as Dumper
except ImportError:
    from yaml import SafeDumper as Dumper

from anthology import Anthology
from anthology.utils import SeverityTracker, deconstruct_anthology_id, is_newstyle_id
from create_hugo_pages import check_directory


def export_anthology(anthology, outdir, clean=False, dryrun=False):
    # Prepare paper index
    papers = defaultdict(dict)
    citation_styles = {
        "acl": "association-for-computational-linguistics",
        # "apa": "apa-6th-edition",
        # "mla": "modern-language-association-7th-edition",
    }
    for id_, paper in anthology.papers.items():
        log.debug("export_anthology: processing paper '{}'".format(id_))
        data = paper.as_dict()
        data["title_html"] = paper.get_title("html")
        if "xml_title" in data:
            del data["xml_title"]
        if "xml_booktitle" in data:
            data["booktitle_html"] = paper.get_booktitle("html")
            del data["xml_booktitle"]
        if "xml_abstract" in data:
            data["abstract_html"] = paper.get_abstract("html")
            del data["xml_abstract"]
        if "xml_url" in data:
            del data["xml_url"]
        if "author" in data:
            data["author"] = [
                anthology.people.resolve_name(name, id_) for name, id_ in data["author"]
            ]
        if "editor" in data:
            data["editor"] = [
                anthology.people.resolve_name(name, id_) for name, id_ in data["editor"]
            ]
        for abbrev, style in citation_styles.items():
            data[f"citation_{abbrev}"] = paper.as_citation_html(style)
        papers[paper.collection_id][paper.full_id] = data

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
        data["papers"] = sorted(
            anthology.people.get_papers(id_),
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
                for (venue, count) in anthology.people.get_venues(
                    anthology.venues, id_
                ).items()
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

    # Prepare volume index
    volumes = {}
    for id_, volume in anthology.volumes.items():
        log.debug("export_anthology: processing volume '{}'".format(id_))
        data = volume.as_dict()
        data["title_html"] = volume.get_title("html")
        del data["xml_booktitle"]
        if "xml_abstract" in data:
            del data["xml_abstract"]
        if "xml_url" in data:
            del data["xml_url"]
        data["has_abstracts"] = volume.has_abstracts
        data["papers"] = volume.paper_ids
        if "author" in data:
            data["author"] = [
                anthology.people.resolve_name(name, id_) for name, id_ in data["author"]
            ]
        if "editor" in data:
            data["editor"] = [
                anthology.people.resolve_name(name, id_) for name, id_ in data["editor"]
            ]
        volumes[volume.full_id] = data

    class SortedVolume:
        """Keys for sorting volumes so they appear in a more reasonable order.
        Takes the parent venue being sorted under, along with its letter,
        and the Anthology ID of the current volume. For example, LREC 2020
        has the following joint events, which get sorted in the following manner:

        ['2020.lrec-1', '2020.aespen-1', '2020.ai4hi-1',
        '2020.bucc-1', '2020.calcs-1', '2020.cllrd-1', '2020.clssts-1',
        '2020.cmlc-1', '2020.computerm-1', '2020.framenet-1', '2020.gamnlp-1',
        '2020.globalex-1', '2020.isa-1', '2020.iwltp-1',
        '2020.ldl-1', '2020.lincr-1', '2020.lr4sshoc-1', '2020.lt4gov-1',
        '2020.lt4hala-1 ', '2020.multilingualbio-1', '2020.onion-1',
        '2020.osact-1', '2020.parlaclarin-1', '2020.rail-1', '2020.readi-1',
        '2020.restup-1', '2020.sltu-1 ', '2020.stoc-1', '2020.trac-1',
        '2020.wac-1', '2020.wildre-1']
        """

        def __init__(self, acronym, letter, anth_id):
            self.parent_venue = acronym.lower()
            self.anth_id = anth_id

            collection_id, self.volume_id, _ = deconstruct_anthology_id(anth_id)
            if is_newstyle_id(collection_id):
                self.venue = collection_id.split(".")[1]
                self.is_parent_venue = self.venue == self.parent_venue
            else:
                self.venue = collection_id[0]
                self.is_parent_venue = self.venue == letter

        def __str__(self):
            return self.anth_id

        def __eq__(self, other):
            """We define equivalence at the venue (not volume) level in order
            to preserve the sort order found in the XML"""
            return self.venue == other.venue

        def __lt__(self, other):
            """First parent volumes, then sort by venue name"""
            if self.is_parent_venue == other.is_parent_venue:
                return self.venue < other.venue
            return self.is_parent_venue and not other.is_parent_venue

    # Prepare venue index
    venues = {}
    for acronym, data in anthology.venues.items():
        letter = data.get("oldstyle_letter", "W")
        data = data.copy()
        data["volumes_by_year"] = {
            year: sorted(
                filter(lambda k: volumes[k]["year"] == year, data["volumes"]),
                key=lambda x: SortedVolume(acronym, letter, x),
            )
            for year in sorted(data["years"])
        }
        data["years"] = sorted(list(data["years"]))
        del data["volumes"]
        venues[acronym] = data

    # Prepare SIG index
    sigs = {}
    for acronym, sig in anthology.sigs.items():
        data = {
            "name": sig.name,
            "slug": sig.slug,
            "url": sig.url,
            "volumes_by_year": sig.volumes_by_year,
            "years": sorted([str(year) for year in sig.years]),
        }
        sigs[acronym] = data

    # Dump all
    if not dryrun:
        # Create directories
        for subdir in ("", "papers", "people"):
            target_dir = "{}/{}".format(outdir, subdir)
            if not check_directory(target_dir, clean=clean):
                return

        progress = tqdm(total=len(papers) + len(people) + 7)
        for collection_id, paper_list in papers.items():
            with open("{}/papers/{}.yaml".format(outdir, collection_id), "w") as f:
                yaml.dump(paper_list, Dumper=Dumper, stream=f)
            progress.update()

        with open("{}/volumes.yaml".format(outdir), "w") as f:
            yaml.dump(volumes, Dumper=Dumper, stream=f)
        progress.update(5)

        with open("{}/venues.yaml".format(outdir), "w") as f:
            yaml.dump(venues, Dumper=Dumper, stream=f)
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
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    log.info("Reading the Anthology data...")
    anthology = Anthology(importdir=args["--importdir"])
    log.info("Exporting to YAML...")
    export_anthology(
        anthology, args["--exportdir"], clean=args["--clean"], dryrun=args["--dry-run"]
    )

    if tracker.highest >= log.ERROR:
        exit(1)
