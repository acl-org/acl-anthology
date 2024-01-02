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

import pytest
from acl_anthology.utils import ids

test_cases_ids = (
    ("P18-1007", ("P18", "1", "7")),
    ("W18-2008", ("W18", "20", "8")),
    ("W18-2000", ("W18", "20", "0")),
    ("W18-6310", ("W18", "63", "10")),
    ("D19-1000", ("D19", "1", "0")),
    ("D19-1001", ("D19", "1", "1")),
    ("D19-5702", ("D19", "57", "2")),
    ("C69-1234", ("C69", "12", "34")),
    ("C68-1234", ("C68", "1", "234")),
    ("2022.acl-main.0", ("2022.acl", "main", "0")),
    ("2022.acl-main.1", ("2022.acl", "main", "1")),
    ("2023.mwe-1.5", ("2023.mwe", "1", "5")),
    ("P18-1", ("P18", "1", None)),
    ("W18-63", ("W18", "63", None)),
    ("D19-1", ("D19", "1", None)),
    ("D19-57", ("D19", "57", None)),
    ("2022.acl-main", ("2022.acl", "main", None)),
    ("2023.mwe-1", ("2023.mwe", "1", None)),
    ("P18", ("P18", None, None)),
    ("2022.acl", ("2022.acl", None, None)),
)


@pytest.mark.parametrize("full_id, parsed", test_cases_ids)
def test_parse_id(full_id, parsed):
    assert parsed == ids.parse_id(full_id)


@pytest.mark.parametrize("full_id, parsed", test_cases_ids)
def test_build_id(full_id, parsed):
    assert ids.build_id(*parsed) == full_id


@pytest.mark.parametrize("full_id, parsed", test_cases_ids)
def test_build_id_from_tuple(full_id, parsed):
    assert ids.build_id_from_tuple(parsed) == ids.build_id_from_tuple(full_id) == full_id


def test_build_id_wrong_type():
    with pytest.raises(TypeError):
        ids.build_id(("P18", "1", "7"))


test_cases_years = (
    ("P18-1007", "2018"),
    ("D19-1001", "2019"),
    ("C69-1234", "1969"),
    ("C68-1234", "1968"),
    ("2022.acl-main.1", "2022"),
    ("2023.mwe-1.5", "2023"),
    ("W99-1", "1999"),
    ("1971.fake-entry", "1971"),
)


@pytest.mark.parametrize("anthology_id, year", test_cases_years)
def test_infer_year(anthology_id, year):
    assert ids.infer_year(anthology_id) == year
