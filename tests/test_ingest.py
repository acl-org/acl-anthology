"""Tests for bin/ingest.py."""

import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from acl_anthology.collections.types import VolumeType
from acl_anthology.text import MarkupText
from acl_anthology.people import Name
from bin.ingest import (
    abstract_has_empty_markup,
    build_name_split_index,
    check_for_anonymous_pdf,
    configure_event,
    ensure_venue,
    read_ingest_metadata,
    read_meta,
    resegment_name,
    register_suggested_sigs,
    register_volume_with_sig,
)

DATADIR = Path(__file__).resolve().parent / "data"


def test_resegment_name_accepts_explicit_index():
    name = Name("Arnab Sen", "Sharma")
    name_split_index = {(name.slugify(), 2): {1}}

    assert resegment_name(name, name_split_index) == Name("Arnab", "Sen Sharma")


@pytest.fixture
def name_split_preferences():
    canonical = Name("Alex", "De Silva")
    alias = Name("Alex De", "Silva")
    people = [
        SimpleNamespace(
            canonical_name=canonical,
            is_explicit=True,
            disable_name_matching=False,
        )
    ]
    anthology = SimpleNamespace(
        people=SimpleNamespace(
            by_name={canonical: ["alex-de-silva"], alias: ["alex-de-silva"]},
            values=lambda: iter(people),
        )
    )
    return SimpleNamespace(
        anthology=anthology, canonical=canonical, alias=alias, people=people
    )


def test_name_split_index_prefers_explicit_canonical_name(name_split_preferences):
    state = name_split_preferences

    index = build_name_split_index(state.anthology)

    assert index[(state.alias.slugify(), 2)] == {1}
    assert resegment_name(state.alias, index) == state.canonical


def test_name_split_preference_preserves_spelling_and_case(name_split_preferences):
    index = build_name_split_index(name_split_preferences.anthology)

    assert resegment_name(Name("ALEX DE", "SILVA"), index) == Name("ALEX", "DE SILVA")


@pytest.mark.parametrize("is_explicit, disabled", [(False, False), (True, True)])
def test_name_split_index_without_canonical_preference(
    name_split_preferences, is_explicit, disabled
):
    state = name_split_preferences
    state.people[0].is_explicit = is_explicit
    state.people[0].disable_name_matching = disabled

    index = build_name_split_index(state.anthology)

    assert index[(state.alias.slugify(), 2)] == {1, 2}
    assert resegment_name(state.alias, index) == state.alias


def test_name_split_index_preserves_conflicting_canonical_splits(name_split_preferences):
    state = name_split_preferences
    state.people.append(
        SimpleNamespace(
            canonical_name=state.alias,
            is_explicit=True,
            disable_name_matching=False,
        )
    )

    index = build_name_split_index(state.anthology)

    assert index[(state.alias.slugify(), 2)] == {1, 2}
    assert resegment_name(state.alias, index) == state.alias
    assert resegment_name(state.canonical, index) == state.canonical


@pytest.mark.parametrize(
    "canonical",
    [Name("Alexandre", "De Silva"), Name("Alex-De", "Silva")],
)
def test_name_split_preference_requires_matching_full_form(
    name_split_preferences, canonical
):
    state = name_split_preferences
    state.people[0].canonical_name = canonical

    index = build_name_split_index(state.anthology)

    assert index[(state.alias.slugify(), 2)] == {1, 2}
    assert resegment_name(state.alias, index) == state.alias


def test_read_meta_accepts_multiple_spaces_between_key_and_value(tmp_path):
    meta_path = tmp_path / "meta"
    meta_path.write_text("booktitle  Proceedings of EAMT 2026 (Volume 1)\n")

    assert read_meta(str(meta_path))["booktitle"] == (
        "Proceedings of EAMT 2026 (Volume 1)"
    )


def test_ensure_venue_creates_without_saving_individual_venue():
    anthology = MagicMock()
    anthology.venues.__contains__.return_value = False
    venue = anthology.venues.create.return_value

    venue_slug, venue_type = ensure_venue(
        anthology, "EVALITA", "Evaluation Campaign", is_conference=True
    )

    assert venue_slug == "evalita"
    assert venue_type == "conference"
    anthology.venues.create.assert_called_once_with(
        id="evalita", acronym="EVALITA", name="Evaluation Campaign"
    )
    venue.save.assert_not_called()


def test_ensure_venue_requires_type_for_new_venue():
    anthology = MagicMock()
    anthology.venues.__contains__.return_value = False

    with pytest.raises(ValueError, match=r"requires one of -w, -j, or -c"):
        ensure_venue(anthology, "EVALITA", "Evaluation Campaign")

    anthology.venues.create.assert_not_called()


def test_ensure_venue_does_not_require_type_for_existing_venue():
    anthology = MagicMock()
    anthology.venues.__contains__.return_value = True
    anthology.venues.__getitem__.return_value.type = "workshop"

    assert ensure_venue(anthology, "EVALITA", "Evaluation Campaign") == (
        "evalita",
        "workshop",
    )

    anthology.venues.create.assert_not_called()


def test_ensure_venue_warns_when_flag_conflicts_with_existing_type(capsys):
    anthology = MagicMock()
    anthology.venues.__contains__.return_value = True
    anthology.venues.__getitem__.return_value.type = "journal"

    assert ensure_venue(
        anthology, "TACL", "Transactions of the ACL", is_workshop=True
    ) == ("tacl", "journal")

    assert "declared as type journal" in capsys.readouterr().out


def ingest_args(tmp_path):
    return SimpleNamespace(
        is_workshop=False,
        is_journal=False,
        is_conference=False,
        pdfs_dir=tmp_path / "pdf",
        attachments_dir=tmp_path / "attachments",
    )


def test_aclpub_metadata_uses_inferred_journal_type(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "meta").write_text(
        "abbrev TACL\ntitle Transactions of the ACL\nyear 2026\nvolume 14\nissue 2\n"
    )

    with patch("bin.ingest.ensure_venue", return_value=("tacl", "journal")):
        metadata = read_ingest_metadata(
            MagicMock(), str(source), "aclpub", ingest_args(tmp_path)
        )

    assert metadata["volume_type"] == VolumeType.JOURNAL
    assert metadata["journal_volume"] == "14"
    assert metadata["journal_issue"] == "2"


def test_aclpub2_metadata_uses_inferred_workshop_type(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    meta = {
        "anthology_venue_id": "YNLG",
        "event_name": "Workshop on Young Researchers in Natural Language Generation",
        "year": "2025",
        "volume_name": "main",
        "book_title": "Proceedings of YNLG 2025",
        "editors": [],
        "sig": "SIGGEN",
    }

    with (
        patch("bin.ingest.parse_conf_yaml", return_value=meta),
        patch("bin.ingest.ensure_venue", return_value=("ynlg", "workshop")),
    ):
        metadata = read_ingest_metadata(
            MagicMock(), str(source), "aclpub2", ingest_args(tmp_path)
        )

    assert metadata["volume_type"] == VolumeType.PROCEEDINGS
    assert metadata["venue_ids"] == ["ynlg", "ws"]
    assert metadata["sig"] == "SIGGEN"


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Proceedings of the the Workshop", "Proceedings of the Workshop"),
        ("Proceedings of the The Workshop", "Proceedings of the Workshop"),
        ("Proceedings of the Theory Workshop", "Proceedings of the Theory Workshop"),
    ],
)
def test_aclpub2_normalizes_book_title(tmp_path, title, expected):
    source = tmp_path / "source"
    source.mkdir()
    meta = {
        "anthology_venue_id": "YNLG",
        "event_name": "Workshop on Young Researchers in Natural Language Generation",
        "year": "2025",
        "volume_name": "main",
        "book_title": title,
        "editors": [],
    }

    with (
        patch("bin.ingest.parse_conf_yaml", return_value=meta),
        patch("bin.ingest.ensure_venue", return_value=("ynlg", "workshop")),
    ):
        metadata = read_ingest_metadata(
            MagicMock(), str(source), "aclpub2", ingest_args(tmp_path)
        )

    assert metadata["title"].as_text() == expected


def test_aclpub_normalizes_frontmatter_book_title_preserving_markup(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "meta").write_text("abbrev EAMT\ntitle EAMT\nyear 2026\nvolume 1\n")
    title = MarkupText.from_latex(r"Proceedings of the The \textit{Workshop}")

    with (
        patch("bin.ingest.ensure_venue", return_value=("eamt", "conference")),
        patch(
            "bin.ingest._aclpub_frontmatter_data",
            return_value={"title": title, "editors": [], "authors": []},
        ),
    ):
        metadata = read_ingest_metadata(
            MagicMock(), str(source), "aclpub", ingest_args(tmp_path)
        )

    assert metadata["title"].as_xml() == "Proceedings of the <i>Workshop</i>"


def test_aclpub_normalizes_meta_book_title(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "meta").write_text(
        "abbrev EAMT\ntitle EAMT\nyear 2026\nvolume 1\n"
        "booktitle Proceedings of the the Workshop\n"
    )

    with patch("bin.ingest.ensure_venue", return_value=("eamt", "conference")):
        metadata = read_ingest_metadata(
            MagicMock(), str(source), "aclpub", ingest_args(tmp_path)
        )

    assert metadata["title"].as_text() == "Proceedings of the Workshop"


def test_register_volume_with_sig_stores_sig_on_volume():
    anthology = SimpleNamespace(sigs={"sigdat": object()})
    volume = SimpleNamespace(full_id="2026.acl-main", sig_ids=())

    register_volume_with_sig(anthology, "SIGDAT", volume)
    register_volume_with_sig(anthology, "sigdat", volume)

    assert volume.sig_ids == ("sigdat",)


def test_register_suggested_sigs_stores_associations_from_venues(caplog):
    sigann = SimpleNamespace(id="sigann")
    siglex = SimpleNamespace(id="siglex")
    starsem = MagicMock(id="starsem")
    starsem.sigs.return_value = [siglex, sigann]
    semeval = MagicMock(id="semeval")
    semeval.sigs.return_value = [siglex]
    ws = MagicMock(id="ws")
    ws.sigs.return_value = []
    volume = MagicMock(
        full_id="2026.starsem-1",
        sig_ids=("sigann",),
    )
    volume.venues.return_value = [starsem, semeval, ws]

    def add_sig(sig):
        volume.sig_ids += (sig.id,)

    volume.add_sig.side_effect = add_sig

    with caplog.at_level(logging.INFO):
        register_suggested_sigs(volume)
        register_suggested_sigs(volume)

    volume.add_sig.assert_called_once_with(siglex)
    assert volume.sig_ids == ("sigann", "siglex")
    for venue in (starsem, semeval, ws):
        assert venue.sigs.call_count == 2
    assert "based on venue association(s): starsem" in caplog.text
    assert len(caplog.records) == 1


# PDFs that still carry an "Anonymous ... submission" header and should be
# flagged by check_for_anonymous_pdf. The supplementary attachments were
# uploaded without de-anonymization, unlike their published main papers.
ANONYMOUS_PDFS = [
    "W18-6417.pdf",
    "2020.conll-1.8.OptionalSupplementaryMaterial.pdf",
    "D18-1202.Attachment.pdf",
    "2020.conll-1.33.OptionalSupplementaryMaterial.pdf",
]

# Properly published (de-anonymized) PDFs that should not be flagged.
CLEAN_PDFS = [
    "W18-6418.pdf",
    "2020.conll-1.8.pdf",
    "D18-1202.pdf",
    "2020.conll-1.33.pdf",
]


def test_abstract_paragraph_is_not_empty_markup():
    abstract = MarkupText.from_latex("First paragraph.\n\nSecond paragraph.")
    assert not abstract_has_empty_markup(abstract)


def test_abstract_empty_inline_markup_is_rejected():
    abstract = MarkupText.from_latex(r"Text with \textit{} empty markup")
    assert abstract_has_empty_markup(abstract)


@pytest.mark.parametrize("filename", ANONYMOUS_PDFS)
def test_check_for_anonymous_pdf_flags_anonymous(filename, caplog):
    """A PDF containing an "Anonymous ... submission" line should be flagged."""
    pdf_path = DATADIR / filename
    with caplog.at_level(logging.WARNING):
        check_for_anonymous_pdf(str(pdf_path))
    assert any("Potentially anonymous PDF" in record.message for record in caplog.records)


@pytest.mark.parametrize("filename", CLEAN_PDFS)
def test_check_for_anonymous_pdf_accepts_clean(filename, caplog):
    """A properly de-anonymized PDF should not be flagged."""
    pdf_path = DATADIR / filename
    with caplog.at_level(logging.WARNING):
        check_for_anonymous_pdf(str(pdf_path))
    assert not any(
        "Potentially anonymous PDF" in record.message for record in caplog.records
    )


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
