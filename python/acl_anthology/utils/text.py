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


from typing import cast, Optional


_MONTH_TO_NUM: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


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


def month_str2num(text: str) -> Optional[int]:
    """Convert a month string to a number, e.g. February -> 2

    Arguments:
        text: A text string representing a month value.

    Returns:
        None if the string doesn't correspond to a month; the numeric month value otherwise.

    Note:
        We're not using Python's datetime here since its behaviour depends on the system locale.
    """
    return _MONTH_TO_NUM.get(text.lower(), None)


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
