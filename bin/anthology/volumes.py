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
from .utils import parse_element, is_journal, month_str2num


class Volume:
    def __init__(self,
                 collection_id,
                 volume_id,
                 meta_data,
                 venue_index: VenueIndex,
                 sig_index: SIGIndex,
                 formatter
    ):
        """Instantiate a proceedings volume.

        `venue_index` and `sig_index` are used to find venues and SIGs
        associated with this proceedings volume.
        """
        self.collection_id = collection_id
        self._id = volume_id
        self.formatter = formatter
        self.attrib = meta_data
        if "author" in self.attrib:
            # Authors of the front matter are the volume's editors
            self.attrib["editor"] = self.attrib["author"]
            del self.attrib["author"]
        if not is_journal(self.collection_id):
            self.attrib["url"] = data.ANTHOLOGY_URL.format(self.full_id)
        self.attrib["venues"] = venue_index.register(self)
        self.attrib["sigs"] = sig_index.get_associated_sigs(self.full_id)
        self._set_meta_info()
        self.content = []

    @staticmethod
    def from_xml(volume_xml,
                 collection_id,
                 venue_index: VenueIndex,
                 sig_index: SIGIndex,
                 formatter):

        volume_id = volume_xml.attrib['id']
        meta_data = parse_element(volume_xml.find('meta'))
        meta_data['booktitle'] = formatter(meta_data['xml_booktitle'], 'plain')
#        print('META', collection_id, meta_data)

        volume = Volume(collection_id, volume_id, meta_data, venue_index, sig_index, formatter)

        front_matter_xml = volume_xml.find('frontmatter')
        if front_matter_xml is not None:
            front_matter = Paper.from_xml(front_matter_xml, volume, formatter)
            front_matter._id = '0'
            front_matter.is_volume = True
            volume.append(front_matter)

        return volume

    def _set_meta_info(self):
        """Derive journal title, volume, and issue no. used in metadata.

        This function replicates functionality that was previously hardcoded in
        'app/helpers/papers_helper.rb' of the Rails app."""
        self.attrib["meta_date"] = self.get("year")
        if "month" in self.attrib:
            month = month_str2num(self.get("month"))
            if month is not None:
                self.attrib["meta_date"] = "{}/{}".format(self.get("year"), month)
        if is_journal(self.collection_id):
            print('** ATTRIB', self.attrib)
            self.attrib["meta_journal_title"] = data.get_journal_title(
                self.collection_id, self.attrib["booktitle"]
            )
            volume_no = re.search(
                r"Volume\s*(\d+)", self.attrib["booktitle"], flags=re.IGNORECASE
            )
            if volume_no is not None:
                self.attrib["meta_volume"] = volume_no.group(1)
            issue_no = re.search(
                r"(Number|Issue)\s*(\d+-?\d*)",
                self.attrib["booktitle"],
                flags=re.IGNORECASE,
            )
            if issue_no is not None:
                self.attrib["meta_issue"] = issue_no.group(2)

    @property
    def volume_id(self):
        if self.collection_id[0] == "W" or self.collection_id == "C69":
            # If volume is a workshop, use the first two digits of ID, e.g. W15-01
            _id = "{:02d}".format(int(self._id))
        else:
            # If not, only use the first digit, e.g. Q15-1
            _id = "{:01d}".format(int(self._id))
        return _id

    @property
    def full_id(self):
        return "{}-{}".format(self.collection_id, self.volume_id)

    @property
    def paper_ids(self):
        return [paper.full_id for paper in self.content]

    def append(self, paper):
        self.content.append(paper)

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
        return self.formatter(self.get("xml_title"), form)

    def __len__(self):
        return len(self.content)

    def __iter__(self):
        return self.content.__iter__()
