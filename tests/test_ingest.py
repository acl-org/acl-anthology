"""Tests for event metadata support in bin/ingest.py."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

import pytest

from acl_anthology.people import Name
from bin.ingest import configure_event, namespec_from


@pytest.mark.parametrize(
    "before, after",
    [
        (("marcel", "bollmann"), ("Marcel", "Bollmann")),
        (("MARCEL", "BOLLMANN"), ("Marcel", "Bollmann")),
        (("MIRYAM", "DE LHONEUX"), ("Miryam", "de Lhoneux")),
        (("simon", "von der weide"), ("Simon", "von der Weide")),
        (("marc-andre", "hackforth-jones"), ("Marc-Andre", "Hackforth-Jones")),
        (("james", "o'neill"), ("James", "O’Neill")),
        (("JAMES", "O’NEILL"), ("James", "O’Neill")),
        (("ken", "mcguire"), ("Ken", "McGuire")),
        (("C`ecile", "Fabre"), ("C‘ecile", "Fabre")),
        (("B.l.", "Webber"), ("B.L.", "Webber")),
        (("B.     ", "Webber"), ("B.", "Webber")),
        (("John C.s.", "Lui"), ("John C.S.", "Lui")),
        (("Santosh", "T.y.s.s"), ("Santosh", "T.Y.S.S")),
        ((None, "S.b.priya"), (None, "S.B.Priya")),
        (("Shri", "Sashmitha.s"), ("Shri", "Sashmitha.S")),
    ],
)
def test_namespec_from_normalizes_name(before, after):
    assert namespec_from(*before).name == Name(*after)


@pytest.mark.parametrize(
    "first, last",
    [
        ("Hal", "Daumé III"),
        ("Hal", "Daumé 3rd"),
        ("Jan", "Hajic jr."),
        ("Jan", "Hajic, jr."),
        ("B.L. B. LT", "B.L"),
    ],
)
def test_namespec_from_accepts_valid_name(first, last):
    namespec_from(first, last)


@pytest.mark.parametrize(
    "first, last",
    [
        ("Hal", "Daum?"),
        ("Mausam", "."),
        ("Mausam", "-"),
        ("Mausam", "_"),
        ("Noor-e-", "Hira"),
        ("Sir", "C3PO"),
        ("Bonnie", "Lynn_Webber"),
        ("b.", "Webber"),
        ("Jonathan q.", "Arbuckle"),
        ("B. l.", "Webber"),
        ("Bonnie.lynn", "Webber"),
        ("Bonnie", "Webber,"),
        ("Bonnie", ".Webber"),
        ("Bonnie", "Webber1"),
        ("Bonnie", "Webber*"),
    ],
)
def test_namespec_from_rejects_invalid_name(first, last):
    with pytest.raises(ValueError):
        namespec_from(first, last)


def test_name_library_preserves_supplied_casing():
    name = Name("John C.s.", "Lui")
    assert (name.first, name.last) == ("John C.s.", "Lui")


def event_args(tmp_path, **overrides):
    values = {
        "event_title": None,
        "event_location": None,
        "event_dates": None,
        "event_website": None,
        "event_handbook": None,
        "event_files_dir": tmp_path,
        "dry_run": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_configure_event_does_nothing_without_metadata(tmp_path):
    collection = MagicMock()

    configure_event(collection, event_args(tmp_path))

    collection.get_event.assert_not_called()


def test_configure_event_updates_existing_event_and_copies_handbook(tmp_path):
    handbook = tmp_path / "source.pdf"
    handbook.write_bytes(b"handbook")
    event = SimpleNamespace(
        title=None,
        location=None,
        dates=None,
        links={"other": "preserved"},
    )
    collection = MagicMock(id="2026.acl")
    collection.get_event.return_value = event
    event_files_dir = tmp_path / "events"

    configure_event(
        collection,
        event_args(
            event_files_dir,
            event_title="64th Annual Meeting",
            event_location="San Diego, California, United States",
            event_dates="July 2–7, 2026",
            event_website="https://2026.aclweb.org",
            event_handbook=handbook,
        ),
    )

    destination = event_files_dir / "handbooks" / "acl" / "2026.acl.handbook.pdf"
    assert destination.read_bytes() == b"handbook"
    assert event.title == "64th Annual Meeting"
    assert event.location == "San Diego, California, United States"
    assert event.dates == "July 2–7, 2026"
    assert event.links["other"] == "preserved"
    assert event.links["website"].name == "https://2026.aclweb.org"
    assert event.links["handbook"].name == "2026.acl.handbook.pdf"
    assert event.links["handbook"].checksum is None


def test_configure_event_creates_event_and_supports_dry_run(tmp_path):
    handbook = tmp_path / "source.pdf"
    handbook.write_bytes(b"handbook")
    event = SimpleNamespace(links={})
    collection = MagicMock(id="2026.acl")
    collection.get_event.return_value = None
    collection.create_event.return_value = event
    event_files_dir = tmp_path / "events"

    configure_event(
        collection,
        event_args(
            event_files_dir,
            event_handbook=handbook,
            dry_run=True,
        ),
    )

    collection.create_event.assert_called_once_with()
    destination = event_files_dir / "handbooks" / "acl" / "2026.acl.handbook.pdf"
    assert not destination.exists()
    assert event.links["handbook"].checksum is None
