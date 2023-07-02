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

import codecs
import re
from typing import Optional

import latexcodec  # noqa: F401


RE_OPENING_QUOTE = re.compile(r"(?<!\\)\"\b")
RE_CLOSING_QUOTE = re.compile(r"(?<!\\)\"")


def latex_encode(text: Optional[str]) -> str:
    """Encodes a text string for use in LaTeX/BibTeX.

    Assumes that the text does *not* contain any LaTeX commands!
    """
    if text is None:
        return ""
    text = str(codecs.encode(text, "ulatex+ascii", "keep"))
    return text


def latex_convert_quotes(text: str) -> str:
    """Converts regular quotes into LaTeX quotes."""
    text = RE_OPENING_QUOTE.sub("``", text)
    text = RE_CLOSING_QUOTE.sub("''", text)
    return text
