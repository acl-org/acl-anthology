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

import re
import logging as log

from . import data
from .papers import Paper
from .venues import VenueIndex
from .sigs import SIGIndex
from .utils import (
    build_anthology_id,
    parse_element,
    is_journal,
    month_str2num,
    infer_url,
    infer_year,
)


class Volume:
    def __init__(
        self,
        collection_id,
        volume_id,
        ingest_date,
        meta_data,
        venue_index: VenueIndex,
        sig_index: SIGIndex,
        formatter,
    ):
        """Instantiate a proceedings volume.

        `venue_index` and `sig_index` are used to find venues and SIGs
        associated with this proceedings volume.
        """
        self.collection_id = collection_id
        self._id = volume_id
        self.ingest_date = ingest_date
        self.formatter = formatter
        self._set_meta_info(meta_data)
        self.attrib["venues"] = venue_index.get_associated_venues(self.full_id)
        self.attrib["sigs"] = sig_index.get_associated_sigs(self.full_id)
        self.content = []
        self.has_abstracts = False
        self.has_frontmatter = False

    @staticmethod
    def from_xml(
        volume_xml, collection_id, venue_index: VenueIndex, sig_index: SIGIndex, formatter
    ):

        volume_id = volume_xml.attrib["id"]
        # The date of publication, defaulting to earlier than anything we'll encounter
        ingest_date = volume_xml.attrib.get("ingest-date", data.UNKNOWN_INGEST_DATE)
        meta_data = parse_element(volume_xml.find("meta"))
        # Though metadata uses "booktitle", switch to "title" for compatibility with downstream scripts
        meta_data["title"] = formatter(meta_data["xml_booktitle"], "plain")

        volume = Volume(
            collection_id,
            volume_id,
            ingest_date,
            meta_data,
            venue_index,
            sig_index,
            formatter,
        )

        front_matter_xml = volume_xml.find("frontmatter")
        if front_matter_xml is not None:
            front_matter = Paper.from_xml(front_matter_xml, volume, formatter)
        else:
            # dummy front matter to make sure that editors of
            # volume get registered as people in author database
            front_matter = Paper("0", ingest_date, volume, formatter)
        volume.add_frontmatter(front_matter)

        return volume

    def _set_meta_info(self, meta_data):
        """Derive journal title, volume, and issue no. used in metadata.

        This function replicates functionality that was previously hardcoded in
        'app/helpers/papers_helper.rb' of the Rails app."""
        self.attrib = meta_data
        if "author" in self.attrib:
            # Authors of the front matter are the volume's editors
            self.attrib["editor"] = self.attrib["author"]
            del self.attrib["author"]

        # Expand URL if present
        if "url" in self.attrib:
            self.attrib["url"] = infer_url(self.attrib["url"])

        # Some volumes don't set this---but they should!
        if "year" not in self.attrib:
            self.attrib["year"] = infer_year(self.collection_id)

        self.attrib["meta_date"] = self.get("year")
        if "month" in self.attrib:
            month = month_str2num(self.get("month"))
            if month is not None:
                self.attrib["meta_date"] = "{}/{}".format(self.get("year"), month)
        if is_journal(self.collection_id):
            self.attrib["meta_journal_title"] = data.get_journal_title(
                self.collection_id, self.attrib["title"]
            )
            volume_no = re.search(
                r"Volume\s*(\d+)", self.attrib["title"], flags=re.IGNORECASE
            )
            if volume_no is not None:
                self.attrib["meta_volume"] = volume_no.group(1)
            issue_no = re.search(
                r"(Number|Issue)\s*(\d+-?\d*)", self.attrib["title"], flags=re.IGNORECASE
            )
            if issue_no is not None:
                self.attrib["meta_issue"] = issue_no.group(2)

    @property
    def volume_id(self):
        return self._id

    @property
    def full_id(self):
        return build_anthology_id(self.collection_id, self.volume_id)

    @property
    def paper_ids(self):
        return [paper.full_id for paper in self.content]

    def add_frontmatter(self, frontmatter):
        self.has_frontmatter = True
        self.append(frontmatter)

    def append(self, paper):
        self.content.append(paper)
        if paper.has_abstract:
            self.has_abstracts = True

    def get(self, name, default=None):
        try:
            return self.attrib[name]
        except KeyError:
            return default

    def get_title(self, form="xml"):
        """Returns the paper title, optionally formatting it.

        Accepted formats:
          - xml:   Include any contained XML tags unchanged
          - plain: Strip all XML tags, returning only plain text
          - html:  Convert XML tags into valid HTML tags
        """
        return self.formatter(self.get("xml_booktitle"), form)

    def __len__(self):
        return len(self.content)

    def __iter__(self):
        return self.content.__iter__()
