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

"""Functions for manipulating Anthology IDs."""

from typing import Optional


AnthologyIDTuple = tuple[str, Optional[str], Optional[str]]
"""A tuple representing an Anthology ID."""

AnthologyID = str | AnthologyIDTuple
"""Any type that can be parsed into an Anthology ID."""


def build_id(
    collection_id: str, volume_id: Optional[str] = None, paper_id: Optional[str] = None
) -> str:
    """
    Transforms collection ID, volume ID, and paper ID to a width-padded
    Anthology ID.

    Parameters:
        collection_id: A collection ID, e.g. "P18".
        volume_id: A volume ID, e.g. "1".
        paper_id: A paper ID, e.g. "42".

    Returns:
        The full Anthology ID.

    Examples:
        >>> build_id("P18", "1", "1")
        P18-1001
        >>> build_id("2022.acl", "long", "42")
        2022.acl-long.42

    Warning:
        Does not perform any kind of input validation.
    """
    if not isinstance(collection_id, str):
        msg = f"collection_id must be str; got {type(collection_id)}"
        if isinstance(collection_id, (list, tuple)):
            msg = f"{msg}; did you mean to use build_id_from_tuple?"
        raise TypeError(msg)
    if volume_id is None:
        return collection_id
    elif collection_id[0].isdigit():
        if paper_id is not None:
            return f"{collection_id}-{volume_id}.{paper_id}"
        else:
            return f"{collection_id}-{volume_id}"
    else:  # pre-2020 IDs
        if (
            collection_id[0] == "W"
            or collection_id == "C69"
            or (collection_id == "D19" and int(volume_id) >= 5)
        ):
            anthology_id = f"{collection_id}-{int(volume_id):02d}"
            if paper_id is not None:
                anthology_id += f"{int(paper_id):02d}"
        else:
            anthology_id = f"{collection_id}-{int(volume_id):01d}"
            if paper_id is not None:
                anthology_id += f"{int(paper_id):03d}"

        return anthology_id


def build_id_from_tuple(anthology_id: AnthologyID) -> str:
    """
    Like [build_id()][acl_anthology.utils.ids.build_id], but takes any [AnthologyID][acl_anthology.utils.ids.AnthologyID] type.

    Parameters:
        anthology_id: The Anthology ID to convert into a string.

    Returns:
        The full Anthology ID.

    Examples:
        >>> build_id(("P18", "1", "1"))
        P18-1001
    """
    if isinstance(anthology_id, str):
        return anthology_id
    return build_id(*anthology_id)


def parse_id(anthology_id: AnthologyID) -> AnthologyIDTuple:
    """
    Parses an Anthology ID into its constituent collection ID, volume ID, and paper ID
    parts.

    Parameters:
        anthology_id: The Anthology ID to parse.

    Returns:
        The parsed collection ID, volume ID, and paper ID.

    Examples:
        >>> parse_id("P18-1007")
        ('P18', '1',  '7')
        >>> parse_id("W18-6310")
        ('W18', '63', '10')
        >>> parse_id("D19-1001")
        ('D19', '1',  '1')
        >>> parse_id("D19-5702")
        ('D19', '57', '2')
        >>> parse_id("2022.acl-main.1")
        ('2022.acl', 'main', '1')

        Also works with volumes:

        >>> parse_id("P18-1")
        ('P18', '1', None)
        >>> parse_id("W18-63")
        ('W18', '63', None)

        And even with just collections:

        >>> parse_id("P18")
        ('P18', None, None)

    Warning:
        Does not perform any kind of input validation.

    Note:
        For Anthology IDs prior to 2020, the volume ID is the first digit after the hyphen, except
        for the following situations, where it is the first two digits:

        - All collections starting with 'W'
        - The collection "C69"
        - All collections in "D19" where the first digit is >= 5
    """

    if isinstance(anthology_id, tuple):
        return anthology_id

    if "-" not in anthology_id:
        return (anthology_id, None, None)

    collection_id, rest = anthology_id.split("-")
    if collection_id[0].isdigit():
        # post-2020 IDs
        if "." in rest:
            return (collection_id, *(rest.split(".")))  # type: ignore
        else:
            return (collection_id, rest, None)
    else:
        # pre-2020 IDs
        if len(rest) < 4:
            # probably volume-only identifier
            return (collection_id, rest.lstrip("0"), None)
        elif (
            collection_id.startswith("W")
            or collection_id == "C69"
            or (collection_id == "D19" and int(rest[0]) >= 5)
        ):
            paper_id = rest[2:].lstrip("0")
            return (collection_id, rest[0:2].lstrip("0"), paper_id if paper_id else "0")
        else:
            paper_id = rest[1:].lstrip("0")
            return (collection_id, rest[0], paper_id if paper_id else "0")


def infer_year(anthology_id: AnthologyID) -> str:
    """Infer the year from an Anthology ID.

    Parameters:
        anthology_id: An arbitrary Anthology ID.

    Returns:
        The year of the item represented by the Anthology ID, as a four-character string.
    """
    collection_id, *_ = parse_id(anthology_id)

    if collection_id[0].isdigit():
        return collection_id.split(".")[0]

    digits = collection_id[1:]
    if int(digits) >= 60:
        year = f"19{digits}"
    else:
        year = f"20{digits}"

    return year
