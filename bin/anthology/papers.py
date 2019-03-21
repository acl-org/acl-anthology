# Marcel Bollmann <marcel@bollmann.me>, 2019

import logging as log
from .people import PersonName
from .utils import (
    infer_attachment_url,
    remove_extra_whitespace,
    is_journal,
    is_volume_id,
    to_volume_id,
)
from . import data

# For BibTeX export
from .formatter import bibtex_encode, bibtex_make_entry

# Names of XML elements that may appear multiple times
_LIST_ELEMENTS = ("attachment", "author", "editor", "video", "revision", "erratum")


class Paper:
    def __init__(self, paper_id, top_level_id, formatter):
        self.formatter = formatter
        self.parent_volume = None
        self.paper_id = paper_id
        self.top_level_id = top_level_id
        self.attrib = {}

    def from_xml(xml_element, *args):
        paper = Paper(xml_element.get("id"), *args)
        paper._parse_element(xml_element)
        paper.attrib["title"] = paper.get_title("plain")
        if "booktitle" in paper.attrib:
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

    def _parse_element(self, paper_element):
        # read & store values
        if "href" in paper_element.attrib:
            self.attrib["attrib_href"] = paper_element.get("href")
            self.attrib["url"] = paper_element.get("href")
        else:
            self.attrib["url"] = data.ANTHOLOGY_URL.format(self.full_id)
        for element in paper_element:
            # parse value
            tag = element.tag.lower()
            if tag in ("abstract", "title", "booktitle"):
                tag = "xml_{}".format(tag)
                value = element
            elif tag == "attachment":
                value = {
                    "filename": element.text,
                    "type": element.get("type", "attachment"),
                    "url": infer_attachment_url(element.text),
                }
            elif tag in ("author", "editor"):
                value = PersonName.from_element(element)
            elif tag in ("erratum", "revision"):
                if tag == "revision" and "revision" not in self.attrib:
                    # Explicitly construct URL of original version of the paper
                    # -- this is a bit hacky, but it's not given in the XML
                    # explicitly
                    self.attrib["revision"] = [
                        {
                            "value": "{}v1".format(self.full_id),
                            "id": "1",
                            "url": data.ANTHOLOGY_URL.format(
                                "{}v1".format(self.full_id)
                            ),
                        }
                    ]
                value = {
                    "value": element.text,
                    "id": element.get("id"),
                    "url": data.ANTHOLOGY_URL.format(element.text),
                }
            elif tag == "mrf":
                value = {"filename": element.text, "src": element.get("src")}
            elif tag == "video":
                # Treat videos the same way as other attachments
                tag = "attachment"
                value = {
                    "filename": element.get("href"),
                    "type": element.get("tag", "video"),
                    "url": infer_attachment_url(element.get("href")),
                }
            elif tag in ("dataset", "software"):
                value = {
                    "filename": element.text,
                    "type": tag,
                    "url": infer_attachment_url(element.text),
                }
                tag = "attachment"
            else:
                value = element.text
            # store value
            if tag == "url":
                continue  # We basically have to ignore this for now
            if tag in _LIST_ELEMENTS:
                try:
                    self.attrib[tag].append(value)
                except KeyError:
                    self.attrib[tag] = [value]
            else:
                if tag in self.attrib:
                    log.warning(
                        "{}: Unexpected multiple occurrence of '{}' element".format(
                            self.full_id, tag
                        )
                    )
                self.attrib[tag] = value

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
    def is_volume(self):
        """Determines if this paper is a regular paper or a proceedings volume.

        By default, each paper ID of format 'x000' will be treated as (the front
        matter of) a proceedings volume, unless the XML is of type workshop,
        where each paper ID of format 'xx00' is treated as one volume.
        """
        return is_volume_id(self.full_id)

    @property
    def full_id(self):
        return "{}-{}".format(self.top_level_id, self.paper_id)

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

    def get_booktitle(self, form="xml"):
        """Returns the booktitle, optionally formatting it.

        See `get_title()` for details.
        """
        return self.formatter(self.get("xml_booktitle"), form)

    def as_bibtex(self):
        """Return the BibTeX entry for this paper."""
        # Build BibTeX entry
        bibkey = self.full_id  # TODO
        bibtype = self.bibtype
        entries = [("title", self.get_title(form="latex"))]
        for people in ("author", "editor"):
            if people in self.attrib:
                entries.append(
                    (people, "  and  ".join(p.as_bibtex() for p in self.get(people)))
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
        for entry in ("month", "year", "address", "publisher", "url", "doi"):
            if entry in self.attrib:
                entries.append((entry, bibtex_encode(self.get(entry))))
        if "pages" in self.attrib:
            entries.append(("pages", self.get("pages").replace("–", "--")))
        if "xml_abstract" in self.attrib:
            entries.append(("abstract", self.get_abstract(form="latex")))

        # Serialize it
        return bibtex_make_entry(bibkey, bibtype, entries)

    def items(self):
        return self.attrib.items()
