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
from difflib import SequenceMatcher
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


TAGS_WITHOUT_LINEBREAKS = {
    "author",
    "editor",
    "speaker",
    "title",
    "booktitle",
    "variant",
}
"""XML tags that should always be serialized without line breaks."""


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
    if isinstance(elem, etree._Comment):
        return

    # tags that have no internal linebreaks (including children)
    oneline = elem.tag in TAGS_WITHOUT_LINEBREAKS

    elem.text = clean_whitespace(elem.text, lambda x: x.lstrip())
    is_markup = elem.tag in TAGS_WITH_MARKUP

    if len(elem):  # children
        # Set indent of first child for tags with no text
        if not oneline and not is_markup and (not elem.text or not elem.text.strip()):
            elem.text = "\n" + (level + 1) * "  "

        if not elem.tail or not elem.tail.strip():
            if level:
                elem.tail = "\n" + level * "  "
            else:
                elem.tail = "\n"

        if is_markup:
            child = elem[-1]
        else:
            # recurse
            for child in elem:
                indent(
                    child,
                    level + 1,
                    internal=(internal or oneline),
                )

        # Clean up the last child
        if oneline:
            child.tail = clean_whitespace(child.tail, lambda x: x.rstrip())
        elif (
            not is_markup and not internal and (not child.tail or not child.tail.strip())
        ):
            child.tail = "\n" + level * "  "
    else:
        elem.text = clean_whitespace(elem.text, lambda x: x.strip())

        if internal:
            elem.tail = clean_whitespace(elem.tail)
        elif not elem.tail or not elem.tail.strip():
            elem.tail = "\n" + level * "  "


def ensure_minimal_diff(elem: etree._Element, reference: etree._Element) -> None:
    """Change a node to minimize the diff compared to a reference node, without changing logical equivalence.

    This will change the order of nodes and attributes to match the order in the reference whenever this makes no functional difference.  Elements that are logically equivalent to those in the reference will be copied exactly.

    Arguments:
        elem: The XML element whose children should be matches.
        reference: The XML element that serves as a reference.

    Raises:
        ValueError: If `elem` and `reference` do not have identical tags.
    """
    if elem.tag != reference.tag:
        raise ValueError(
            f"ensure_minimal_diff received two elements with different tags ({elem.tag} != {reference.tag})"
        )

    # If the entire elements are logically equivalent, we just clone the reference
    try:
        assert_equals(elem, reference)
        # NOTE: not using elem.getparent().replace() here since that breaks
        # recursion (it also removes the reference from its parent)
        elem.clear()
        for key, value in reference.items():
            elem.set(key, value)
        elem.text = reference.text
        elem.tail = reference.tail
        elem.extend(reference)
        return
    except AssertionError:
        pass  # Need to do more work

    # Sort attributes to match reference
    if len(elem.attrib) > 1 and len(reference.attrib) > 1:
        # Follow key order in reference, with keys new in elem coming last
        attrib_order = list(it.chain(reference.keys(), elem.keys()))
        # Since elem.attrib is an etree._Attrib, not a plain dictionary, we
        # clear attribs and reassign in the desired order
        attribs = sorted(elem.items(), key=lambda x: attrib_order.index(x[0]))
        elem.attrib.clear()
        for key, value in attribs:
            elem.set(key, value)

    # Sort child elements to match order in reference, if element allows reordering
    if elem.tag in TAGS_WITH_UNORDERED_CHILDREN:
        # Follow tag order in reference, with keys new in elem coming last
        ref_order = [x.tag for x in it.chain(reference, elem)]
        # Sort the child elements by the given reference order, reassigning
        # them to the parent element.  Since the sort key is only the tag,
        # elements will the same tag will always be grouped together, and
        # Python's sort stability guarantees that this does not change the
        # relative order of elements with the same tag.
        elem[:] = sorted(elem, key=lambda x: ref_order.index(x.tag))

    # From here on, children of elem have either been reordered to match
    # reference, or the order carries meaning.  Since elem may have added or
    # deleted child elements compared to reference, we now use difflib to find
    # "corresponding" child elements to recurse into.  Two elements are
    # considered as "corresponding" to each other if they have the same tag and
    # attributes.
    def make_match_keys(elems: Iterable[etree._Element]) -> list[str]:
        """Key used for element matching."""
        return [f"{elem.tag}{sorted(elem.items())}" for elem in elems]

    matcher = SequenceMatcher(
        a=make_match_keys(elem),
        b=make_match_keys(reference),
    )
    for a, b, size in matcher.get_matching_blocks():
        for idx_elem, idx_ref in zip(range(a, a + size), range(b, b + size)):
            ensure_minimal_diff(elem[idx_elem], reference[idx_ref])


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
