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

from attrs import define, field
import re
from slugify import slugify
from stop_words import get_stop_words


RE_ENGLISH_ORDINAL = re.compile(
    r"[0-9]+(st|nd|rd|th)|[a-z]+(ieth|enth)|first|second|third|fourth|fifth|sixth|eighth|ninth|twelfth"
)
STOPWORDS_VOLUMES = {
    "proceedings",
    "volume",
    "conference",
    "workshop",
    "annual",
    "meeting",
    "computational",
}


@define
class _StopWords:
    """This class exposes a (slugified) stop word list used for generating citation keys."""

    stopwords: set[str] = field(init=False, factory=set)
    loaded: bool = field(init=False, default=False)

    def load(self) -> None:
        self.stopwords = set(
            t for w in get_stop_words("en") for t in slugify(w).split("-")
        )
        self.loaded = True

    def contains(self, word: str) -> bool:
        """Check if a given word is contained in the stop word list.

        Parameters:
            word: The word to look up.

        Returns:
            True if `word` is a known stop word, False otherwise.
        """
        if not self.loaded:
            self.load()
        return word in self.stopwords

    def is_stopword(self, word: str) -> bool:
        """Alias for `self.contains`."""
        return self.contains(word)

    def is_volume_stopword(self, word: str) -> bool:
        """Check if a given word is considered a stop word in the context of volume titles.

        This will also return True on words like "proceedings" or "workshop", as well as ordinal expressions.

        Parameters:
            word: The word to look up.

        Returns:
            True if `word` is considered a volume-level stop word, False otherwise.
        """
        return (
            self.contains(word)
            or word in STOPWORDS_VOLUMES
            or RE_ENGLISH_ORDINAL.fullmatch(word) is not None
        )


StopWords = _StopWords()
