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

import attrs
from pathlib import Path

from acl_anthology.collections import Collection, Volume
from acl_anthology.people import NameSpecification as NameSpec
from acl_anthology.text import MarkupText

REPEAT = 1_000


def create_volume():
    volume_title = MarkupText.from_string("Lorem ipsum")
    volume_shorttitle = MarkupText.from_string("L.I.")
    parent = Collection("2023.acl", None, Path("."))
    _ = Volume(
        id="long",
        parent=parent,
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


def instantiate_volume_regularly():
    """Instantiate a Volume."""
    for _ in range(REPEAT):
        create_volume()


def instantiate_volume_without_validation():
    """Instantiate a class with attribute validation disabled."""
    for _ in range(REPEAT):
        with attrs.validators.disabled():
            create_volume()


__benchmarks__ = [
    (
        instantiate_volume_regularly,
        instantiate_volume_without_validation,
        "attrs: instantiate Volume with attrs.validators.disabled",
    ),
]
