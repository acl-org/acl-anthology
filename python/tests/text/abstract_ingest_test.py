# Copyright 2025 ACL Anthology contributors
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

"""Tests for LaTeX abstract ingestion and XML serialization.

Test data lives in ``test_abstract_ingest/abstracts.yaml``.
"""

import difflib
import pytest
import yaml
from lxml import etree
from pathlib import Path
from acl_anthology.text import MarkupText

DATADIR = Path(__file__).with_name("test_abstract_ingest")


def _load_cases():
    with open(DATADIR / "abstracts.yaml", encoding="utf-8") as f:
        entries = yaml.safe_load(f)
    return [(e["in"].rstrip("\n"), e["expected"].rstrip("\n")) for e in entries]


def _word_diff(a: str, b: str) -> str:
    """Return a compact word-level diff between two strings."""
    a_words = a.split()
    b_words = b.split()
    parts = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, a_words, b_words
    ).get_opcodes():
        if tag == "equal":
            continue
        if tag in ("replace", "delete"):
            parts.append(f"- {' '.join(a_words[i1:i2])}")
        if tag in ("replace", "insert"):
            parts.append(f"+ {' '.join(b_words[j1:j2])}")
    return "\n".join(parts)


ABSTRACT_CASES = _load_cases()


@pytest.mark.parametrize(
    "latex_input, expected_xml",
    ABSTRACT_CASES,
    ids=[f"case_{i}" for i in range(len(ABSTRACT_CASES))],
)
def test_abstract_latex_to_xml(latex_input, expected_xml):
    """Test that a LaTeX abstract string is correctly converted to Anthology XML."""
    markup = MarkupText.from_latex_maybe(latex_input)
    element = markup.to_xml("abstract")
    result = etree.tostring(element, encoding="unicode")
    assert result == expected_xml, (
        f"Word-level diff (- got, + expected):\n{_word_diff(result, expected_xml)}"
    )