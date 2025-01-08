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

from __future__ import annotations

from attrs import define, field
import re
from rich.progress import track
from slugify import slugify
from typing import cast, TYPE_CHECKING

from ..containers import SlottedDict
from ..text import StopWords
from .paper import Paper

if TYPE_CHECKING:
    from .index import CollectionIndex


BIBKEY_MAX_NAMES = 2
"""The maximum number of names to consider when generating bibkeys."""


@define
class BibkeyIndex(SlottedDict[Paper]):
    """Index object which collects citation keys for all papers.

    Provides dictionary-like functionality mapping bibkeys to [Paper][acl_anthology.collections.collection.Paper] objects in the Anthology.

    Attributes:
        parent: The parent CollectionIndex instance to which this index belongs.
        is_data_loaded: A flag indicating whether the XML directory has already been indexed.
    """

    parent: CollectionIndex = field(repr=False, eq=False)
    is_data_loaded: bool = field(init=False, repr=True, default=False)

    def generate_bibkey(self, paper: Paper) -> str:
        """Generate a unique bibkey for the given paper.

        Parameters:
            paper: The paper for which a bibkey should be generated.

        Returns:
            The generated bibkey.

        Note:
            Calling this function will _not change_ the paper's bibkey nor add the bibkey to the index.
        """
        if not self.is_data_loaded:
            self.load()

        title_words = None

        if paper.is_frontmatter:
            # Proceedings volumes/frontmatter use {venue}-{year}-{volume_id}
            bibkey = (
                f"{slugify(paper.parent.venue_acronym)}-{paper.year}-{paper.volume_id}"
            )
        else:
            # Generate slugified author string, using '-etal' if necessary
            namespecs = paper.authors if paper.authors else paper.get_editors()
            if not namespecs:
                bibnames = "nn"
            elif len(namespecs) > BIBKEY_MAX_NAMES:
                bibnames = f"{slugify(namespecs[0].last)}-etal"
            else:
                bibnames = "-".join(slugify(ns.last) for ns in namespecs)

            # Generate slugified and filtered list of title words
            title_words = [
                word
                for word in slugify(paper.title.as_text()).split("-")
                if not StopWords.contains(word)
            ]

            # Regular papers use {authors}-{year}-{first_title_words}
            bibkey = f"{bibnames}-{paper.year}-{title_words.pop(0)}"

        # Guarantee uniqueness
        while bibkey in self.data:
            if title_words:
                # If we have unused title words, take the next one
                bibkey = f"{bibkey}-{title_words.pop(0)}"
            else:
                # Otherwise, add a number, starting from 2
                if (m := re.search(r"-([0-9]+)$", bibkey)) is not None:
                    number = int(m.group(1)) + 1
                    bibkey = m.re.sub(f"-{number}", bibkey)
                else:
                    bibkey = f"{bibkey}-2"

        return bibkey

    def _index_paper(self, bibkey: str, paper: Paper) -> None:
        """Add a paper to the index.

        Warning:
            This function should not be called manually. It is invoked automatically when a paper's bibkey is changed.

        Raises:
            ValueError: If the paper's bibkey is not None and is already in the index.
        """
        if not self.is_data_loaded:
            self.load()
        if bibkey in self.data:
            raise ValueError(
                f"Cannot index bibkey '{bibkey}' for paper {paper.full_id}; already assigned to {self.data[bibkey].full_id}"
            )
        self.data[bibkey] = paper

    def load(self) -> None:
        """Load an index of bibkeys."""
        # This function exists so we can later add the option to read the index
        # from a cache if it doesn't need re-building.
        if self.is_data_loaded:
            return
        self.build()
        self.is_data_loaded = True

    def reset(self) -> None:
        """Reset the index."""
        self.data = {}
        self.is_data_loaded = False

    def build(self, show_progress: bool = False) -> None:
        """Load the entire Anthology data and build an index of bibkeys.

        Raises:
            ValueError: If a non-unique bibkey is encountered.
        """
        self.reset()
        # Go through every single paper
        iterator = track(
            self.parent.values(),
            total=len(self.parent),
            disable=(not show_progress),
            description="Building bibkey index...",
        )
        for collection in iterator:
            for paper in collection.papers():
                if paper.bibkey in self.data:
                    raise ValueError(
                        f"Paper {paper.full_id} has bibkey {paper.bibkey}, which is already assigned to paper {self.data[paper.bibkey].full_id}"
                    )
                self.data[cast(str, paper.bibkey)] = paper
        self.is_data_loaded = True
