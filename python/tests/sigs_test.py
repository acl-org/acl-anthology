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

all_toy_sigs = ("sigdat", "sigsem")


def test_sig_defaults():
    sig = SIG("foo", None, "FOO", "Special Interest Group on Foobar")
    assert sig.id == "foo"
    assert sig.acronym == "FOO"
    assert sig.name == "Special Interest Group on Foobar"
    assert sig.url is None


def test_sigindex_sigsem(anthology):
    index = SIGIndex(anthology)
    sig = index.get("sigsem")
    assert sig.id == "sigsem"
    assert sig.acronym == "SIGSEM"
    assert sig.name == "Special Interest Group on Computational Semantics (SIGSEM)"
    assert sig.url == "http://www.sigsem.org/"
    assert len(sig.external_meetings) == 3
    assert (
        SIGMeeting(
            "1999",
            "Proceedings of the First International Workshop on Inference in Computational Semantics (ICoS-1)",
            "http://turing.wins.uva.nl/~mdr/ICoS/",
        )
        in sig.external_meetings
    )
    assert len(sig.item_ids) == 1
    assert ("2022.naloma", "1", None) in sig.item_ids
    volume = next(sig.volumes())
    assert volume.full_id == "2022.naloma-1"


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


def test_sig_get_meetings_by_year_sigsem(anthology):
    index = SIGIndex(anthology)
    sig = index.get("sigsem")

    assert sig.get_meetings_by_year() == {
        "1999": [
            SIGMeeting(
                "1999",
                "Proceedings of the Third International Workshop on Computational Semantics (IWCS-3)",
            ),
            SIGMeeting(
                "1999",
                "Proceedings of the First International Workshop on Inference in Computational Semantics (ICoS-1)",
                "http://turing.wins.uva.nl/~mdr/ICoS/",
            ),
        ],
        "2007": [
            SIGMeeting(
                "2007",
                "Proceedings of the Seventh International Workshop on Computational Semantics (IWCS-7)",
                "http://let.uvt.nl/research/ti/sigsem/iwcs/iwcs7/",
            )
        ],
        "2022": ["2022.naloma-1"],
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
