# Marcel Bollmann <marcel@bollmann.me>, 2019

from glob import glob
from lxml import etree
import logging as log
import os

from .papers import Paper
from .people import PersonIndex
from .venues import VenueIndex
from .volumes import Volume
from .sigs import SIGIndex


class Anthology:
    schema = None
    venues = None
    sigs = None

    def __init__(self, importdir=None):
        self.volumes = {}  # maps volume IDs to Volume objects
        self.papers = {}  # maps paper IDs to Paper objects
        self.people = PersonIndex()
        if importdir is not None:
            self.import_directory(importdir)

    def load_schema(self, schemafile):
        if os.path.exists(schemafile):
            self.schema = etree.RelaxNG(file=schemafile)
        else:
            log.error("RelaxNG schema not found: {}".format(schemafile))

    def import_directory(self, importdir):
        assert os.path.isdir(importdir), "Directory not found: {}".format(importdir)
        self.venues = VenueIndex(importdir)
        self.sigs = SIGIndex(importdir)
        self.load_schema(importdir + "/schema.rng")
        for xmlfile in glob(importdir + "/*.xml"):
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
            parsed_paper = Paper.from_xml(paper, top_level_id)
            self._register_people(parsed_paper)
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

    def _register_people(self, paper):
        for role in ("author", "editor"):
            for name in paper.get(role, []):
                self.people.register(name, paper.full_id, role)
