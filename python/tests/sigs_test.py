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

from acl_anthology.sigs import SIGIndex, SIGMeeting, SIG

all_toy_sigs = ("sigfake1", "sigfake2")


def test_sig_defaults():
    sig = SIG("foo", None, "FOO", "Special Interest Group on Foobar")
    assert sig.id == "foo"
    assert sig.acronym == "FOO"
    assert sig.name == "Special Interest Group on Foobar"
    assert sig.url is None


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
