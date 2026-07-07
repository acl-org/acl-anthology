# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Functions for serializing to JSON."""

import re


_NAMES_ARRAY_RE: re.Pattern[bytes] = re.compile(
    rb'("names":\s*\[\n)(.*?)(\n[ \t]*\])',
    re.DOTALL,
)
"""Regex to match "names": [ ... ] blocks (non-greedy, across newlines)."""


_OBJ_RE: re.Pattern[bytes] = re.compile(
    rb"\{\n(?P<body>.*?)\n[ \t]*\}",
    re.DOTALL,
)
"""Regex to match individual dictionary objects.  Assumes that there are no nested dicts/lists as values."""


_PAIR_RE: re.Pattern[bytes] = re.compile(
    rb"""
    "(?:[^"\\]|\\.)*"   # the key: a JSON string, respecting \" escapes
    :\s*                # colon, then optional whitespace before the value
    "(?:[^"\\]|\\.)*"   # the value: also a JSON string, same escape handling
    """,
    re.VERBOSE,
)
"""Regex to extract key/value pairs from a dictionary object body.  Assumes that values will always be strings."""


def _collapse_obj(m: re.Match[bytes]) -> bytes:
    """Collapse all dictionaries within an object to a single line."""
    pairs = _PAIR_RE.findall(m.group("body"))
    return b"{" + b", ".join(pairs) + b"}"


def _collapse_names_array(m: re.Match[bytes]) -> bytes:
    """Collapse all dictionaries within a names array to a single line."""
    prefix, body, suffix = m.group(1), m.group(2), m.group(3)
    return prefix + _OBJ_RE.sub(_collapse_obj, body) + suffix


def collapse_names(json_object: bytes) -> bytes:
    """Collapse all name dictionaries in a serialized JSON object to a single line.

    Parameters:
        json_object: A byte string representing a JSON object, e.g. as produced by `msgspec.json.format`.

    Returns:
        A byte string of the same object, but with name dictionaries collapsed to a single line.

    Note:
        This assumes that name dictionaries only ever contain strings as values.
    """
    # Courtesy of Claude Sonnet 5.  More details, incl. more thorough regexes if
    # the assumption of only-string values should ever be invalidated:
    # <https://claude.ai/share/cd9b628e-f5d1-4130-ac7d-f3b61aa7f478>
    return _NAMES_ARRAY_RE.sub(_collapse_names_array, json_object)
