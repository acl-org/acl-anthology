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

from typing import Optional, Tuple


def build_anthology_id(
    collection_id: str, volume_id: str, paper_id: Optional[str] = None
) -> str:
    """
    Transforms collection id, volume id, and paper id to a width-padded
    Anthology ID. e.g., ('P18', '1', '1') -> P18-1001.
    """
    if collection_id[0].isdigit():
        if paper_id is not None:
            return f"{collection_id}-{volume_id}.{paper_id}"
        elif volume_id is not None:
            return f"{collection_id}-{volume_id}"
        else:
            return collection_id

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


def deconstruct_anthology_id(anthology_id: str) -> Tuple[str, str, str]:
    """
    Parses an Anthology ID into its constituent collection id, volume id, and paper id
    parts. e.g,

        P18-1007 -> ('P18', '1',  '7')
        W18-6310 -> ('W18', '63', '10')
        D19-1001 -> ('D19', '1',  '1')
        D19-5702 -> ('D19', '57', '2')
        2022.acl-main.1 -> ('2022.acl', 'main', '1')

    Also works with volumes:

        P18-1 -> ('P18', '1', None)
        W18-63 -> ('W18', '63', None)

    And even with just collections:

        P18 -> ('P18', None, None)

    For Anthology IDs prior to 2020, the volume ID is the first digit after the hyphen, except
    for the following situations, where it is the first two digits:

    - All collections starting with 'W'
    - The collection "C69"
    - All collections in "D19" where the first digit is >= 5
    """

    if "-" not in anthology_id:
        return (anthology_id, None, None)

    collection_id, rest = anthology_id.split("-")
    if collection_id[0].isdigit():
        # post-2020 IDs
        if "." in rest:
            return (collection_id, *(rest.split(".")))
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
            return (collection_id, rest[0:2].lstrip("0"), rest[2:].lstrip("0"))
        else:
            return (collection_id, rest[0], rest[1:].lstrip("0"))
