# Marcel Bollmann <marcel@bollmann.me>, 2019

from collections import defaultdict
from glob import glob
from lxml import etree
import itertools as it
import logging as log
import os
import re


class Anthology:
    schema = None

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
                current_volume = Volume(parsed_paper)
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


def _stringify_children(node):
    """Returns the full content of a node, including tags.

    Used for nodes that can have mixed text and HTML elements (like <b> and <i>)."""
    return "".join(
        chunk
        for chunk in it.chain(
            (node.text,),
            it.chain(
                *(
                    (etree.tostring(child, with_tail=False, encoding=str), child.tail)
                    for child in node.getchildren()
                )
            ),
            (node.tail,),
        )
        if chunk
    ).strip()


def _remove_extra_whitespace(text):
    return re.sub(" +", " ", text.replace("\n", "").strip())


_LIST_ELEMENTS = ("attachment", "author", "editor", "video", "revision", "erratum")
_ANTHOLOGY_URL = "http://www.aclweb.org/anthology/{}"


class Paper:
    def __init__(self, paper_id, top_level_id):
        self.parent_volume_id = None
        self.paper_id = paper_id
        self.top_level_id = top_level_id
        self.attrib = {}

    def from_xml(xml_element, top_level_id):
        paper = Paper(xml_element.get("id"), top_level_id)
        paper._parse_element(xml_element)
        if "year" not in paper.attrib:
            paper._infer_year()
        return paper

    def _parse_element(self, paper_element):
        # read & store values
        if "href" in paper_element.attrib:
            self.attrib["attrib_href"] = paper_element.get("href")
        for element in paper_element:
            # parse value
            tag = element.tag.lower()
            if tag in ("abstract", "title"):
                value = _stringify_children(element)
            elif tag == "attachment":
                value = {"filename": element.text, "type": element.get("type", None)}
            elif tag in ("author", "editor"):
                value = PersonName.from_element(element)
            elif tag in ("erratum", "revision"):
                value = {
                    "value": element.text,
                    "id": element.get("id"),
                    "url": _ANTHOLOGY_URL.format(element.text),
                }
            elif tag == "mrf":
                value = {"filename": element.text, "src": element.get("src")}
            elif tag == "video":
                value = {"href": element.get("href"), "tag": element.get("tag")}
            else:
                value = element.text
            # store value
            if tag in ("title", "booktitle"):
                value = _remove_extra_whitespace(value)
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

    @property
    def is_volume(self):
        """Determines if this paper is a regular paper or a proceedings volume.

        By default, each paper ID of format 'x000' will be treated as (the front
        matter of) a proceedings volume, unless the XML is of type workshop,
        where each paper ID of format 'xx00' is treated as one volume.
        """
        return (
            self.paper_id[-3:] == "000"
            or (self.top_level_id[0] == "W" and self.paper_id[-2:] == "00")
            or (self.top_level_id == "C69" and self.paper_id[-2:] == "00")
        )

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


class Volume:
    def __init__(self, front_matter):
        self.front_matter_id = front_matter.paper_id
        self.top_level_id = front_matter.top_level_id
        self.attrib = front_matter.attrib.copy()
        self.attrib["url"] = _ANTHOLOGY_URL.format(self.full_id)
        self.content = []
        if self.top_level_id[0] not in ("J", "Q"):
            # J and Q don't have front matter, but others do
            self.append(front_matter)

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
        if paper.parent_volume_id is not None:
            log.error(
                "Trying to append paper '{}' to volume '{}', but it already belongs to '{}'".format(
                    paper.full_id, self.full_id, paper.parent_volume_id
                )
            )
        paper.parent_volume_id = self.full_id


class PersonName:
    first, last, jr = "", "", ""

    def __init__(self, first, last, jr):
        self.first = first.strip()
        self.last = last.strip()
        self.jr = jr.strip()

    def from_element(person_element):
        first, last, jr = "", "", ""
        for element in person_element:
            tag = element.tag
            # These are guaranteed to occur at most once by the schema
            if tag == "first":
                first = element.text or ""
            elif tag == "last":
                last = element.text or ""
            elif tag == "jr":
                jr = element.text or ""
        return PersonName(first, last, jr)

    @property
    def full(self):
        return "{} {}{}".format(self.first, self.last, self.jr).strip()

    @property
    def id_(self):
        return repr(self)

    def as_dict(self):
        return {
            "first": self.first,
            "last": self.last,
            "jr": self.jr,
            "full": self.full,
        }

    def __eq__(self, other):
        return (
            (self.first == other.first)
            and (self.last == other.last)
            and (self.jr == other.jr)
        )

    def __str__(self):
        return self.full

    def __repr__(self):
        if self.jr:
            return "{} || {} || {}".format(self.first, self.last, self.jr)
        elif self.first:
            return "{} || {}".format(self.first, self.last)
        else:
            return self.last

    def __hash__(self):
        return hash(repr(self))


class PersonIndex:
    """Keeps an index of persons and their associated papers."""

    def __init__(self):
        self.names = {}  # maps name strings to PersonName objects
        self.papers = defaultdict(lambda: defaultdict(list))

    def register(self, name: PersonName, paper_id, role):
        """Adds a name to the index, associates it with the given paper ID and role, and returns the name's unique representation."""
        assert isinstance(name, PersonName), "Expected PersonName, got {} ({})".format(
            type(name), repr(name)
        )
        if repr(name) not in self.names:
            self.names[repr(name)] = name
        self.papers[name][role].append(paper_id)
        return repr(name)

    def items(self):
        for name_repr, name in self.names.items():
            yield name_repr, name, self.papers[name]


if __name__ == "__main__":
    print("This is not a stand-alone script.")
