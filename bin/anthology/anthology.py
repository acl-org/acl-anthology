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

from glob import glob
from lxml import etree
import logging as log
import os

from .formatter import MarkupFormatter
from .papers import Paper
from .people import PersonIndex
from .venues import VenueIndex
from .volumes import Volume
from .sigs import SIGIndex


class Anthology:
    schema = None
    people = None
    venues = None
    sigs = None
    formatter = None

    def __init__(self, importdir=None):
        self.formatter = MarkupFormatter()
        self.volumes = {}  # maps volume IDs to Volume objects
        self.papers = {}  # maps paper IDs to Paper objects
        if importdir is not None:
            self.import_directory(importdir)

    def load_schema(self, schemafile):
        if os.path.exists(schemafile):
            self.schema = etree.RelaxNG(file=schemafile)
        else:
            log.error("RelaxNG schema not found: {}".format(schemafile))

    def import_directory(self, importdir):
        assert os.path.isdir(importdir), "Directory not found: {}".format(importdir)
        self.people = PersonIndex(importdir)
        self.venues = VenueIndex(importdir)
        self.sigs = SIGIndex(importdir)
        self.load_schema(importdir + "/xml/schema.rng")
        for xmlfile in glob(importdir + "/xml/*.xml"):
            self.import_file(xmlfile)

    def import_file(self, filename):
        tree = etree.parse(filename)
        if self.schema is not None:
            if not self.schema(tree):
                log.error("RelaxNG validation failed for {}".format(filename))
        volume = tree.getroot()
        top_level_id = volume.get("id")
        if top_level_id in self.volumes:
            log.critical(
                "Attempted to import top-level ID '{}' twice".format(top_level_id)
            )
            log.critical("Triggered by file: {}".format(filename))
        current_volume = None
        for paper in volume:
            parsed_paper = Paper.from_xml(paper, top_level_id, self.formatter)
            self.people.register(parsed_paper)
            full_id = parsed_paper.full_id
            if full_id in self.papers:
                log.critical(
                    "Attempted to import paper '{}' twice -- skipping".format(full_id)
                )
                continue
            if parsed_paper.is_volume:
                if current_volume is not None:
                    self.volumes[current_volume.full_id] = current_volume
                current_volume = Volume(parsed_paper, self.venues, self.sigs)
            else:
                if current_volume is None:
                    log.critical(
                        "First paper of XML should be volume entry, but '{}' is not interpreted as one".format(
                            full_id
                        )
                    )
                current_volume.append(parsed_paper)
            self.papers[full_id] = parsed_paper
        if current_volume is not None:
            self.volumes[current_volume.full_id] = current_volume
