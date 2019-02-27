# Marcel Bollmann <marcel@bollmann.me>, 2019

import logging as log
from .people import PersonName
from .utils import stringify_children, infer_attachment_url, remove_extra_whitespace
from . import data

# Names of XML elements that may appear multiple times
_LIST_ELEMENTS = ("attachment", "author", "editor", "video", "revision", "erratum")


def is_volume_id(anthology_id):
    return (
        anthology_id[-3:] == "000"
        or (anthology_id[0] == "W" and anthology_id[-2:] == "00")
        or (anthology_id[:3] == "C69" and anthology_id[-2:] == "00")
    )


def to_volume_id(anthology_id):
    if anthology_id[0] == "W":
        return anthology_id[:6]
    return anthology_id[:5]


class Paper:
    def __init__(self, paper_id, top_level_id):
        self.parent_volume_id = None
        self.paper_id = paper_id
        self.top_level_id = top_level_id
        self.attrib = {}

    def from_xml(xml_element, top_level_id):
        paper = Paper(xml_element.get("id"), top_level_id)
        paper._parse_element(xml_element)
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
        if "pages" in paper.attrib and paper.attrib["pages"] is not None:
            paper._interpret_pages()
        return paper

    def _parse_element(self, paper_element):
        # read & store values
        if "href" in paper_element.attrib:
            self.attrib["attrib_href"] = paper_element.get("href")
        for element in paper_element:
            # parse value
            tag = element.tag.lower()
            if tag in ("abstract", "title"):
                value = stringify_children(element)
            elif tag == "attachment":
                value = {
                    "filename": element.text,
                    "type": element.get("type", "attachment"),
                    "url": infer_attachment_url(element.text),
                }
            elif tag in ("author", "editor"):
                value = PersonName.from_element(element)
            elif tag in ("erratum", "revision"):
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
            else:
                value = element.text
            # store value
            if tag in ("title", "booktitle"):
                value = remove_extra_whitespace(value)
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

    def get(self, name, default=None):
        try:
            return self.attrib[name]
        except KeyError:
            return default

    def items(self):
        return self.attrib.items()
