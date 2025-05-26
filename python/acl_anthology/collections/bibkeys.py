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
from typing import TYPE_CHECKING

from .. import constants
from ..containers import SlottedDict
from ..exceptions import AnthologyDuplicateIDError
from ..text import StopWords
from ..utils.logging import get_logger
from .paper import Paper

if TYPE_CHECKING:
    from .index import CollectionIndex


log = get_logger()


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

    def _index_paper(self, bibkey: str, paper: Paper) -> str:
        """Add a paper to the index.

        If the supplied bibkey is [`constants.NO_BIBKEY`][acl_anthology.constants.NO_BIBKEY], this will trigger creation of a new bibkey.

        Warning:
            This function should not be called manually. It is invoked automatically when a paper's bibkey is changed.

        Returns:
            The bibkey that was indexed.

        Raises:
            AnthologyDuplicateIDError: If the bibkey is not [`constants.NO_BIBKEY`][acl_anthology.constants.NO_BIBKEY] and is already in the index pointing to another paper.
        """
        if not self.is_data_loaded:
            self.load()

        if paper.bibkey in self.data:
            del self.data[paper.bibkey]

        if bibkey == constants.NO_BIBKEY:
            bibkey = self.generate_bibkey(paper)
        elif bibkey in self.data:
            raise AnthologyDuplicateIDError(
                bibkey,
                f"Cannot index bibkey '{bibkey}' for paper {paper.full_id}; already assigned to {self.data[bibkey].full_id}",
            )

        self.data[bibkey] = paper
        return bibkey

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
            AnthologyDuplicateIDError: If a non-unique bibkey is encountered.  In case of multiple errors, only one exception is raised at the end, and all errors are sent to the logger.
        """
        self.reset()
        # Go through every single paper
        iterator = track(
            self.parent.values(),
            total=len(self.parent),
            disable=(not show_progress),
            description="Building bibkey index...",
        )
        errors = []
        for collection in iterator:
            for paper in collection.papers():
                if paper.bibkey in self.data:
                    log.error(
                        f"Paper {paper.full_id} has bibkey {paper.bibkey}, which is already assigned to paper {self.data[paper.bibkey].full_id}"
                    )
                    errors.append(paper.bibkey)
                self.data[paper.bibkey] = paper
        if errors:
            raise AnthologyDuplicateIDError(
                errors, "There were duplicate bibkeys while building the bibkey index."
            )
        self.is_data_loaded = True
