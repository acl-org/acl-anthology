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

from pathlib import Path
from acl_anthology.sigs import SIGIndex, SIGMeeting, SIG


def test_sig_defaults():
    sig = SIG(None, "foo", "FOO", "Special Interest Group on Foobar", Path("foo.yaml"))
    assert sig.id == "foo"
    assert sig.acronym == "FOO"
    assert sig.name == "Special Interest Group on Foobar"
    assert sig.path.name == "foo.yaml"
    assert sig.url is None


def test_sig_get_meetings_by_year():
    sig = SIG(None, "fake", "FAKE", "Fake Interest Group", Path("fake.yaml"))
    meeting = SIGMeeting(
        "1984",
        "Proceedings of the First Fakery Workshop",
        "http://xxx.yyy.zzz.nl/~fake/",
    )
    sig.meetings.append(meeting)
    sig.meetings.append("2004.fake-1")
    assert sig.get_meetings_by_year() == {
        "1984": [meeting],
        "2004": ["2004.fake-1"],
    }


def test_sig_save(tmp_path):
    path = tmp_path / "foo.yaml"
    sig = SIG(None, "foo", "FOO", "Special Interest Group on Foobar", path)
    sig.save()
    assert path.is_file()
    with open(path, "r") as f:
        out = f.read()
    expected = """Name: Special Interest Group on Foobar
ShortName: FOO
"""
    assert out == expected


def test_sig_roundtrip_yaml(anthology_stub, tmp_path):
    yaml_in = anthology_stub.datadir / "yaml" / "sigs" / "sigsem.yaml"
    sig = SIG.load_from_yaml(None, yaml_in)
    yaml_out = tmp_path / "sigsem.yaml"
    sig.save(yaml_out)
    assert yaml_out.is_file()
    with open(yaml_in, "r") as f, open(yaml_out, "r") as g:
        # Comments will unfortunately be deleted upon saving ...
        expected = "\n".join(line.split("#")[0].rstrip() for line in f.readlines()) + "\n"
        out = g.read()
    assert out == expected


def test_sigindex_sigsem(anthology):
    index = SIGIndex(anthology)
    sig = index.get("sigsem")
    assert sig.id == "sigsem"
    assert sig.acronym == "SIGSEM"
    assert sig.name == "Special Interest Group on Computational Semantics (SIGSEM)"
    assert sig.url == "http://www.sigsem.org/"
    assert len(sig.meetings) == 4
    assert "2022.naloma-1" in sig.meetings
    assert (
        SIGMeeting(
            "1999",
            "Proceedings of the First International Workshop on Inference in Computational Semantics (ICoS-1)",
            "http://turing.wins.uva.nl/~mdr/ICoS/",
        )
        in sig.meetings
    )
    volume = next(sig.volumes())
    assert volume.full_id == "2022.naloma-1"
