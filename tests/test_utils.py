import pytest
from acl_anthology.utils import (
    build_anthology_id,
    deconstruct_anthology_id,
)

test_cases_ids = (
    ("P18-1007", ("P18", "1", "7")),
    ("W18-2008", ("W18", "20", "8")),
    ("W18-6310", ("W18", "63", "10")),
    ("D19-1001", ("D19", "1", "1")),
    ("D19-5702", ("D19", "57", "2")),
    ("C69-1234", ("C69", "12", "34")),
    ("C68-1234", ("C68", "1", "234")),
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

@pytest.mark.parametrize('full_id, deconstructed', test_cases_ids)
def test_deconstruct_anthology_id(full_id, deconstructed):
    assert deconstructed == deconstruct_anthology_id(full_id)

@pytest.mark.parametrize('full_id, deconstructed', test_cases_ids)
def test_build_anthology_id(full_id, deconstructed):
    if deconstructed[1] is not None:
        assert build_anthology_id(*deconstructed) == full_id
