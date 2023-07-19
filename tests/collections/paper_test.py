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

import pytest
from acl_anthology.collections import CollectionIndex, Paper
from acl_anthology.text import MarkupText


@pytest.fixture
def index(anthology):
    return CollectionIndex(anthology)


def test_paper_minimum_attribs():
    paper_title = MarkupText.from_string("A minimal example")
    parent = None
    paper = Paper("42", parent, bibkey="nn-1900-minimal", title=paper_title)
    assert not paper.is_deleted
    assert paper.title == paper_title
