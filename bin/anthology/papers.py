# -*- coding: utf-8 -*-
#
# Copyright 2019-2022 Marcel Bollmann <marcel@bollmann.me>
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
import langcodes
import logging as log

from .utils import (
    build_anthology_id,
    parse_element,
    infer_url,
    infer_attachment_url,
)
from . import data

# For bibliography export
from .formatter import (
    bibtex_encode,
    bibtex_make_entry,
    CiteprocFormatter,
    MarkupFormatter,
)


class Paper:
    def __init__(self, paper_id, ingest_date, volume, formatter=None):
        self.parent_volume = volume
        if formatter is None:
            formatter = MarkupFormatter()
        self.formatter = formatter
        self._id = paper_id
        self._ingest_date = ingest_date
        self._bibkey = None
        self._citeproc_json = None
        self.is_volume = paper_id == "0"

        # initialize metadata with keys inherited from volume
        self.attrib = {}
        for key, value in volume.attrib.items():
            if key in (
                "collection_id",
                "booktitle",
                "id",
                "meta_data",
                "meta_journal_title",
                "meta_volume",
                "meta_issue",
                "sigs",
                "venues",
                "meta_date",
                "url",
                "pdf",
                "xml_url",
            ):
                continue

            self.attrib[key] = value

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

    @cached_property
    def videos(self):
        videos = self.attrib.get("video", None)
        if videos:
            return [
                infer_url(video, template=data.VIDEO_LOCATION_TEMPLATE)
                for video in videos
            ]
        return []

    def _parse_revision_or_errata(self, tag):
        for item in self.attrib.get(tag, []):
            # Expand URLs with paper ID
            if not item["url"].startswith(self.full_id):
                log.error(
                    "{} must begin with paper ID '{}', but is '{}'".format(
                        tag, self.full_id, item["url"]
                    )
                )
            item["url"] = data.PDF_LOCATION_TEMPLATE.format(item["url"])
        return self.attrib.get(tag, [])

    @cached_property
    def revisions(self):
        return self._parse_revision_or_errata("revision")

    @cached_property
    def errata(self):
        return self._parse_revision_or_errata("erratum")

    @cached_property
    def attachments(self):
        for item in self.attrib.get("attachment", []):
            item["url"] = infer_attachment_url(item["url"], self.full_id)
        return self.attrib.get("attachment", [])

    @cached_property
    def thumbnail(self):
        return data.PDF_THUMBNAIL_LOCATION_TEMPLATE.format(self.full_id)

    @cached_property
    def title(self):
        return self.get_title("plain")

    @cached_property
    def booktitle(self):
        return self.get_booktitle("plain")

    def from_xml(xml_element, *args):
        ingest_date = xml_element.get("ingest-date", data.UNKNOWN_INGEST_DATE)

        # Default to paper ID "0" (for front matter)
        paper = Paper(xml_element.get("id", "0"), ingest_date, *args)

        # Set values from parsing the XML element (overwriting
        # and changing some initialized from the volume metadata)
        for key, value in parse_element(xml_element).items():
            if key == "bibkey":
                paper.bibkey = value
            else:
                paper.attrib[key] = value

        # Frontmatter title is the volume 'booktitle'
        if paper.is_volume:
            paper.attrib["xml_title"] = paper.attrib["xml_booktitle"]
            paper.attrib["xml_title"].tag = "title"

        # Remove booktitle for frontmatter and journals
        if paper.is_volume or paper.parent_volume.is_journal:
            del paper.attrib["xml_booktitle"]

        if "editor" in paper.attrib:
            if paper.is_volume and "author" not in paper.attrib:
                # Proceedings editors are considered authors for their front matter
                paper.attrib["author"] = paper.attrib["editor"]
                del paper.attrib["editor"]

        if "pages" in paper.attrib:
            if paper.attrib["pages"] is not None:
                paper._interpret_pages()
            else:
                del paper.attrib["pages"]

        if "author" in paper.attrib:
            paper.attrib["author_string"] = ", ".join(
                [x[0].full for x in paper.attrib["author"]]
            )

        # TODO: compute this lazily!
        paper.attrib["citation"] = paper.as_markdown()

        # An empty value gets set to None, which causes hugo to skip it over
        # entirely. Set it here to a single space, instead. There's probably
        # a better way to do this.
        if "retracted" in paper.attrib and paper.attrib["retracted"] is None:
            paper.attrib["retracted"] = " "

        # Adjust the title for retracted papers
        if (
            "retracted" in paper.attrib
            and "xml_title" in paper.attrib
            and paper.attrib["xml_title"].text is not None
        ):
            paper.attrib["xml_title"].text = (
                "[RETRACTED] " + paper.attrib["xml_title"].text
            )

        if "removed" in paper.attrib and paper.attrib["removed"] is None:
            paper.attrib["removed"] = " "

        return paper

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
    def ingest_date(self):
        """Inherit publication date from parent, but self overrides. May be undefined."""
        if self._ingest_date:
            return self._ingest_date
        if self.parent_volume:
            return self.parent_volume.ingest_date
        return data.UNKNOWN_INGEST_DATE

    @property
    def collection_id(self):
        return self.parent_volume.collection_id

    @property
    def volume_id(self):
        return self.parent_volume.volume_id

    @property
    def paper_id(self):
        return self._id

    @property
    def full_id(self):
        return self.anthology_id

    @cached_property
    def anthology_id(self):
        return build_anthology_id(self.collection_id, self.volume_id, self.paper_id)

    @property
    def bibkey(self):
        return self._bibkey

    @bibkey.setter
    def bibkey(self, value):
        self._bibkey = value

    @property
    def bibtype(self):
        """Return the BibTeX entry type for this paper."""
        if self.is_volume:
            return "proceedings"
        elif self.parent_volume.is_journal:
            return "article"
        else:
            return "inproceedings"

    @property
    def csltype(self):
        """Return the CSL type for this paper.

        cf. https://docs.citationstyles.org/en/stable/specification.html#appendix-iii-types
        """
        if self.parent_volume.is_journal:
            return "article-journal"
        elif self.is_volume:
            return "book"
        else:
            return "paper-conference"

    @property
    def parent_volume_id(self):
        if self.parent_volume is not None:
            return self.parent_volume.full_id
        return None

    @property
    def has_abstract(self):
        return "xml_abstract" in self.attrib

    @property
    def is_retracted(self) -> bool:
        return "retracted" in self.attrib

    @property
    def is_removed(self) -> bool:
        return "removed" in self.attrib

    @property
    def isbn(self):
        return self.attrib.get("isbn", None)

    @property
    def langcode(self):
        """Returns the BCP47 language code, if present"""
        return self.attrib.get("language", None)

    @property
    def language(self):
        """Returns the language name, if present"""
        lang = None
        if self.langcode:
            lang = langcodes.Language.get(self.langcode).display_name()
        return lang

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
          - latex: Convert XML tags into LaTeX commands
        """
        return self.formatter(self.get("xml_title"), form)

    def get_abstract(self, form="xml"):
        """Returns the abstract, optionally formatting it.

        See `get_title()` for details.
        """
        return self.formatter(self.get("xml_abstract"), form, allow_url=True)

    def get_booktitle(self, form="xml", default=""):
        """Returns the booktitle, optionally formatting it.

        See `get_title()` for details.
        """
        if "xml_booktitle" in self.attrib:
            return self.formatter(self.get("xml_booktitle"), form)
        elif self.parent_volume is not None:
            return self.parent_volume.get("title")
        else:
            return default

    def as_bibtex(self, concise=False):
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
        if self.parent_volume.is_journal:
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
                entries.append(("booktitle", self.parent_volume.get_title(form="latex")))
        for entry in ("month", "year", "address", "publisher", "note"):
            if self.get(entry) is not None:
                entries.append((entry, bibtex_encode(self.get(entry))))
        if self.url is not None:
            entries.append(("url", self.url))
        if "doi" in self.attrib:
            # don't want latex escapes such as
            # doi = "10.1162/coli{\_}a{\_}00008",
            entries.append(("doi", self.get("doi")))
        if "pages" in self.attrib:
            entries.append(("pages", self.get("pages").replace("–", "--")))
        if "xml_abstract" in self.attrib and not concise:
            entries.append(("abstract", self.get_abstract(form="latex")))
        if self.language:
            entries.append(("language", self.language))
        if self.isbn:
            entries.append(("ISBN", self.isbn))

        # Serialize it
        return bibtex_make_entry(bibkey, bibtype, entries)

    def as_citeproc_json(self):
        """Return a citation object suitable for CiteProcJSON."""
        if self._citeproc_json is None:
            data = {
                "id": self.bibkey,
                "title": self.get_title(form="text"),
                "type": self.csltype,
            }
            if "author" in self.attrib:
                data["author"] = [p.as_citeproc_json() for p, _ in self.get("author")]
            if "editor" in self.attrib:
                # or should this be "container-author"/"collection-editor" here?
                data["editor"] = [p.as_citeproc_json() for p, _ in self.get("editor")]
            if self.parent_volume.is_journal:
                data["container-title"] = self.parent_volume.get("meta_journal_title")
                journal_volume = self.parent_volume.get(
                    "meta_volume", self.parent_volume.get("volume")
                )
                if journal_volume:
                    data["volume"] = journal_volume
                journal_issue = self.parent_volume.get(
                    "meta_issue", self.parent_volume.get("issue")
                )
                if journal_issue:
                    data["issue"] = journal_issue
            else:
                if "xml_booktitle" in self.attrib:
                    data["container-title"] = self.get_booktitle(form="text")
                elif self.bibtype != "proceedings":
                    data["container-title"] = self.parent_volume.get_title(form="text")
            data["publisher"] = self.get("publisher", "")
            data["publisher-place"] = self.get("address", "")
            data["issued"] = {
                "date-parts": [
                    [self.get("year")]
                ]  # TODO: month needs to be a numeral to be included
            }
            data["URL"] = self.url
            if "doi" in self.attrib:
                data["DOI"] = self.get("doi")
            if "pages" in self.attrib:
                data["page"] = self.get("pages")
            if self.isbn:
                data["ISBN"] = self.isbn
            self._citeproc_json = [data]
        return self._citeproc_json

    def as_citation_html(
        self, style="association-for-computational-linguistics", link_title=True
    ):
        html = CiteprocFormatter.render_html_citation(self, style)
        if link_title:
            # It would be nicer to do this within Citeproc, which would probably
            # entail writing/updating our own CSL style.
            title = self.get_title("plain")
            link = f'<a href="{self.url}">{title}</a>'
            html = html.replace(title, link)
        return html

    def as_markdown(self, concise=False):
        """Return a Markdown-formatted entry."""
        title = self.get_title(form="text")

        authors = "N.N."
        field = "author" if "author" in self.attrib else "editor"
        if field in self.attrib:
            people = [person[0] for person in self.get(field)]
            num_people = len(people)
            if num_people == 1:
                authors = people[0].last
            elif num_people == 2:
                authors = f"{people[0].last} & {people[1].last}"
            elif num_people >= 3:
                authors = f"{people[0].last} et al."

        year = self.get("year")
        venue = self.get_venue_acronym()
        url = self.url

        # hard-coded exception for old-style W-* volumes without an annotated
        # main venue
        if venue != "WS":
            return f"[{title}]({url}) ({authors}, {venue} {year})"
        return f"[{title}]({url}) ({authors}, {year})"

    def get_venue_acronym(self):
        """
        Returns the venue acronym for the paper (e.g., NLP4TM).
        Joint events will have more than one venue and will be hyphenated (e.g., ACL-IJCNLP).
        """
        venue_slugs = self.parent_volume.get_venues()
        venues = [
            self.parent_volume.venue_index.get_acronym_by_slug(slug)
            for slug in venue_slugs
        ]
        return "-".join(venues)

    def as_dict(self):
        value = self.attrib.copy()
        value["paper_id"] = self.paper_id
        value["parent_volume_id"] = self.parent_volume_id
        value["bibkey"] = self.bibkey
        value["bibtype"] = self.bibtype
        value["language"] = self.language
        value["url"] = self.url
        value["title"] = self.title
        value["booktitle"] = self.booktitle
        if self.pdf:
            value["pdf"] = self.pdf
        if self.revisions:
            value["revision"] = self.revisions
        if self.errata:
            value["erratum"] = self.errata
        if self.videos:
            value["video"] = self.videos
        if self.attachments:
            value["attachment"] = self.attachments
        value["thumbnail"] = self.thumbnail
        return value

    def items(self):
        return self.attrib.items()

    def iter_people(self):
        for name, id_ in self.get("author", []):
            yield (name, id_, "author")
        if self.is_volume:
            for name, id_ in self.get("editor", []):
                yield (name, id_, "editor")
