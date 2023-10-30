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

from pathlib import Path
from lxml import etree
import logging as log


from .formatter import MarkupFormatter
from .index import AnthologyIndex
from .papers import Paper
from .venues import VenueIndex
from .volumes import Volume
from .sigs import SIGIndex
from .events import EventIndex


class Anthology:
    schema = None
    pindex = None
    venues = None
    eventindex = None
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
        """
        Reads all XML files in the data directory.
        """
        importdir = Path(importdir)

        assert (
            importdir.exists() and importdir.is_dir()
        ), f"Directory not found: {importdir}"
        self.pindex = AnthologyIndex(
            importdir,
            fast_load=self._fast_load,
            require_bibkeys=self._require_bibkeys,
            parent=self,
        )
        self.venues = VenueIndex(importdir)
        self.eventindex = EventIndex(self.venues)  # contains a list of all events
        self.sigs = SIGIndex(importdir)
        for xmlfile in (importdir / "xml").glob("*.xml"):
            self.import_file(xmlfile)

    def import_file(self, filename):
        tree = etree.parse(filename)
        collection_xml = tree.getroot()
        collection_id = collection_xml.get("id")

        # register complete events
        if (event_xml := collection_xml.find("./event")) is not None:
            self.eventindex.register_event(event_xml)

        for volume_xml in collection_xml.findall("./volume"):
            # If we're here we're processing volumes
            volume = Volume.from_xml(
                volume_xml,
                collection_id,
                self.venues,
                self.sigs,
                self.formatter,
            )

            # Register the volume since we're not skipping it
            self.venues.register(volume)

            # Also register volumes with events
            for venue in volume.get_venues():
                event = f"{venue}-{volume.year}"
                self.eventindex.register_volume(volume.full_id, event)

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
                parsed_paper = Paper.from_xml(paper_xml, volume, self.formatter)

                self.pindex.register(parsed_paper)
                full_id = parsed_paper.full_id
                if full_id in self.papers:
                    log.critical(
                        f"Attempted to import paper '{full_id}' twice -- skipping"
                    )
                    continue
                volume.append(parsed_paper)
                self.papers[full_id] = parsed_paper
