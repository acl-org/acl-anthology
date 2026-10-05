# Copyright 2026 Marcel Bollmann <marcel@bollmann.me>
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

from acl_anthology.utils.similarity import SimilarityGroups


def test_add_registers_singleton():
    groups = SimilarityGroups()
    groups.add("a")
    assert "a" in groups
    assert groups.subset("a") == {"a"}
    # Adding twice is a no-op
    groups.add("a")
    assert groups.subset("a") == {"a"}


def test_subset_of_unknown_item_is_singleton():
    groups = SimilarityGroups()
    assert groups.subset("unknown") == {"unknown"}
    assert "unknown" not in groups


def test_merge_combines_groups():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    assert groups.subset("a") == {"a", "b"}
    assert groups.subset("b") == {"a", "b"}
    assert groups.connected("a", "b")


def test_merge_is_transitive():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.merge("b", "c")
    groups.merge("d", "e")
    groups.merge("c", "d")
    assert groups.subset("a") == {"a", "b", "c", "d", "e"}
    assert groups.subset("e") == {"a", "b", "c", "d", "e"}
    assert groups.connected("a", "e")


def test_merge_same_group_is_noop():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.merge("a", "b")
    groups.merge("b", "a")
    assert groups.subset("a") == {"a", "b"}


def test_connected_false_for_different_groups():
    groups = SimilarityGroups()
    groups.add("a")
    groups.add("b")
    assert not groups.connected("a", "b")


def test_connected_true_for_item_with_itself():
    # Regression test: a lone, never-merged item is represented internally
    # by a `None` sentinel rather than an actual {item} set (see
    # SimilarityGroups' docstring), so connected(a, a) must special-case
    # this rather than comparing `None is None`.
    groups = SimilarityGroups()
    groups.add("a")
    assert groups.connected("a", "a")


def test_merge_singleton_with_singleton():
    groups = SimilarityGroups()
    groups.add("a")
    groups.add("b")
    groups.merge("a", "b")
    assert groups.subset("a") == {"a", "b"}
    assert groups.subset("b") == {"a", "b"}


def test_merge_singleton_into_existing_group():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.add("c")
    groups.merge("a", "c")
    assert groups.subset("c") == {"a", "b", "c"}


def test_merge_existing_group_with_singleton():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.add("c")
    groups.merge("c", "a")
    assert groups.subset("c") == {"a", "b", "c"}


def test_merge_two_existing_groups():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.merge("c", "d")
    groups.merge("b", "c")
    assert groups.subset("a") == {"a", "b", "c", "d"}
    assert groups.subset("d") == {"a", "b", "c", "d"}


def test_connected_false_for_unknown_items():
    groups = SimilarityGroups()
    groups.add("a")
    assert not groups.connected("a", "unknown")
    assert not groups.connected("unknown", "a")
    assert not groups.connected("unknown", "unknown")


def test_subset_returns_independent_copy():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    subset = groups.subset("a")
    subset.add("c")
    assert groups.subset("a") == {"a", "b"}


def test_remove_drops_item_from_group_and_index():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.merge("b", "c")
    groups.remove("b")
    assert "b" not in groups
    assert groups.subset("a") == {"a", "c"}
    assert groups.subset("c") == {"a", "c"}
    # Removed item resolves back to its own singleton
    assert groups.subset("b") == {"b"}


def test_remove_unknown_item_is_noop():
    groups = SimilarityGroups()
    groups.add("a")
    groups.remove("unknown")
    assert groups.subset("a") == {"a"}


def test_remove_last_item_in_group():
    groups = SimilarityGroups()
    groups.add("a")
    groups.remove("a")
    assert "a" not in groups
    assert len(groups) == 0


def test_len_and_iter():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.add("c")
    assert len(groups) == 3
    assert set(groups) == {"a", "b", "c"}
