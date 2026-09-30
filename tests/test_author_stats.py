"""Tests for current and historical author statistics."""

from datetime import date
import json
from pathlib import Path
import shutil

import pytest

from acl_anthology import Anthology
from acl_anthology.collections.paper import PaperDeletionNotice
from acl_anthology.collections.types import PaperType
from acl_anthology.people import Name, NameSpecification
from bin.author_stats import (
    checkpoint_revision,
    compute_authorship_stats,
    month_starts,
    update_history,
)


@pytest.fixture
def anthology(tmp_path):
    source = Path(__file__).resolve().parents[1] / "python/tests/data/anthology"
    shutil.copytree(source, tmp_path / "data")
    return Anthology(tmp_path / "data").load_all()


def test_counts_namespecs_and_deduplicates_aliases_and_earlier_years(anthology):
    baseline = compute_authorship_stats(anthology)
    person = anthology.people.create(
        "metrics-alice",
        [Name("Alice", "Metrics"), Name("A.", "Metrics")],
        orcid="0000-0002-1825-0097",
    )
    anthology.people.create("metrics-bob", [Name("Bob", "Metrics")])
    anthology.people.create("metrics-editor", [Name("Editor", "Metrics")])

    def authors():
        return [
            NameSpecification(Name("Alice", "Metrics"), id=person.id),
            NameSpecification(Name("Bob", "Metrics"), id="metrics-bob"),
            NameSpecification(Name("Carol", "Metrics")),
            NameSpecification(Name("Dave", "Metrics")),
        ]

    for year in (2018, 2019, 2026):
        volume = anthology.create_collection(f"{year}.metrics").create_volume(
            "main",
            title="Metrics",
            editors=[NameSpecification(Name("Editor", "Metrics"), id="metrics-editor")],
        )
        volume.create_paper(title="Metrics paper", authors=authors())
        volume.create_paper(
            title="Repeated author",
            authors=[NameSpecification(Name("A.", "Metrics"), id=person.id)],
        )
        volume.create_paper(
            title="Front matter", authors=authors(), type=PaperType.FRONTMATTER
        )
        volume.create_paper(
            title="Removed",
            authors=authors(),
            deletion=PaperDeletionNotice("removed", "Test", "2026-01-01"),
        )

    stats = compute_authorship_stats(anthology)
    years = {row["year"]: row for row in stats["years"]}
    for year in (2018, 2019, 2026):
        assert years[year] == {
            "year": year,
            "authorships": [2, 1, 0, 2],
            "authors": [1, 1, 0, 2],
        }
    old = next(
        (row for row in baseline["years"] if row["year"] == 0),
        {"authorships": [0] * 4, "authors": [0] * 4},
    )
    assert years[0]["authorships"] == [
        a + b for a, b in zip(old["authorships"], [4, 2, 0, 4])
    ]
    assert years[0]["authors"] == [a + b for a, b in zip(old["authors"], [1, 1, 0, 2])]
    assert stats["totals"] == [a + b for a, b in zip(baseline["totals"], [1, 2, 0, 2])]


def test_legacy_explicit_people_are_verified_and_orcid_is_on_namespecs(anthology):
    person = anthology.people.create(
        "metrics-legacy", [Name("Legacy", "Metrics")], orcid="0000-0002-1825-0097"
    )
    volume = anthology.create_collection("2019.metrics").create_volume(
        "main", title="Legacy"
    )
    volume.create_paper(
        title="Legacy paper",
        authors=[
            NameSpecification(Name("Legacy", "Metrics"), id=person.id, orcid=person.orcid)
        ],
    )
    stats = compute_authorship_stats(anthology, legacy=True)
    row = next(row for row in stats["years"] if row["year"] == 2019)
    assert row["authorships"] == [1, 0, 0, 0]
    assert row["authors"] == [1, 0, 0, 0]
    assert stats["totals"][0] >= 1


def test_openreview_only_namespecs_are_counted_once_per_person(anthology):
    volume = anthology.create_collection("2026.metrics").create_volume(
        "main", title="Metrics"
    )
    spec = NameSpecification(Name("OpenReview", "Only"), openreview="~OpenReview_Only1")
    volume.create_paper(title="First", authors=[spec])
    volume.create_paper(
        title="Second",
        authors=[
            NameSpecification(Name("OpenReview", "Only")),
            NameSpecification(Name("No", "Identifier")),
        ],
    )
    stats = compute_authorship_stats(anthology)
    row = next(row for row in stats["years"] if row["year"] == 2026)
    assert row["authorships"] == [0, 0, 2, 1]
    assert row["authors"] == [0, 0, 1, 1]


def test_month_starts_and_invalid_range():
    assert month_starts(date(2026, 3, 20)) == [
        date(2026, 2, 1),
        date(2026, 3, 1),
    ]
    assert month_starts(date(2027, 1, 1))[-1] == date(2027, 1, 1)
    with pytest.raises(ValueError, match="February"):
        month_starts(date(2026, 1, 1))


def test_checkpoint_is_strictly_before_midnight_even_with_nonmonotonic_dates(
    tmp_path, monkeypatch
):
    def log(repo, *args):
        assert args == ("log", "--first-parent", "--format=%H %ct", "main")
        # Exclude midnight and continue past an ancestor with a later timestamp.
        return "child 1767225601\nmidnight 1767225600\nlater 1767225602\nolder 1767225599"

    monkeypatch.setattr("bin.author_stats.git", log)
    assert checkpoint_revision(tmp_path, "main", date(2026, 1, 1)) == "older"
    with pytest.raises(ValueError, match="No commit"):
        checkpoint_revision(tmp_path, "main", date(2025, 1, 1))


def test_history_cache_and_changed_revision(tmp_path, monkeypatch):
    output = tmp_path / "history.json"
    revisions = {"2026-02-01": "feb", "2026-03-01": "mar"}
    calls = []
    monkeypatch.setattr("bin.author_stats.git", lambda *args: "false")
    monkeypatch.setattr(
        "bin.author_stats.checkpoint_revision",
        lambda repo, ref, checkpoint: revisions[str(checkpoint)],
    )

    def compute(repo, revision):
        calls.append(revision)
        return {"years": [], "totals": [1, 2, 3, 4], "identity_model": "verified"}

    monkeypatch.setattr("bin.author_stats.compute_checkpoint", compute)
    update_history(tmp_path, "main", date(2026, 3, 1), output)
    assert calls == ["feb", "mar"]
    original = output.read_bytes()
    update_history(tmp_path, "main", date(2026, 3, 1), output)
    assert calls == ["feb", "mar"]
    assert output.read_bytes() == original
    revisions["2026-03-01"] = "new-mar"
    update_history(tmp_path, "main", date(2026, 3, 1), output)
    assert calls == ["feb", "mar", "new-mar"]
    assert json.loads(output.read_text())["checkpoints"][1]["revision"] == "new-mar"


def test_old_history_schema_recomputes_checkpoints(tmp_path, monkeypatch):
    output = tmp_path / "history.json"
    output.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "checkpoints": [
                    {"date": "2026-01-01", "revision": "jan"},
                    {"date": "2026-02-01", "revision": "feb"},
                ],
            }
        )
    )
    monkeypatch.setattr("bin.author_stats.git", lambda *args: "false")
    monkeypatch.setattr("bin.author_stats.checkpoint_revision", lambda *args: "feb")
    monkeypatch.setattr(
        "bin.author_stats.compute_checkpoint",
        lambda *args: {
            "years": [],
            "totals": [1, 0, 0, 0],
            "identity_model": "legacy",
        },
    )
    update_history(tmp_path, "main", date(2026, 2, 1), output)
    assert json.loads(output.read_text()) == {
        "schema_version": 3,
        "checkpoints": [
            {
                "date": "2026-02-01",
                "revision": "feb",
                "years": [],
                "totals": [1, 0, 0, 0],
                "identity_model": "legacy",
            }
        ],
    }


def test_history_rejects_shallow_and_future_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr("bin.author_stats.git", lambda *args: "true")
    with pytest.raises(ValueError, match="full clone"):
        update_history(tmp_path, "main", date(2026, 2, 1), tmp_path / "history.json")
    monkeypatch.setattr("bin.author_stats.git", lambda *args: "false")
    with pytest.raises(ValueError, match="future"):
        update_history(tmp_path, "main", date(9999, 1, 1), tmp_path / "history.json")


def test_failed_checkpoint_preserves_previous_results(tmp_path, monkeypatch):
    output = tmp_path / "history.json"
    monkeypatch.setattr("bin.author_stats.git", lambda *args: "false")
    monkeypatch.setattr(
        "bin.author_stats.checkpoint_revision",
        lambda repo, ref, checkpoint: str(checkpoint),
    )

    def compute(repo, revision):
        if revision == "2026-03-01":
            raise RuntimeError("Unable to load historical data")
        return {"years": [], "totals": [0, 0, 0, 1], "identity_model": "legacy"}

    monkeypatch.setattr("bin.author_stats.compute_checkpoint", compute)
    with pytest.raises(RuntimeError, match="historical data"):
        update_history(tmp_path, "main", date(2026, 3, 1), output)
    assert [entry["date"] for entry in json.loads(output.read_text())["checkpoints"]] == [
        "2026-02-01"
    ]


def test_persisted_history_has_provenance_and_consistent_counts():
    repo = Path(__file__).resolve().parents[1]
    history = json.loads((repo / "hugo/assets/data/author-history.json").read_text())
    assert history["schema_version"] == 3
    checkpoints = history["checkpoints"]
    assert [entry["date"] for entry in checkpoints] == [
        str(month) for month in month_starts(date.fromisoformat(checkpoints[-1]["date"]))
    ]
    for checkpoint in checkpoints:
        assert len(checkpoint["revision"]) == 40
        assert checkpoint["identity_model"] in ("legacy", "verified")
        assert len(checkpoint["totals"]) == 4
        rows = {row["year"]: row for row in checkpoint["years"]}
        for row in rows.values():
            assert len(row["authorships"]) == len(row["authors"]) == 4
            assert all(
                0 <= unique <= occurrences
                for unique, occurrences in zip(row["authors"], row["authorships"])
            )
        assert rows[0]["authorships"] == [
            sum(row["authorships"][i] for year, row in rows.items() if 0 < year < 2020)
            for i in range(4)
        ]
    assert all(
        sum(entry["totals"][:2]) > 0
        for entry in checkpoints
        if entry["identity_model"] == "legacy"
    )
    assert all(
        entry["totals"][2] > 0 for entry in checkpoints if entry["date"] >= "2026-08-01"
    )
