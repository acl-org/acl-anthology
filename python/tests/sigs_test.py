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

from acl_anthology.sigs import SIGIndex, SIGMeeting, SIG

all_toy_sigs = ("sigfake1", "sigfake2")


def test_sig_defaults():
    sig = SIG("foo", None, "FOO", "Special Interest Group on Foobar")
    assert sig.id == "foo"
    assert sig.acronym == "FOO"
    assert sig.name == "Special Interest Group on Foobar"
    assert sig.url is None
    assert sig.venue_ids == ()
    assert sig.related_ids == []


def test_sigindex_create(anthology):
    index = anthology.sigs
    sig = index.create(id="sigfake", acronym="SIGFAKE", name="Fake Interest Group")
    assert "sigfake" in index
    assert index["sigfake"] is sig
    assert sig.acronym == "SIGFAKE"
    assert sig.name == "Fake Interest Group"
    assert len(sig.external_meetings) == 0


def test_sigindex_sigfake2(anthology):
    index = SIGIndex(anthology)
    sig = index.get("sigfake2")
    assert sig.id == "sigfake2"
    assert sig.acronym == "SIGFAKE2"
    assert (
        sig.name
        == "Special Interest Group on Fabricated Computational Semantics (SIGFAKE2)"
    )
    assert sig.url == "http://www.sigsem.org/"
    assert len(sig.external_meetings) == 3
    assert (
        SIGMeeting(
            "1899",
            "Proceedings of the First International Fabricated Workshop on Inference in Computational Semantics (IFCoS-1)",
            "https://example.org/ifcos-1",
        )
        in sig.external_meetings
    )
    assert len(sig.item_ids) == 1
    assert ("2022.natfake", "1", None) in sig.item_ids
    volume = next(sig.volumes())
    assert volume.full_id == "2022.natfake-1"
    assert sig.venue_ids == ("natfake",)
    venues = sig.venues()
    assert len(venues) == 1
    assert venues[0].id == "natfake"


def test_sig_get_meetings_by_year_fake():
    sig = SIG("fake", None, "FAKE", "Fake Interest Group")
    meeting = SIGMeeting(
        "1984",
        "Proceedings of the First Fakery Workshop",
        "http://xxx.yyy.zzz.nl/~fake/",
    )
    sig.external_meetings.append(meeting)
    assert sig.get_meetings_by_year() == {
        "1984": [meeting],
    }


def test_sig_get_meetings_by_year_sigfake2(anthology):
    index = SIGIndex(anthology)
    sig = index.get("sigfake2")

    assert sig.get_meetings_by_year() == {
        "1899": [
            SIGMeeting(
                "1899",
                "Proceedings of the Third International Fabricated Workshop on Computational Semantics (IFWCS-3)",
            ),
            SIGMeeting(
                "1899",
                "Proceedings of the First International Fabricated Workshop on Inference in Computational Semantics (IFCoS-1)",
                "https://example.org/ifcos-1",
            ),
        ],
        "1907": [
            SIGMeeting(
                "1907",
                "Proceedings of the Seventh International Fabricated Workshop on Computational Semantics (IFWCS-7)",
                "https://example.org/ifwcs-7",
            )
        ],
        "2022": ["2022.natfake-1"],
    }


def test_sig_with_nonexistent_venue(anthology):
    sig = SIG(
        "foo",
        anthology.sigs,
        "FOO",
        "Special Interest Group on Foobar",
        venue_ids=["doesntexist"],
    )
    with pytest.raises(KeyError):
        _ = sig.venues()


def test_sig_add_venue_updates_venue(anthology):
    sig = anthology.sigs["sigfake2"]
    natfake = anthology.venues["natfake"]
    humfake = anthology.venues["humfake"]
    assert sig in natfake.sigs()
    assert sig not in humfake.sigs()

    # Adding a venue to this SIG
    sig.venue_ids += ("humfake",)

    # Venues should be updated
    assert sig in natfake.sigs()
    assert sig in humfake.sigs()


def test_sig_remove_venue_updates_venue(anthology):
    sig = anthology.sigs["sigfake2"]
    natfake = anthology.venues["natfake"]
    assert sig in natfake.sigs()

    # Removing a venue from this SIG
    sig.venue_ids = ()

    # Venue should be updated
    assert sig not in natfake.sigs()


def test_sig_add_venue_raises(anthology):
    sig = anthology.sigs["sigfake1"]
    anthology.venues.load()
    with pytest.raises(ValueError):
        # Adding a venue to this SIG that doesn't exist
        sig.venue_ids += ("doesntexist",)


def test_sig_add_venue_by_id(anthology):
    sig = anthology.sigs["sigfake1"]
    humfake = anthology.venues["humfake"]
    assert "humfake" not in sig.venue_ids
    assert sig not in humfake.sigs()

    sig.add_venue("humfake")

    assert sig.venue_ids == ("humfake",)
    assert sig in humfake.sigs()


def test_sig_add_venue_by_object(anthology):
    sig = anthology.sigs["sigfake1"]
    humfake = anthology.venues["humfake"]
    assert "humfake" not in sig.venue_ids

    sig.add_venue(humfake)

    assert sig.venue_ids == ("humfake",)
    assert sig in humfake.sigs()


def test_sig_add_venue_already_present_is_noop(anthology):
    sig = anthology.sigs["sigfake2"]
    assert "natfake" in sig.venue_ids

    sig.add_venue("natfake")

    assert sig.venue_ids.count("natfake") == 1


def test_sig_add_venue_nonexistent_raises(anthology):
    sig = anthology.sigs["sigfake1"]
    anthology.venues.load()
    with pytest.raises(ValueError):
        sig.add_venue("doesntexist")


def test_sig_remove_venue_by_id(anthology):
    sig = anthology.sigs["sigfake2"]
    natfake = anthology.venues["natfake"]
    assert "natfake" in sig.venue_ids
    assert sig in natfake.sigs()

    sig.remove_venue("natfake")

    assert "natfake" not in sig.venue_ids
    assert sig not in natfake.sigs()


def test_sig_remove_venue_by_object(anthology):
    sig = anthology.sigs["sigfake2"]
    natfake = anthology.venues["natfake"]
    assert "natfake" in sig.venue_ids

    sig.remove_venue(natfake)

    assert "natfake" not in sig.venue_ids
    assert sig not in natfake.sigs()


def test_sig_remove_venue_not_present_is_noop(anthology):
    sig = anthology.sigs["sigfake1"]
    assert sig.venue_ids == ()

    sig.remove_venue("natfake")

    assert sig.venue_ids == ()


def test_sigindex_related(anthology):
    index = anthology.sigs
    assert index.related["sigfake1"] == {"sigfake2"}
    assert index.related["sigfake2"] == {"sigfake1"}


def test_sigindex_related_triggers_load(anthology):
    index = SIGIndex(anthology)
    assert not index.is_data_loaded
    assert index.related["sigfake1"] == {"sigfake2"}
    assert index.is_data_loaded


def test_sigindex_reset_clears_related(anthology):
    index = anthology.sigs
    assert index.related["sigfake1"] == {"sigfake2"}
    index.reset()
    assert len(index._related) == 0


def test_sigindex_roundtrip_data(anthology, tmp_path):
    index = anthology.sigs
    index.load()
    data_in = index.path
    data_out = tmp_path / "sigs.json"
    index.save(data_out)
    assert data_out.is_file()
    with (
        open(data_in, "r", encoding="utf-8") as f,
        open(data_out, "r", encoding="utf-8") as g,
    ):
        expected = f.read()
        out = g.read()
    assert out == expected
