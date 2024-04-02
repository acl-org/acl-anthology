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

import itertools as it
import logging
import os
import re
import requests
import shutil

from lxml import etree
from xml.sax.saxutils import escape as xml_escape
from typing import Tuple, Optional
from zlib import crc32

from .people import PersonName
from . import data

from typing import List


def xml_escape_or_none(t):
    return None if t is None else xml_escape(t)


def is_newstyle_id(anthology_id):
    return anthology_id[0].isdigit()  # New-style IDs are year-first


def is_volume_id(anthology_id):
    collection_id, volume_id, paper_id = deconstruct_anthology_id(anthology_id)
    return paper_id == "0"


def is_valid_id(id_):
    """
    Determines whether the identifier has a valid Anthology identifier format (paper or volume).
    """
    match = re.match(r"([A-Z]\d{2})-(\d{1,4})", id_)
    if not re.match(r"[A-Z]\d{2}-\d{1,3}", id_):
        return False

    first, rest = match.groups()

    if len(rest) != 4:
        if (
            first.startswith("W")
            or first == "C69"
            or (first == "D19" and int(rest[0]) >= 5)
        ):
            return len(rest) == 2
        else:
            return len(rest) == 1

    return True


def build_anthology_id(
    collection_id: str, volume_id: Optional[str], paper_id: Optional[str] = None
) -> str:
    """
    Transforms collection id, volume id, and paper id to a width-padded
    Anthology ID. e.g., ('P18', '1', '1') -> P18-1001.
    """
    if is_newstyle_id(collection_id):
        if paper_id is not None:
            return f"{collection_id}-{volume_id}.{paper_id}"
        elif volume_id is not None:
            return f"{collection_id}-{volume_id}"
        else:
            return collection_id

    else:  # pre-2020 IDs
        if (
            collection_id[0] == "W"
            or collection_id == "C69"
            or (collection_id == "D19" and int(volume_id) >= 5)
        ):
            anthology_id = f"{collection_id}-{int(volume_id):02d}"
            if paper_id is not None:
                anthology_id += f"{int(paper_id):02d}"
        else:
            anthology_id = f"{collection_id}-{int(volume_id):01d}"
            if paper_id is not None:
                anthology_id += f"{int(paper_id):03d}"

        return anthology_id


def test_url_code(url):
    """
    Test a URL, returning the result.
    """
    headers = {'user-agent': 'acl-anthology/0.0.1'}
    r = requests.head(url, headers=headers, allow_redirects=True)  # , verify=False)
    return r


def test_url(url):
    """
    Tests a URL, returning True if the URL exists, and False otherwise.
    """
    return test_url_code(url).status_code == requests.codes.ok


def retrieve_url(remote_url: str, local_path: str):
    """
    Saves a URL to a local path. Can handle cookies, e.g., those
    used downloading PDFs from MIT Press (TACL, CL).

    :param remote_url: The URL to download from. Currently supports http only.
    :param local_path: Where to save the file to.
    """
    outdir = os.path.dirname(local_path)
    if outdir != "" and not os.path.exists(outdir):
        os.makedirs(outdir)

    if remote_url.startswith("http"):
        import urllib.request

        cookieProcessor = urllib.request.HTTPCookieProcessor()
        opener = urllib.request.build_opener(cookieProcessor)
        request = urllib.request.Request(
            remote_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'
            },
        )

        with opener.open(request, timeout=1000) as url, open(
            local_path, mode="wb"
        ) as input_file_fh:
            input_file_fh.write(url.read())
    else:
        shutil.copyfile(remote_url, local_path)

    return True


def deconstruct_anthology_id(anthology_id: str) -> Tuple[str, str, str]:
    """
    Parses an Anthology ID into its constituent collection id, volume id, and paper id
    parts. e.g,

        P18-1007 -> ('P18', '1',  '7')
        W18-6310 -> ('W18', '63', '10')
        D19-1001 -> ('D19', '1',  '1')
        D19-5702 -> ('D19', '57', '2')
        2022.acl-main.1 -> ('2022.acl', 'main', '1')

    Also works with volumes:

        P18-1 -> ('P18', '1', None)
        W18-63 -> ('W18', '63', None)

    And even with just collections:

        P18 -> ('P18', None, None)

    For Anthology IDs prior to 2020, the volume ID is the first digit after the hyphen, except
    for the following situations, where it is the first two digits:

    - All collections starting with 'W'
    - The collection "C69"
    - All collections in "D19" where the first digit is >= 5
    """

    if is_newstyle_id(anthology_id):
        if "-" in anthology_id:
            collection_id, rest = anthology_id.split("-")
        else:
            collection_id = anthology_id
        rest = None
        if "-" in anthology_id:
            collection_id, rest = anthology_id.split("-")
            if "." in rest:
                volume_id, paper_id = rest.split(".")
            else:
                volume_id, paper_id = rest, None
        else:
            collection_id, volume_id, paper_id = anthology_id, None, None

        return (collection_id, volume_id, paper_id)
    else:
        if "-" in anthology_id:
            collection_id, rest = anthology_id.split("-")
            # pre-2020 IDs
            if (
                collection_id.startswith("W")
                or collection_id == "C69"
                or (collection_id == "D19" and int(rest[0]) >= 5)
            ):
                if len(rest) == 4:
                    return (collection_id, str(int(rest[0:2])), str(int(rest[2:])))
                else:  # Possible Volume only identifier
                    return (collection_id, str(int(rest)), None)
            else:
                if len(rest) == 4:
                    return (collection_id, str(int(rest[0:1])), str(int(rest[1:])))
                else:  # Possible Volume only identifier
                    return (collection_id, str(int(rest)), None)
        else:
            return anthology_id, None, None


def get_xml_file(anth_id):
    """
    Returns the XML file containing an Anthology ID.
    """
    collection_id, _, _ = deconstruct_anthology_id(anth_id)
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "data",
        "xml",
        f"{collection_id}.xml",
    )


def get_pdf_dir(anth_id):
    """
    Returns a local path to the directory containing the PDF of the specified Anthology ID.
    """
    collection_id, volume_id, paper_id = deconstruct_anthology_id(anth_id)

    if is_newstyle_id(anth_id):
        venue_name = collection_id.split(".")[1]
        return os.path.join(data.ANTHOLOGY_FILE_DIR, "pdf", venue_name)
    else:
        return os.path.join(
            data.ANTHOLOGY_FILE_DIR, "pdf", collection_id[0], collection_id
        )


def stringify_children(node):
    """Returns the full content of a node, including tags.

    Used for nodes that can have mixed text and HTML elements (like <b> and <i>)."""
    return "".join(
        chunk
        for chunk in it.chain(
            (xml_escape_or_none(node.text),),
            it.chain(
                *(
                    (
                        etree.tostring(child, with_tail=False, encoding=str),
                        xml_escape_or_none(child.tail),
                    )
                    for child in node.getchildren()
                )
            ),
            (xml_escape_or_none(node.tail),),
        )
        if chunk
    ).strip()


def remove_extra_whitespace(text):
    text = text.replace("\n", "").strip()
    # This was profiled to be 2x-4x faster than using re.sub();
    # also cf. https://stackoverflow.com/a/15913564
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def infer_url(filename, template=data.CANONICAL_URL_TEMPLATE):
    """If URL is relative, return the full Anthology URL.
    Returns the canonical URL by default, unless a different
    template is provided."""

    assert (
        "{}" in template or "%s" in template
    ), "template has no substitution text; did you pass a prefix by mistake?"

    if "://" in filename:
        return filename
    return template.format(filename)


def infer_attachment_url(filename, parent_id=None):
    if "://" in filename:
        return filename
    # Otherwise, treat it as an internal filename
    if parent_id is not None and not filename.startswith(parent_id):
        logging.error(
            f"attachment must begin with paper ID '{parent_id}', but is '{filename}'"
        )
    return data.ATTACHMENT_TEMPLATE.format(filename)


def infer_year(collection_id):
    """Infer the year from the collection ID.

    Many paper entries do not explicitly contain their year.  This function assumes
    that the paper's collection identifier follows the format 'xyy', where x is
    some letter and yy are the last two digits of the year of publication.
    """
    if is_newstyle_id(collection_id):
        return collection_id.split(".")[0]

    assert (
        len(collection_id) == 3
    ), f"Couldn't infer year: unknown volume ID format '{collection_id}' ({type(collection_id)})"
    digits = collection_id[1:]
    if int(digits) >= 60:
        year = f"19{digits}"
    else:
        year = f"20{digits}"

    return year


_MONTH_TO_NUM = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def month_str2num(text):
    """Convert a month string to a number, e.g. February -> 2

    Returns None if the string doesn't correspond to a month.

    Not using Python's datetime here since its behaviour depends on the system
    locale."""
    return _MONTH_TO_NUM.get(text.lower(), None)


class SeverityTracker(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level=level)
        self.highest = logging.NOTSET

    def emit(self, record):
        if record.levelno > self.highest:
            self.highest = record.levelno


def clean_whitespace(text, strip="left"):
    if text is not None:
        text = re.sub(r" +", " ", text)
        if strip == "left" or strip == "both":
            text = text.lstrip()
        if strip == "right" or strip == "both":
            text = text.rstrip()
    return text


def indent(elem, level=0, internal=False):
    """
    Enforces canonical indentation: two spaces,
    with each tag on a new line, except that 'author', 'editor',
    'title', and 'booktitle' tags are placed on a single line.

    Adapted from https://stackoverflow.com/a/33956544 .
    """
    # tags that have no internal linebreaks (including children)
    oneline = elem.tag in (
        "author",
        "editor",
        "speaker",
        "title",
        "booktitle",
        "variant",
        "abstract",
    )

    elem.text = clean_whitespace(elem.text)

    if len(elem):  # children
        # Set indent of first child for tags with no text
        if not oneline and (not elem.text or not elem.text.strip()):
            elem.text = "\n" + (level + 1) * "  "

        if not elem.tail or not elem.tail.strip():
            if level:
                elem.tail = "\n" + level * "  "
            else:
                elem.tail = "\n"

        # recurse
        for child in elem:
            indent(child, level + 1, internal=(internal or oneline))

        # Clean up the last child
        if oneline:
            child.tail = clean_whitespace(child.tail, strip="right")
        elif not internal and (not child.tail or not child.tail.strip()):
            child.tail = "\n" + level * "  "
    else:
        elem.text = clean_whitespace(elem.text, strip="both")

        if internal:
            elem.tail = clean_whitespace(elem.tail, strip="none")
        elif not elem.tail or not elem.tail.strip():
            elem.tail = "\n" + level * "  "


def parse_element(
    xml_element,
    list_elements=data.LIST_ELEMENTS,
    dont_parse_elements=data.DONT_PARSE_ELEMENTS,
):
    """
    Parses an XML node into a key-value hash.
    Certain types receive special treatment.
    Works for defined elements (mainly paper nodes and the <meta> block)

    :param xml_element: the XML node to parse
    :param list_elements: a list of elements that should be accumulated as lists
    :param dont_parse_elements: a list of elements whose value should be the unparsed
           XML node, rather than the parsed value
    """
    attrib = {}
    if xml_element is None:
        return attrib

    for element in xml_element:
        if element.tag is etree.Comment:
            continue

        # parse value
        tag = element.tag.lower()
        if tag in dont_parse_elements:
            # These elements have sub-formatting that gets interpreted in different
            # ways (text, BibTeX, HTML, etc.), so we preserve the XML, marking it
            # with a prefix.
            tag = f"xml_{tag}"
            value = element
        elif tag == "url":
            tag = element.attrib.get("type", "xml_url")
            value = element.text
        elif tag == "attachment":
            value = {
                "filename": element.text,
                "type": element.get("type", "attachment"),
                "url": element.text,
            }
        elif tag in ("author", "editor"):
            id_ = element.attrib.get("id", None)
            value = (PersonName.from_element(element), id_)
        elif tag == "erratum":
            value = {"value": element.text, "id": element.get("id"), "url": element.text}
        elif tag == "revision":
            value = {
                "value": element.get("href"),
                "id": element.get("id"),
                "url": element.get("href"),
                "explanation": element.text,
            }
        elif tag == "mrf":
            value = {"filename": element.text, "src": element.get("src")}
        elif tag == "video":
            tag = "video"
            # Skip videos where permission was not granted (these should be marked as private anyway in Vimeo)
            if element.get("permission", "true") == "false":
                continue
            value = element.get("href")
        elif tag in ("dataset", "software"):
            value = {"filename": element.text, "type": tag, "url": element.text}
            tag = "attachment"
        elif tag == "pwccode":
            value = {
                "url": element.get("url"),
                "additional": element.get("additional"),
                "name": element.text,
            }
        elif tag == "pwcdataset":
            value = {"url": element.get("url"), "name": element.text}
        else:
            value = element.text

        # these items get built as lists (default is to overwrite)
        if tag in list_elements:
            try:
                attrib[tag].append(value)
            except KeyError:
                attrib[tag] = [value]
        else:
            attrib[tag] = value

    return attrib


def make_simple_element(tag, text=None, attrib=None, parent=None, namespaces=None):
    """Convenience function to create an LXML node"""
    el = (
        etree.Element(tag, nsmap=namespaces)
        if parent is None
        else etree.SubElement(parent, tag)
    )
    if text:
        el.text = str(text)
    if attrib:
        for key, value in attrib.items():
            el.attrib[key] = value
    return el


def compute_hash(value: bytes) -> str:
    checksum = crc32(value) & 0xFFFFFFFF
    return f"{checksum:08x}"


def compute_hash_from_file(path: str) -> str:
    with open(path, "rb") as f:
        return compute_hash(f.read())


def read_leaves(data) -> List[str]:
    """Reads the leaves of a possibly superfluously-hierarchical data structure.
    For example:

    { "2019": ["this", "that"] } -> ["this", "that"]
    ["this", "that"] => ["this", "that"]
    """
    leaves = []
    if isinstance(data, dict):
        for subdata in data.values():
            leaves += read_leaves(subdata)
    elif isinstance(data, list):
        for subdata in data:
            leaves += read_leaves(subdata)
    elif data:
        leaves = [data]

    return leaves
