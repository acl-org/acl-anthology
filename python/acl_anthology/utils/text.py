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


from typing import cast


def interpret_pages(text: str) -> tuple[str, str]:
    """Splits up a 'pages' field into first and last page.

    Arguments:
        text: A text string representing a page range.

    Returns:
        A tuple `(first_page, last_page)`; if a known separator was found, this is the result of splitting the input on the separator; otherwise, we assume that the field contains a single page.
    """
    for s in ("--", "-", "–"):
        if text.count(s) == 1:
            return cast(tuple[str, str], tuple(text.split(s)))
    return (text, text)


def remove_extra_whitespace(text: str) -> str:
    """
    Arguments:
        text: An arbitrary string.

    Returns:
        The input string without newlines and consecutive whitespace replaced by a single whitespace character.
    """
    text = text.replace("\n", "").strip()
    # This was profiled to be 2x-4x faster than using re.sub();
    # also cf. https://stackoverflow.com/a/15913564
    while "  " in text:
        text = text.replace("  ", " ")
    return text
