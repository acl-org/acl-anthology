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
from .index import AnthologyIndex
from .papers import Paper
from .venues import VenueIndex
from .volumes import Volume
from .sigs import SIGIndex


class Anthology:
    schema = None
    pindex = None
    venues = None
    sigs = None
    formatter = None

    def __init__(self, importdir=None):
        self.formatter = MarkupFormatter()
        self.volumes = {}  # maps volume IDs to Volume objects
        self.papers = {}  # maps paper IDs to Paper objects
        if importdir is not None:
            self.import_directory(importdir)

    @property
    def people(self):
        # compatibility, since this was renamed internally
        return self.pindex

    def import_directory(self, importdir):
        assert os.path.isdir(importdir), "Directory not found: {}".format(importdir)
        self.pindex = AnthologyIndex(self, importdir)
        self.venues = VenueIndex(importdir)
        self.sigs = SIGIndex(importdir)
        for xmlfile in glob(importdir + "/xml/*.xml"):
            self.import_file(xmlfile)
        self.pindex.verify()

    def import_file(self, filename):
        tree = etree.parse(filename)
        collection = tree.getroot()
        collection_id = collection.get("id")
        for volume_xml in collection:
            volume = Volume.from_xml(volume_xml, collection_id, self.venues, self.sigs, self.formatter)

            if volume.full_id in self.volumes:
                log.critical(
                    "Attempted to import volume ID '{}' twice".format(volume.full_id)
                )
                log.critical("Triggered by file: {}".format(filename))

            # front matter
            if volume.has_frontmatter:
                front_matter = volume.content[0]
                self.pindex.register(front_matter)
                self.papers[front_matter.full_id] = front_matter

            self.volumes[volume.full_id] = volume
            for paper in volume_xml.findall('paper'):
                parsed_paper = Paper.from_xml(paper, volume, self.formatter)
                self.pindex.register(parsed_paper)
                full_id = parsed_paper.full_id
                if full_id in self.papers:
                    log.critical(
                        "Attempted to import paper '{}' twice -- skipping".format(full_id)
                    )
                    continue
                volume.append(parsed_paper)
                self.papers[full_id] = parsed_paper
