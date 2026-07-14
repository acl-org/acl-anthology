"""Tests for bin/create_hugo_data.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bin.create_hugo_data import paper_to_dict

from acl_anthology import Anthology


@pytest.fixture(scope="module")
def anthology():
    return Anthology.from_within_repo()


def test_external_paper_url_is_not_exported_as_pdf(anthology):
    data = paper_to_dict(anthology.get_paper("1998.amta-papers.1"))

    assert data["external"] == (
        "https://link.springer.com/chapter/10.1007/3-540-49478-2_1"
    )
    assert "pdf" not in data
    assert "thumbnail" not in data


def test_local_paper_url_is_exported_as_pdf(anthology):
    data = paper_to_dict(anthology.get_paper("2025.acl-long.1"))

    assert data["pdf"] == "https://aclanthology.org/2025.acl-long.1.pdf"
    assert data["thumbnail"] == ("https://aclanthology.org/thumb/2025.acl-long.1.jpg")
    assert "external" not in data
