# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
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

import pytest
from acl_anthology.utils import text

test_cases_pages = (
    ("1-1", ("1", "1")),
    ("14-17", ("14", "17")),
    ("42–44", ("42", "44")),
    ("45–45", ("45", "45")),
    ("96--101", ("96", "101")),
    ("557", ("557", "557")),
)

test_cases_whitespace = (
    (" ", ""),
    ("\n\n  \n            \n \n", ""),
    ("   text   ", "text"),
    ("Foo\nBar\nBaz ", "FooBarBaz"),
    (" Lorem  ipsum   dolor      sit\n\n\n amen", "Lorem ipsum dolor sit amen"),
)

test_cases_clean_unicode = (
    ("break\u00adable", "breakable"),  # soft hyphen
    ("break‐able", "break-able"),  # dash
    ("bı́r", "bír"),  # combining diacritic on ı vs. composed character í
    ("afﬁrm", "affirm"),  # ligature
    ("see： here", "see: here"),  # wide colon
    ("fn²", "fn²"),  # unchanged
)


@pytest.mark.parametrize("inp, out", test_cases_pages)
def test_interpret_pages(inp, out):
    assert text.interpret_pages(inp) == out


@pytest.mark.parametrize("inp, out", test_cases_whitespace)
def test_remove_extra_whitespace(inp, out):
    assert text.remove_extra_whitespace(inp) == out


@pytest.mark.parametrize("inp, out", test_cases_clean_unicode)
def test_clean_unicode(inp, out):
    assert text.clean_unicode(inp) == out
