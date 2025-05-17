# Copyright 2025 Marcel Bollmann <marcel@bollmann.me>
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
from acl_anthology.text import StopWords

test_cases_stopwords = (
    ("model", False),
    ("lstm", False),
    ("the", True),
    ("of", True),
    ("volume", False),
    ("first", False),
)

test_cases_volume_stopwords = (
    ("model", False),
    ("lstm", False),
    ("the", True),
    ("of", True),
    ("volume", True),
    ("first", True),
    ("thirtieth", True),
    ("30th", True),
    ("21st", True),
)


@pytest.mark.parametrize("word, is_stop", test_cases_stopwords)
def test_stopwords_contains(word, is_stop):
    assert StopWords.contains(word) == is_stop
    assert StopWords.is_stopword(word) == is_stop


@pytest.mark.parametrize("word, is_stop", test_cases_volume_stopwords)
def test_stopwords_is_volume_stopword(word, is_stop):
    assert StopWords.is_volume_stopword(word) == is_stop
