"""Tests for the Underline video request TSV export."""

import csv
import io
from pathlib import Path
import shutil
import sys

import pytest
from lxml import etree

from acl_anthology import Anthology
from acl_anthology.collections.paper import PaperDeletionNotice
from acl_anthology.collections.types import PaperType
from acl_anthology.people import Name, NameSpecification
from acl_anthology.text import MarkupText
from bin.export_video_request import export_video_request, main


@pytest.fixture
def anthology(tmp_path):
    source = Path(__file__).resolve().parents[1] / "python/tests/data/anthology"
    shutil.copytree(source, tmp_path / "data")
    anthology = Anthology(tmp_path / "data").load_all()
    collection = anthology.create_collection("2026.videotest")
    event = collection.create_event()
    main_volume = collection.create_volume("main", title="Main")
    main_volume.create_paper(
        title=MarkupText.from_xml(
            etree.fromstring(
                "<title>A <fixed-case>TSV</fixed-case>\twith \n"
                '"quotes" &amp; markup</title>'
            )
        ),
        authors=[
            NameSpecification(Name("Alice", "Example")),
            NameSpecification(Name(None, "Mononym")),
        ],
    )
    main_volume.create_paper(title="Front matter", type=PaperType.FRONTMATTER)
    main_volume.create_paper(title="Back matter", type=PaperType.BACKMATTER)
    main_volume.create_paper(
        title="Removed",
        deletion=PaperDeletionNotice("removed", "Test", "2026-01-01"),
    )
    collection.create_volume("demo", title="Demos").create_paper(title="Demo")
    workshop = anthology.create_collection("2026.videoworkshop").create_volume(
        "1", title="Workshop"
    )
    workshop.create_paper(
        title="Workshop paper",
        authors=[NameSpecification(Name("Ren\u00e9", "Example"))],
    )
    event.add_colocated(main_volume)
    event.add_colocated(workshop)
    anthology.create_collection("2026.unrelatedvideo").create_volume(
        "1", title="Unrelated"
    ).create_paper(title="Unrelated paper")
    return anthology


def test_export_includes_all_main_and_colocated_volumes_once(anthology):
    stream = io.StringIO()
    export_video_request(anthology, "videotest-2026", stream)
    rows = list(csv.reader(io.StringIO(stream.getvalue()), delimiter="\t"))
    assert rows == [
        ["anthology_id", "title", "authors"],
        [
            "2026.videotest-main.1",
            'A TSV with "quotes" & markup',
            "Alice Example; Mononym",
        ],
        ["2026.videotest-demo.1", "Demo", ""],
        ["2026.videoworkshop-1.1", "Workshop paper", "Ren\u00e9 Example"],
    ]
    assert len(stream.getvalue().splitlines()) == len(rows)


def test_missing_event_fails_without_writing_header(anthology):
    stream = io.StringIO()
    with pytest.raises(ValueError, match="Event nonexistent-2026 not found"):
        export_video_request(anthology, "nonexistent-2026", stream)
    assert stream.getvalue() == ""


def test_missing_colocated_volume_fails_without_partial_output(anthology):
    anthology.get_event("videotest-2026").add_colocated("2026.missingvideo-1")
    stream = io.StringIO()
    with pytest.raises(ValueError, match="which doesn't exist"):
        export_video_request(anthology, "videotest-2026", stream)
    assert stream.getvalue() == ""


def test_empty_event_exports_header(anthology):
    anthology.create_collection("2026.emptyvideo").create_event()
    stream = io.StringIO()
    export_video_request(anthology, "emptyvideo-2026", stream)
    assert stream.getvalue() == "anthology_id\ttitle\tauthors\n"


@pytest.mark.parametrize("output_file", [False, True])
def test_cli_stdout_and_file(anthology, tmp_path, monkeypatch, capsys, output_file):
    monkeypatch.setattr(Anthology, "from_within_repo", lambda: anthology)
    output = tmp_path / "videos.tsv"
    argv = ["export_video_request.py", "videotest-2026"]
    if output_file:
        argv.extend(["-o", str(output)])
    monkeypatch.setattr(sys, "argv", argv)
    main()
    captured = capsys.readouterr()
    expected = io.StringIO()
    export_video_request(anthology, "videotest-2026", expected)
    if output_file:
        assert output.read_text(encoding="utf-8") == expected.getvalue()
        assert captured.out == ""
    else:
        assert captured.out == expected.getvalue()
    assert captured.err == ""


def test_cli_unknown_event(anthology, monkeypatch, capsys):
    monkeypatch.setattr(Anthology, "from_within_repo", lambda: anthology)
    monkeypatch.setattr(sys, "argv", ["export_video_request.py", "nonexistent-2026"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Event nonexistent-2026 not found" in captured.err
