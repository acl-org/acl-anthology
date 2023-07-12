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

from functools import cached_property

from . import data
from .papers import Paper
from .venues import VenueIndex
from .sigs import SIGIndex
from .utils import (
    build_anthology_id,
    parse_element,
    month_str2num,
    infer_url,
)


class Volume:
    def __init__(
        self,
        collection_id,
        volume_id,
        volume_type,
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
        self._type = volume_type
        self.ingest_date = ingest_date
        self.formatter = formatter
        self.venue_index = venue_index
        self._set_meta_info(meta_data)
        self.attrib["venues"] = meta_data.get("venue", [])
        self.attrib["events"] = meta_data.get("event", [])
        self.attrib["sigs"] = sig_index.get_associated_sigs(self.full_id)
        self.content = []
        self.has_abstracts = False
        self.has_frontmatter = False

    def get_venues(self):
        """
        Return the primary venues (as slugs) associated with this volume. This can be multiple venues,
        if the volumes is a joint volume. These venue associations are now listed explicitly in the
        XML, even for new-style IDs.
        """
        return self.attrib["venues"]

    @staticmethod
    def from_xml(
        volume_xml, collection_id, venue_index: VenueIndex, sig_index: SIGIndex, formatter
    ):
        volume_id = volume_xml.attrib["id"]
        volume_type = volume_xml.attrib["type"]
        # The date of publication, defaulting to earlier than anything we'll encounter
        ingest_date = volume_xml.attrib.get("ingest-date", data.UNKNOWN_INGEST_DATE)
        meta_data = parse_element(volume_xml.find("meta"))

        # Though metadata uses "booktitle", switch to "title" for compatibility with downstream scripts
        meta_data["title"] = formatter(meta_data["xml_booktitle"], "plain")

        volume = Volume(
            collection_id,
            volume_id,
            volume_type,
            ingest_date,
            meta_data,
            venue_index,
            sig_index,
            formatter,
        )

        front_matter_xml = volume_xml.find("frontmatter")
        if front_matter_xml is not None:
            front_matter = Paper.from_xml(front_matter_xml, volume, formatter)
            volume.add_frontmatter(front_matter)

        return volume

    @cached_property
    def url(self):
        # If <url> field not present, use ID.
        # But see https://github.com/acl-org/acl-anthology/issues/997.
        return infer_url(self.attrib.get("xml_url", self.full_id))

    @cached_property
    def pdf(self):
        url = self.attrib.get("xml_url", None)
        if url is not None:
            return infer_url(url, template=data.PDF_LOCATION_TEMPLATE)
        return None

    @property
    def is_journal(self):
        return self._type == "journal"

    def _set_meta_info(self, meta_data):
        """Derive journal title, volume, and issue no. used in metadata.

        This function replicates functionality that was previously hardcoded in
        'app/helpers/papers_helper.rb' of the Rails app."""
        self.attrib = meta_data

        self.attrib["meta_date"] = self.get("year")
        if "month" in self.attrib:
            month = month_str2num(self.get("month"))
            if month is not None:
                self.attrib["meta_date"] = f"{self.get('year')}/{month}"
        if self.is_journal:
            if "journal-title" in self.attrib:
                journal_title = self.attrib["journal-title"]
            else:
                venues = meta_data.get("venue", [])
                if len(venues) != 1:
                    raise ValueError(
                        f"{self.full_id}: journal volume must have exactly one venue or an explicit <journal-title>"
                    )
                journal_title = self.venue_index.get_venue(venues[0])["name"]

            self.attrib["meta_journal_title"] = journal_title

            # For compatibility reasons, we rename the attributes here; might
            # change this later
            if "journal-volume" in self.attrib:
                self.attrib["meta_volume"] = self.attrib["journal-volume"]
                del self.attrib["journal-volume"]
            if "journal-issue" in self.attrib:
                self.attrib["meta_issue"] = self.attrib["journal-issue"]
                del self.attrib["journal-issue"]

    @property
    def volume_id(self):
        return self._id

    @cached_property
    def full_id(self):
        return build_anthology_id(self.collection_id, self.volume_id)

    @property
    def year(self):
        """Return the year the volume was published."""
        return self.attrib["year"]

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

    def as_dict(self):
        value = self.attrib.copy()
        value["url"] = self.url
        if self.pdf:
            value["pdf"] = self.pdf
        return value

    def __len__(self):
        return len(self.content)

    def __iter__(self):
        return self.content.__iter__()
