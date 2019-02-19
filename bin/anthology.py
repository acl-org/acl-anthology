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
        self.volumes = defaultdict(list)  # maps volume IDs to lists of paper IDs
        self.papers = {}  # maps paper IDs to Paper objects
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
        volume_id = volume.get("id")
        if volume_id in self.volumes:
            log.critical("Attempted to import volume '{}' twice".format(volume_id))
            log.critical("Triggered by file: {}".format(filename))
        for paper in volume:
            paper_id = paper.get("id")
            full_id = "{}-{}".format(volume_id, paper_id)
            if full_id in self.papers:
                log.critical(
                    "Attempted to import paper '{}' twice -- skipping".format(full_id)
                )
                continue
            self.papers[full_id] = Paper(paper, volume_id)
            self.volumes[volume_id].append(full_id)


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
_REVISION_URL = "http://www.aclweb.org/anthology/{}"


class Paper:
    def __init__(self, paper_element, volume_id):
        # initialize
        self.paper_id = paper_element.get("id")
        self.parent_volume = volume_id
        self.attrib = {}
        self._parse_element(paper_element)
        if "year" not in self.attrib:
            self._infer_year()

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
                    "url": _REVISION_URL.format(element.text),
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
            len(self.parent_volume) == 3
        ), "Couldn't infer year: unknown volume ID format"
        digits = int(self.parent_volume[1:])
        if digits >= 60:
            year = "19{}".format(digits)
        else:
            year = "20{}".format(digits)
        self.attrib["year"] = year

    @property
    def full_id(self):
        return "{}-{}".format(self.parent_volume, self.paper_id)

    def get(self, name, default=None):
        try:
            return self.attrib[name]
        except KeyError:
            return default

    def items(self):
        return self.attrib.items()


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

    def as_dict(self):
        return {"first": self.first, "last": self.last, "jr": self.jr}

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
