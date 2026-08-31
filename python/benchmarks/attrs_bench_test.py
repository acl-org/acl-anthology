# Copyright 2023-2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Is it worth disabling attrs' validators when instantiating many objects?"""

import attrs
import pytest
from pathlib import Path

from acl_anthology import Anthology
from acl_anthology.collections import Collection, Volume
from acl_anthology.people import NameSpecification as NameSpec
from acl_anthology.text import MarkupText

SCRIPTDIR = Path(__file__).parent.resolve()
TESTDATADIR = SCRIPTDIR / ".." / "tests" / "data" / "anthology"


class CollectionIndexStub:
    """Minimal stand-in for a CollectionIndex, just enough for `Volume.root`
    (`self.parent.parent.parent`) to resolve to a real Anthology instance."""

    def __init__(self, parent):
        self.parent = parent


@pytest.fixture(scope="module")
def collection():
    anthology = Anthology(datadir=TESTDATADIR)
    return Collection("2023.acl", CollectionIndexStub(anthology), Path("."))


def instantiate_volume(collection):
    volume_title = MarkupText.from_string("Lorem ipsum")
    volume_shorttitle = MarkupText.from_string("L.I.")
    return Volume(
        id="long",
        parent=collection,
        type="proceedings",
        booktitle=volume_title,
        year="2023",
        address="Online",
        doi="10.100/0000",
        editors=[NameSpec("Bollmann, Marcel")],
        ingest_date="2023-01-12",
        isbn="0000-0000-0000",
        month="jan",
        pdf=None,
        publisher="Myself",
        shortbooktitle=volume_shorttitle,
        venue_ids=["li", "acl"],
    )


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "disable_validation", [False, True], ids=["validated", "unvalidated"]
)
def test_instantiate_volume(benchmark, collection, disable_validation):
    if disable_validation:
        with attrs.validators.disabled():
            benchmark(instantiate_volume, collection)
    else:
        benchmark(instantiate_volume, collection)
