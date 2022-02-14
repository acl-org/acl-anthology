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

from datetime import datetime
import pytz

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

    def __init__(self, importdir=None, fast_load=False, require_bibkeys=True):
        """Instantiates the Anthology.

        :param importdir: Data directory to import from; if not given, you'll
        need to call `import_directory` explicitly to load the Anthology data.
        :param fast_load: If True, will disable some error checking in favor
        of faster loading.
        :param require_bibkeys: If True (default), will log errors if papers
        don't have a bibkey; can be set to False in order to create bibkeys
        for newly added papers.
        """
        self.formatter = MarkupFormatter()
        self.volumes = {}  # maps volume IDs to Volume objects
        self.papers = {}  # maps paper IDs to Paper objects
        self._fast_load = fast_load
        self._require_bibkeys = require_bibkeys
        if importdir is not None:
            self.import_directory(importdir)

    @property
    def people(self):
        # compatibility, since this was renamed internally
        return self.pindex

    def import_directory(self, importdir):
        assert os.path.isdir(importdir), f"Directory not found: {importdir}"
        self.pindex = AnthologyIndex(
            importdir,
            fast_load=self._fast_load,
            require_bibkeys=self._require_bibkeys,
            parent=self,
        )
        self.venues = VenueIndex(importdir)
        self.sigs = SIGIndex(importdir)
        for xmlfile in glob(importdir + "/xml/*.xml"):
            self.import_file(xmlfile)
        self.pindex.verify()

    def import_file(self, filename):
        # furthest east!
        # date_in_kiritimati = datetime.now(pytz.timezone("Pacific/Kiritimati")).date()

        tree = etree.parse(filename)
        collection = tree.getroot()
        collection_id = collection.get("id")
        for volume_xml in collection:
            volume = Volume.from_xml(
                volume_xml,
                collection_id,
                self.venues,
                self.sigs,
                self.formatter,
            )

            # MJP 2021-05: no longer doing this since it kills branch previews.
            # Don't merge with master prior to ingest date!
            #
            # skip volumes that have an ingestion date in the future
            # if (
            #     datetime.strptime(volume.ingest_date, "%Y-%m-%d").date()
            #     > date_in_kiritimati
            # ):
            #     log.info(
            #         f"Skipping volume {volume.full_id} with ingestion date {volume.ingest_date} in the future."
            #     )
            #     # Remove any SIG entries with this volume
            #     self.sigs.remove_volume(volume.full_id)
            #     continue

            # Register the volume since we're not skipping it
            self.venues.register(volume)

            if volume.full_id in self.volumes:
                log.critical(f"Attempted to import volume ID '{volume.full_id}' twice")
                log.critical(f"Triggered by file: {filename}")

            # front matter
            if volume.has_frontmatter:
                front_matter = volume.content[0]
                self.pindex.register(front_matter)
                self.papers[front_matter.full_id] = front_matter
            else:
                # dummy front matter to make sure that editors of
                # volume get registered as people in author database
                dummy_front_matter = Paper("0", None, volume, self.formatter)
                self.pindex.register(dummy_front_matter, dummy=True)

            self.volumes[volume.full_id] = volume
            for paper_xml in volume_xml.findall("paper"):
                parsed_paper = Paper.from_xml(
                    paper_xml, volume, self.formatter, self.venues
                )

                # MJP 2021-05: no longer doing this since it kills branch previews.
                # Don't merge with master prior to ingest date!
                #
                # skip papers that have an ingestion date in the future
                # if (
                #     datetime.strptime(parsed_paper.ingest_date, "%Y-%m-%d").date()
                #     > date_in_kiritimati
                # ):
                #     log.info(
                #         f"Skipping paper {parsed_paper.full_id} with ingestion date {parsed_paper.ingest_date} in the future."
                #     )
                #     continue

                self.pindex.register(parsed_paper)
                full_id = parsed_paper.full_id
                if full_id in self.papers:
                    log.critical(
                        f"Attempted to import paper '{full_id}' twice -- skipping"
                    )
                    continue
                volume.append(parsed_paper)
                self.papers[full_id] = parsed_paper
