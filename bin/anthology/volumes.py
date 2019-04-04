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
from . import data
from .papers import Paper
from .venues import VenueIndex
from .sigs import SIGIndex
from .utils import is_journal, month_str2num


class Volume:
    def __init__(
        self, front_matter: Paper, venue_index: VenueIndex, sig_index: SIGIndex
    ):
        """Instantiate a proceedings volume.

        `venue_index` and `sig_index` are used to find venues and SIGs
        associated with this proceedings volume.
        """
        self.formatter = front_matter.formatter
        self.front_matter_id = front_matter.paper_id
        self.top_level_id = front_matter.top_level_id
        self.attrib = front_matter.attrib.copy()
        if "author" in self.attrib:
            # Authors of the front matter are the volume's editors
            self.attrib["editor"] = self.attrib["author"]
            del self.attrib["author"]
        # Some fields should not be copied from the front matter
        for attrib in ("revision", "erratum", "pages", "xml_booktitle"):
            if attrib in self.attrib:
                del self.attrib[attrib]
        self.attrib["url"] = data.ANTHOLOGY_URL.format(self.full_id)
        self.attrib["venues"] = venue_index.register(self)
        self.attrib["sigs"] = sig_index.get_associated_sigs(front_matter.full_id)
        self._set_meta_info()
        self.content = []
        if not is_journal(self.top_level_id):
            # journals don't have front matter, but others do
            self.append(front_matter)

    def _set_meta_info(self):
        """Derive journal title, volume, and issue no. used in metadata.

        This function replicates functionality that was previously hardcoded in
        'app/helpers/papers_helper.rb' of the Rails app."""
        self.attrib["meta_date"] = self.get("year")
        if "month" in self.attrib:
            month = month_str2num(self.get("month"))
            if month is not None:
                self.attrib["meta_date"] = "{}/{}".format(self.get("year"), month)
        if is_journal(self.top_level_id):
            self.attrib["meta_journal_title"] = data.get_journal_title(
                self.top_level_id, self.attrib["title"]
            )
            volume_no = re.search(
                r"Volume\s*(\d+)", self.attrib["title"], flags=re.IGNORECASE
            )
            if volume_no is not None:
                self.attrib["meta_volume"] = volume_no.group(1)
            issue_no = re.search(
                r"(Number|Issue)\s*(\d+-?\d*)",
                self.attrib["title"],
                flags=re.IGNORECASE,
            )
            if issue_no is not None:
                self.attrib["meta_issue"] = issue_no.group(2)

    @property
    def full_id(self):
        if self.top_level_id[0] == "W":
            # If volume is a workshop, use the first two digits of ID, e.g. W15-01
            _id = "{}-{}".format(self.top_level_id, self.front_matter_id[:2])
        else:
            # If not, only use the first digit, e.g. Q15-1
            _id = "{}-{}".format(self.top_level_id, self.front_matter_id[0])
        return _id

    @property
    def paper_ids(self):
        return [paper.full_id for paper in self.content]

    def append(self, paper):
        self.content.append(paper)
        if paper.parent_volume is not None:
            log.error(
                "Trying to append paper '{}' to volume '{}', but it already belongs to '{}'".format(
                    paper.full_id, self.full_id, paper.parent_volume_id
                )
            )
        paper.parent_volume = self

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
