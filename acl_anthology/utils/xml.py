# Copyright 2023 Marcel Bollmann <marcel@bollmann.me>
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
from lxml import etree
from typing import Optional
from xml.sax.saxutils import escape as xml_escape


def xml_escape_or_none(t: Optional[str]) -> Optional[str]:
    """Like [xml.sax.saxutils.escape][], but accepts [None][]."""
    return None if t is None else xml_escape(t)


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


def xsd_boolean(value: str) -> bool:
    """Converts an xsd:boolean value to a bool."""
    if value in ("0", "false"):
        return False
    elif value in ("1", "true"):
        return True
    raise ValueError(f"Not a valid xsd:boolean value: '{value}'")
