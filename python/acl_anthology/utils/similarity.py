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

"""A disjoint-set-like structure for tracking groups of similar items."""

from __future__ import annotations

from typing import Iterator


class SimilarityGroups:
    """Tracks groups of items (e.g. person IDs) considered "similar" to each other.

    Functionally a union-find: [`merge()`][acl_anthology.utils.similarity.SimilarityGroups.merge] merges the groups of two items, and [`subset()`][acl_anthology.utils.similarity.SimilarityGroups.subset] returns all items grouped with a given one.  For performance reasons, there is no `add()` operation -- all items are considered to exist and be grouped with only themselves by default.
    """

    __slots__ = ("_groups",)

    def __init__(self) -> None:
        self._groups: dict[str, set[str]] = {}

    def __contains__(self, item: str) -> bool:
        return item in self._groups

    def __iter__(self) -> Iterator[str]:
        return iter(self._groups)

    def __len__(self) -> int:
        return len(self._groups)

    def merge(self, a: str, b: str) -> None:
        """Merge the groups containing `a` and `b` into a single group.

        Either or both of `a`, `b` may be items that have never been seen by this structure before.

        Parameters:
            a: An item.
            b: Another item.
        """
        group_a = self._groups.get(a)
        group_b = self._groups.get(b)
        if group_a is not None and group_a is group_b:
            return  # already in the same group

        # Each grouped item maps to a (shared) `set` object representing its
        # group.  We always extends the larger of the two sets with the smaller
        # one and repoint the smaller set's members to it; this is the standard
        # "weighted union" trick and costs an amortized O(log n) pointer updates
        # per item across all merges, the same complexity class as a tree-based
        # union-find with union-by-size.
        if group_a is None and group_b is None:
            new_group = {a, b}
            self._groups[a] = new_group
            self._groups[b] = new_group
        elif group_b is None:
            assert group_a is not None
            group_a.add(b)
            self._groups[b] = group_a
        elif group_a is None:
            group_b.add(a)
            self._groups[a] = group_b
        else:
            if len(group_a) < len(group_b):
                group_a, group_b = group_b, group_a
            group_a |= group_b
            for item in group_b:
                self._groups[item] = group_a

    def connected(self, a: str, b: str) -> bool:
        """Return whether `a` and `b` are currently in the same group.

        Every item is trivially connected to itself, whether or not it has ever been merged with anything (consistent with [`subset()`][acl_anthology.utils.similarity.SimilarityGroups.subset] always including `item` itself).
        """
        group_a = self._groups.get(a)
        if group_a is None:
            return a == b
        return group_a is self._groups.get(b)

    def subset(self, item: str) -> set[str]:
        """Return the group containing `item`.

        Parameters:
            item: An item.

        Returns:
            A new `set` containing every item grouped with `item`, including `item` itself. If `item` was never merged with anything, returns `{item}`.
        """
        group = self._groups.get(item)
        if group is None:
            return {item}
        return set(group)

    def remove(self, item: str) -> None:
        """Remove `item` from its group, and from this structure entirely.

        Does nothing if `item` was never merged with anything.

        Parameters:
            item: An item.
        """
        group = self._groups.pop(item, None)
        if group is not None:
            group.discard(item)
