# Copyright 2023 Marcel Bollmann <marcel@bollmann.me>
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
