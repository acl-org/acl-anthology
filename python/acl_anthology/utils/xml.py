# Copyright 2023-2025 Marcel Bollmann <marcel@bollmann.me>
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

"""Functions for XML serialization."""

import itertools as it
from lxml import etree
from typing import Callable, Iterable, Optional
from xml.sax.saxutils import escape as xml_escape


TAGS_WITH_MARKUP = {
    "b",
    "i",
    "fixed-case",
    "title",
    "abstract",
    "booktitle",
    "shortbooktitle",
}
"""XML tags which contain MarkupText."""


TAGS_WITH_UNORDERED_CHILDREN = {
    "talk",
    "paper",
    "meta",
    "frontmatter",
    "event",
    "colocated",
    "author",
    "editor",
    "speaker",
    "variant",
}
"""XML tags that may contain child elements that can logically appear in arbitrary order."""


TAGS_WITH_ORDER_SEMANTICS = {
    "author",
    "editor",
    "speaker",
    "erratum",
    "revision",
    "talk",
    "venue",
    # These maybe shouldn't matter, but currently do:
    "attachment",
    "award",
    "video",
    "pwcdataset",
}
"""XML tags that may appear multiple times per parent tag, and whose relative order matters even if their parent tag belongs to `TAGS_WITH_UNORDERED_CHILDREN`."""


def _filter_children(elems: Iterable[etree._Element]) -> list[etree._Element]:
    """Filter child elements that contribute no information.

    This includes superfluous empty XML elements, such as <first/> tags, as well as XML comments.
    """
    taglist = (
        "abstract",
        "address",
        "affiliation",
        "colocated",
        "dates",
        "first",
        "pages",
        "publisher",
    )
    return [
        x
        for x in elems
        if not (x.tag in taglist and not x.text) and not isinstance(x, etree._Comment)
    ]


def _sort_children(x: etree._Element) -> tuple[str, str]:
    """Turn an XML element into a key for sorting purposes."""
    if x.tag in TAGS_WITH_ORDER_SEMANTICS:
        # We return the same sorting key for all tags whose relative order
        # should not be changed. This guarantees that their original order will
        # not be changed due to Python's sort stability:
        # <https://docs.python.org/3/howto/sorting.html#sort-stability-and-complex-sorts>
        return (x.tag, "")
    return (x.tag, etree.tostring(x, encoding="unicode"))


def assert_equals(elem: etree._Element, other: etree._Element) -> None:
    """Assert that two Anthology XML elements are logically equivalent.

    Arguments:
        elem: The first element to compare.
        other: The second element to compare.

    Raises:
        AssertionError: If the two elements are not logically equivalent.
    """
    assert elem.tag == other.tag
    assert elem.attrib == other.attrib
    assert elem.text == other.text or (not elem.text and not other.text)
    if elem.tag in TAGS_WITH_MARKUP:
        # Should render identically, except maybe for trailing whitespace
        assert (
            etree.tostring(elem, encoding="unicode").rstrip()
            == etree.tostring(other, encoding="unicode").rstrip()
        )
    else:
        elem_children = _filter_children(elem)
        other_children = _filter_children(other)
        if elem_children and elem.tag in TAGS_WITH_UNORDERED_CHILDREN:
            elem_children = sorted(elem_children, key=_sort_children)
            other_children = sorted(other_children, key=_sort_children)
        assert [child.tag for child in elem_children] == [
            child.tag for child in other_children
        ]
        for elem_child, other_child in zip(elem_children, other_children):
            assert_equals(elem_child, other_child)


def append_text(elem: etree._Element, text: str) -> None:
    """Append text to an XML element.

    If the XML element has children, the text will be appended to the tail of the last child; otherwise, it will be appended to its text attribute.

    Arguments:
        elem: The XML element.
        text: The text string to append to the XML element.

    Returns:
        None; the XML element is modified in-place.
    """
    if len(elem):
        # already has children — append text to tail
        if elem[-1].tail is not None:
            elem[-1].tail = "".join((elem[-1].tail, text))
        else:
            elem[-1].tail = text
    elif elem.text is not None:
        elem.text = "".join((elem.text, text))
    else:
        elem.text = text


def clean_whitespace(
    text: Optional[str], func: Optional[Callable[[str], str]] = None
) -> Optional[str]:
    if text is None:
        return text
    while "  " in text:
        text = text.replace("  ", " ")
    if func is not None:
        text = func(text)
    return text


def indent(elem: etree._Element, level: int = 0, internal: bool = False) -> None:
    """Enforce canonical indentation.

    "Canonical indentation" is two spaces, with each tag on a new line,
    except that 'author', 'editor', 'title', and 'booktitle' tags are
    placed on a single line.

    Arguments:
        elem: The XML element to apply canonical indentation to.
        level: Indentation level; used for recursive calls of this function.
        internal: If True, assume we are within a single-line element.

    Note:
        Adapted from [https://stackoverflow.com/a/33956544](https://stackoverflow.com/a/33956544).
    """
    # tags that have no internal linebreaks (including children)
    oneline = elem.tag in ("author", "editor", "speaker", "title", "booktitle", "variant")

    elem.text = clean_whitespace(elem.text, lambda x: x.lstrip())

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
            child.tail = clean_whitespace(child.tail, lambda x: x.rstrip())
        elif not internal and (not child.tail or not child.tail.strip()):
            child.tail = "\n" + level * "  "
    else:
        elem.text = clean_whitespace(elem.text, lambda x: x.strip())

        if internal:
            elem.tail = clean_whitespace(elem.tail)
        elif not elem.tail or not elem.tail.strip():
            elem.tail = "\n" + level * "  "


def stringify_children(node: etree._Element) -> str:
    """
    Arguments:
        node: An XML element.

    Returns:
        The full content of the input node, including tags.

    Used for nodes that can have mixed text and HTML elements (like `<b>` and `<i>`).
    """
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
                    for child in node
                )
            ),
            (xml_escape_or_none(node.tail),),
        )
        if chunk
    ).strip()


def xml_escape_or_none(t: Optional[str]) -> Optional[str]:
    """Like [xml.sax.saxutils.escape][], but accepts [None][]."""
    return None if t is None else xml_escape(t)


def xsd_boolean(value: str) -> bool:
    """Converts an xsd:boolean value to a bool."""
    if value in ("0", "false"):
        return False
    elif value in ("1", "true"):
        return True
    raise ValueError(f"Not a valid xsd:boolean value: '{value}'")
