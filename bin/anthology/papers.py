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

import logging as log
from .people import PersonName
from .utils import (
    parse_element,
    infer_attachment_url,
    remove_extra_whitespace,
    is_journal,
    is_volume_id,
    to_volume_id,
)
from . import data

# For BibTeX export
from .formatter import bibtex_encode, bibtex_make_entry

class Paper:
    def __init__(self, paper_id, volume, formatter):
        self.parent_volume = volume
        self.formatter = formatter
        self.paper_id = paper_id
        self.top_level_id = volume.top_level_id
        self.attrib = {}
        self._bibkey = False
        self.is_volume = False

    def from_xml(xml_element, *args):
        paper = Paper(xml_element.get("id"), *args)
        paper.attrib = utils.parse_element(xml_element)

        # Expand URLs with paper ID
        for tag in ('revision', 'erratum'):
            if tag in paper.attrib:
                for item in paper.attrib[tag]:
                    if item['url'].startswith(paper.full_id):
                        log.error(
                            "{} must begin with paper ID '{}', but is '{}'".format(
                                tag, self.full_id, item['value']
                            )
                        )
                    item['url'] = data.ANTHOLOGY_URL.format(item['url'])

        if 'attachment' in paper.attrib:
            for item in paper.attrib['attachment']:
                item['url'] = utils.infer_attachment_url(item['url'], self.full_id),

        # Explicitly construct URL of original version of the paper
        # -- this is a bit hacky, but it's not given in the XML
        # explicitly
        if 'revision' in paper.attrib:
            paper.attrib['revision'].insert(0, {
                "value": "{}v1".format(self.full_id),
                "id": "1",
                "url": data.ANTHOLOGY_URL.format( "{}v1".format(self.full_id)) } )


        paper.attrib["title"] = paper.get_title("plain")
        if paper.get("booktitle"):
            paper.attrib["booktitle"] = paper.get_booktitle("plain")
        if "editor" in paper.attrib:
            if paper.is_volume:
                if "author" in paper.attrib:
                    log.warn(
                        "Paper {} has both <editor> and <author>; ignoring <author>".format(
                            paper.full_id
                        )
                    )
                # Proceedings editors are considered authors for their front matter
                paper.attrib["author"] = paper.attrib["editor"]
                del paper.attrib["editor"]
            else:
                log.warn(
                    "Paper {} has <editor> but is not a proceedings volume; ignoring <editor>".format(
                        paper.full_id
                    )
                )
        if "year" not in paper.attrib:
            paper._infer_year()
        if "pages" in paper.attrib:
            if paper.attrib["pages"] is not None:
                paper._interpret_pages()
            else:
                del paper.attrib["pages"]
        return paper

    def _infer_year(self):
        """Infer the year from the volume ID.

        Many paper entries do not explicitly contain their year.  This function assumes
        that the paper's volume identifier follows the format 'xyy', where x is
        some letter and yy are the last two digits of the year of publication.
        """
        assert (
            len(self.top_level_id) == 3
        ), "Couldn't infer year: unknown volume ID format"
        digits = self.top_level_id[1:]
        if int(digits) >= 60:
            year = "19{}".format(digits)
        else:
            year = "20{}".format(digits)
        self.attrib["year"] = year

    def _interpret_pages(self):
        """Splits up 'pages' field into first and last page, if possible.

        This is used for metadata in the generated HTML."""
        for s in ("--", "-", "–"):
            if self.attrib["pages"].count(s) == 1:
                self.attrib["page_first"], self.attrib["page_last"] = self.attrib[
                    "pages"
                ].split(s)
                self.attrib["pages"] = self.attrib["pages"].replace(s, "–")
                return

    @property
    def full_id(self):
        return "{}-{}".format(self.top_level_id, self.paper_id)

    @property
    def bibkey(self):
        if not self._bibkey:
            self._bibkey = self.full_id  # fallback
        return self._bibkey

    @bibkey.setter
    def bibkey(self, value):
        self._bibkey = value

    @property
    def bibtype(self):
        if is_journal(self.full_id):
            return "article"
        elif self.is_volume:
            return "proceedings"
        else:
            return "inproceedings"

    @property
    def parent_volume_id(self):
        if self.parent_volume is not None:
            return self.parent_volume.full_id
        return None

    def get(self, name, default=None):
        if name in self.attrib:
            return self.attrib[name]
        else:
            return self.parent_volume.get(name, default)

    def get_title(self, form="xml"):
        """Returns the paper title, optionally formatting it.

        Accepted formats:
          - xml:   Include any contained XML tags unchanged
          - plain: Strip all XML tags, returning only plain text
          - html:  Convert XML tags into valid HTML tags
          - latex: Convert XML tags into LaTeX commands
        """
        return self.formatter(self.get("xml_title"), form)

    def get_abstract(self, form="xml"):
        """Returns the abstract, optionally formatting it.

        See `get_title()` for details.
        """
        return self.formatter(self.get("xml_abstract"), form, allow_url=True)

    def get_booktitle(self, form="xml"):
        """Returns the booktitle, optionally formatting it.

        See `get_title()` for details.
        """
        return self.formatter(self.get("xml_booktitle"), form)

    def as_bibtex(self):
        """Return the BibTeX entry for this paper."""
        # Build BibTeX entry
        bibkey = self.bibkey
        bibtype = self.bibtype
        entries = [("title", self.get_title(form="latex"))]
        for people in ("author", "editor"):
            if people in self.attrib:
                entries.append(
                    (people, "  and  ".join(p.as_bibtex() for p, _ in self.get(people)))
                )
        if is_journal(self.full_id):
            entries.append(
                ("journal", bibtex_encode(self.parent_volume.get("meta_journal_title")))
            )
            journal_volume = self.parent_volume.get(
                "meta_volume", self.parent_volume.get("volume")
            )
            if journal_volume:
                entries.append(("volume", journal_volume))
            journal_issue = self.parent_volume.get(
                "meta_issue", self.parent_volume.get("issue")
            )
            if journal_issue:
                entries.append(("number", journal_issue))
        else:
            # not is_journal(self.full_id)
            if "xml_booktitle" in self.attrib:
                entries.append(("booktitle", self.get_booktitle(form="latex")))
            elif bibtype != "proceedings":
                entries.append(
                    ("booktitle", self.parent_volume.get_title(form="latex"))
                )
        for entry in ("month", "year", "address", "publisher", "note"):
            if self.get(entry) is not None:
                entries.append((entry, bibtex_encode(self.get(entry))))
        for entry in ("url", "doi"):
            if entry in self.attrib:
                # don't want latex escapes such as
                # doi = "10.1162/coli{\_}a{\_}00008",
                entries.append((entry, self.get(entry)))
        if "pages" in self.attrib:
            entries.append(("pages", self.get("pages").replace("–", "--")))
        if "xml_abstract" in self.attrib:
            entries.append(("abstract", self.get_abstract(form="latex")))

        # Serialize it
        return bibtex_make_entry(bibkey, bibtype, entries)

    def as_dict(self):
        value = self.attrib
        value["paper_id"] = self.paper_id
        value["parent_volume_id"] = self.parent_volume_id
        value["bibkey"] = self.bibkey
        value["bibtype"] = self.bibtype
        return value

    def items(self):
        return self.attrib.items()

class FrontMatter(Paper):
    def __init__(self, volume, formatter):
        super.__init__(self, 0, volume, formatter)
        self.is_volume = True

    def from_xml(xml_element, *args):
        front_matter = FrontMatter(*args)
        front_matter.attrib = utils.parse_element(xml_element)
