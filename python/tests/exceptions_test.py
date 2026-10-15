# Copyright 2023-2026 Marcel Bollmann <marcel@bollmann.me>
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

from typing import Any, cast
import pytest
import warnings

from acl_anthology.exceptions import (
    MaintainerWarning,
    NameSpecResolutionWarning,
    TeXParserWarning,
    suppress_maintainer_warnings,
)


def tex_warning(message: str = "tex problem") -> TeXParserWarning:
    return TeXParserWarning(cast(Any, None), message)


def namespec_warning(message: str = "namespec problem") -> NameSpecResolutionWarning:
    return NameSpecResolutionWarning(cast(Any, None), message)


@pytest.fixture(autouse=True)
def restore_warning_filters():
    # suppress_maintainer_warnings() mutates the global warnings filter list;
    # make sure tests don't leak state into each other.
    with warnings.catch_warnings():
        warnings.resetwarnings()
        yield


def test_suppress_maintainer_warnings_all():
    suppress_maintainer_warnings(True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(tex_warning())
        warnings.warn(namespec_warning())
    assert len(caught) == 0


def test_suppress_maintainer_warnings_enable_all():
    suppress_maintainer_warnings(True)
    suppress_maintainer_warnings(False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(tex_warning())
        warnings.warn(namespec_warning())
    assert len(caught) == 2


def test_suppress_maintainer_warnings_selected_by_class():
    suppress_maintainer_warnings([TeXParserWarning])
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(tex_warning())
    assert len(caught) == 0
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(namespec_warning())
    assert len(caught) == 1


def test_suppress_maintainer_warnings_selected_by_name():
    suppress_maintainer_warnings(["TeXParserWarning"])
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(tex_warning())
    assert len(caught) == 0
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(namespec_warning())
    assert len(caught) == 1


def test_suppress_maintainer_warnings_empty_list_enables_all():
    suppress_maintainer_warnings(True)
    suppress_maintainer_warnings([])
    with warnings.catch_warnings(record=True) as caught:
        warnings.warn(tex_warning())
        warnings.warn(namespec_warning())
    assert len(caught) == 2


def test_suppress_maintainer_warnings_unknown_name_raises():
    with pytest.raises(ValueError, match="not a known MaintainerWarning"):
        suppress_maintainer_warnings(["NotARealWarning"])


def test_suppress_maintainer_warnings_non_maintainer_warning_name_raises():
    # AnthologyException exists in the module's globals, but isn't a MaintainerWarning.
    with pytest.raises(ValueError, match="not a known MaintainerWarning"):
        suppress_maintainer_warnings(["AnthologyException"])


def test_suppress_maintainer_warnings_non_maintainer_warning_class_raises():
    with pytest.raises(ValueError, match="cannot be interpreted as a MaintainerWarning"):
        suppress_maintainer_warnings(cast(Any, [UserWarning]))


def test_suppress_maintainer_warnings_invalid_entry_type_raises():
    with pytest.raises(ValueError, match="cannot be interpreted as a MaintainerWarning"):
        suppress_maintainer_warnings(cast(Any, [123]))


def test_base_class_is_user_warning():
    assert issubclass(MaintainerWarning, UserWarning)
