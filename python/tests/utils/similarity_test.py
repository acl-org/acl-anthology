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


def test_subset_of_never_merged_item_is_singleton():
    groups = SimilarityGroups()
    assert groups.subset("unknown") == {"unknown"}
    # A never-merged item isn't actually tracked -- there's nothing to
    # distinguish it from one that's merely unknown.
    assert "unknown" not in groups
    assert len(groups) == 0


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


def test_merge_two_existing_groups():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.merge("c", "d")
    groups.merge("b", "c")
    assert groups.subset("a") == {"a", "b", "c", "d"}
    assert groups.subset("d") == {"a", "b", "c", "d"}


def test_merge_two_existing_groups_extends_the_larger_one():
    # Regression test for the swap branch: when merging two already-existing
    # groups of different sizes, the *smaller* one must be absorbed into the
    # larger one, regardless of which merge() argument it's passed as. The
    # resulting subset() is the same either way (set union is symmetric), so
    # this has to check object identity of the surviving backing set in
    # _groups directly to actually exercise what the swap is for.
    groups = SimilarityGroups()
    groups.merge("a", "b")  # {a, b}, size 2
    groups.merge("c", "d")
    groups.merge("d", "e")  # {c, d, e}, size 3
    larger_group = groups._groups["c"]
    groups.merge("a", "c")  # "a"'s (smaller) group must be absorbed into "c"'s
    assert groups.subset("a") == {"a", "b", "c", "d", "e"}
    assert groups.subset("e") == {"a", "b", "c", "d", "e"}
    assert groups._groups["a"] is larger_group
    assert groups._groups["b"] is larger_group
    assert groups._groups["c"] is larger_group


def test_merge_never_merged_item_into_existing_group():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.merge("a", "c")  # "c" has never been seen before
    assert groups.subset("c") == {"a", "b", "c"}


def test_merge_existing_group_with_never_merged_item():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.merge("c", "a")  # "c" has never been seen before
    assert groups.subset("c") == {"a", "b", "c"}


def test_connected_true_for_item_with_itself():
    # Reflexive even for an item that was never merged with anything, same
    # as subset(item) always including item itself.
    groups = SimilarityGroups()
    assert groups.connected("unknown", "unknown")
    groups.merge("a", "b")
    assert groups.connected("a", "a")


def test_connected_false_for_different_groups():
    groups = SimilarityGroups()
    groups.merge("a", "x")
    groups.merge("b", "y")
    assert not groups.connected("a", "b")


def test_connected_false_for_unrelated_never_merged_items():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    assert not groups.connected("a", "unknown")
    assert not groups.connected("unknown", "a")


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


def test_remove_never_merged_item_is_noop():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.remove("unknown")
    assert groups.subset("a") == {"a", "b"}


def test_remove_leaves_singleton_behind():
    # The remaining member of a dissolved pair keeps a real (now
    # one-element) group rather than reverting to "never merged" -- this is
    # a one-off cost on removal, not on the hot construction path.
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.remove("b")
    assert "a" in groups
    assert groups.subset("a") == {"a"}


def test_len_and_iter():
    groups = SimilarityGroups()
    groups.merge("a", "b")
    groups.merge("c", "d")
    assert len(groups) == 4
    assert set(groups) == {"a", "b", "c", "d"}
