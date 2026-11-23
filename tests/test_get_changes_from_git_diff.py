"""Preview-link generation must distinguish publication data from XML templates."""

from pathlib import Path

import pytest

from acl_anthology import Anthology
from bin.get_changes_from_git_diff import changed_links


def test_xml_templates_and_fixtures_are_not_publication_collections(monkeypatch):
    def unexpected_load(**kwargs):
        pytest.fail("Non-publication XML must not load or parse Anthology data")

    monkeypatch.setattr(Anthology, "from_within_repo", unexpected_load)
    assert (
        changed_links(
            [
                "hugo/layouts/sitemap.xml",
                "hugo/layouts/_default/rss.xml",
                "python/tests/data/anthology/xml/2022.facl.xml",
            ],
            "https://preview.example.org/test",
        )
        == []
    )


def test_changed_publications_use_the_library_and_configured_preview_url():
    source = Path(__file__).resolve().parents[1] / "python/tests/data/anthology"
    anthology = Anthology(source)
    url = "https://preview.example.org/test"
    assert changed_links(["data/xml/2022.natfake.xml\n"], url, anthology) == [
        f"[2022.natfake-1]({url}/volumes/2022.natfake-1)"
    ]


def test_deleted_collections_are_explicitly_reported(caplog):
    source = Path(__file__).resolve().parents[1] / "python/tests/data/anthology"
    assert (
        changed_links(
            ["data/xml/2026.absent.xml"], "https://preview.example.org", Anthology(source)
        )
        == []
    )
    assert "Changed collection 2026.absent is absent" in caplog.text


def test_faq_deduplication_info_links_and_limit():
    url = "https://preview.example.org"
    assert changed_links(
        ["hugo/content/faq/a.md", "hugo/content/faq/b.md", "hugo/content/info/ids.md"],
        url,
    ) == [f"[FAQ]({url}/faq)", f"[Info: ids]({url}/info/ids)"]
    result = changed_links([f"hugo/content/info/page{i}.md" for i in range(53)], url)
    assert len(result) == 51
    assert result[-1] == "(plus 3 more...)"
