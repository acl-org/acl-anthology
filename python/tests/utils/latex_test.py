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
from acl_anthology.people.name import Name, NameSpecification
from acl_anthology.text import MarkupText
from acl_anthology.utils import latex

test_cases_latex = (
    ('"This is a quotation."', "``This is a quotation.''"),
    ('This is a "quotation".', "This is a ``quotation''."),
    ('Can you "please" "convert" this?', "Can you ``please'' ``convert'' this?"),
    ('My name is "陳大文".', "My name is ``陳大文''."),
)


@pytest.mark.parametrize("inp, out", test_cases_latex)
def test_latex_convert_quotes(inp, out):
    assert latex.latex_convert_quotes(inp) == out


def test_namespecs_to_bibtex():
    ns1 = NameSpecification(Name("Tai Man", "Chan"))
    ns2 = NameSpecification(Name("John", "Doé"))
    assert latex.namespecs_to_bibtex([]) == ""
    assert latex.namespecs_to_bibtex([ns1]) == "Chan, Tai Man"
    assert (
        latex.namespecs_to_bibtex([ns1, ns2]) == "Chan, Tai Man  and\n      Do\\'e, John"
    )


def test_has_unbalanced_braces():
    assert not latex.has_unbalanced_braces("asdf")
    assert not latex.has_unbalanced_braces("{}")
    assert not latex.has_unbalanced_braces("{foo} {bar {baz}}")
    assert latex.has_unbalanced_braces("}{")
    assert latex.has_unbalanced_braces("{}}")
    assert latex.has_unbalanced_braces("foo {bar {baz}")


def test_bibtex_convert_month():
    assert latex.bibtex_convert_month("January") == "jan"
    assert latex.bibtex_convert_month("SEPTEMBER") == "sep"
    assert latex.bibtex_convert_month("mar") == "mar"
    assert latex.bibtex_convert_month("aug") == "aug"
    assert latex.bibtex_convert_month("September--November") == 'sep # "--" # nov'
    assert latex.bibtex_convert_month("December 3") == 'dec # " 3"'
    assert latex.bibtex_convert_month("UNK") == '"unk"'


def test_make_bibtex_entry():
    bibtype, bibkey = "inproceedings", "my-entry"
    fields = [
        ("author", [NameSpecification(Name("John", "Doé"))]),
        ("editor", []),
        ("title", MarkupText.from_string("Thé Papér")),
        ("booktitle", MarkupText.from_string('My "Conference"')),
        ("address", '"Montréal"'),
        ("doi", "10.000.a_b_c"),
        ("publisher", ""),
        ("month", "February"),
        ("note", None),
        ("pages", "1–7"),
    ]
    expected = """@inproceedings{my-entry,
    author = "Do\\'e, John",
    title = "Th\\'e Pap\\'er",
    booktitle = "My ``Conference''",
    address = {"Montr\\'eal"},
    doi = "10.000.a_b_c",
    month = feb,
    pages = "1--7"
}"""
    assert latex.make_bibtex_entry(bibtype, bibkey, fields) == expected


def test_make_bibtex_entry_malformed():
    with pytest.raises(TypeError):
        latex.make_bibtex_entry("", "", [("author", Name("John", "Doé"))])
    with pytest.raises(TypeError):
        latex.make_bibtex_entry("", "", [("author", [Name("John", "Doé")])])
    with pytest.raises(ValueError):
        latex.make_bibtex_entry("", "", [("title", "}{")])
