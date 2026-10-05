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

from typing import Iterator, Optional


class SimilarityGroups:
    """Tracks groups of items (person IDs) considered "similar" to each other.

    Functionally a union-find: [`add()`][acl_anthology.utils.similarity.SimilarityGroups.add] registers a new singleton group, [`merge()`][acl_anthology.utils.similarity.SimilarityGroups.merge] merges the groups of two items, and [`subset()`][acl_anthology.utils.similarity.SimilarityGroups.subset] returns all items grouped with a given one.

    Unlike `scipy.cluster.hierarchy.DisjointSet` (this class's predecessor), items can also be removed again via [`remove()`][acl_anthology.utils.similarity.SimilarityGroups.remove]. This is needed here because groups change dynamically as Anthology data is edited (e.g. persons being merged, renamed, or deleted), rather than being computed once from static input.

    Internally, each grouped item maps to the (shared) `set` object representing its group, rather than to a parent pointer in a tree. `merge()` always extends the larger of the two sets with the smaller one and repoints the smaller set's members to it; this is the standard "weighted union" trick and costs an amortized O(log n) pointer updates per item across all merges, the same complexity class as a tree-based union-find with union-by-size. The payoff is that `remove()` becomes a plain, O(1) `set.discard()` -- there is no parent chain that would need repairing.

    An item that was only ever [`add()`][acl_anthology.utils.similarity.SimilarityGroups.add]ed, and never merged with anything, maps to `None` instead of an actual `{item}` set. This matters in practice: almost all items registered here are never merged with anything (merges are the exception, not the rule), so allocating a real `set` per item up front would mean allocating one object per item for no reason -- which, measured against the real Anthology corpus, was enough new-object churn to repeatedly trigger full (generation-2) garbage collection passes over the entire, already-loaded `Anthology` object graph, dominating this structure's own construction cost many times over. Deferring the allocation to the first actual merge avoids that entirely for the common case.
    """

    __slots__ = ("_groups",)

    def __init__(self) -> None:
        self._groups: dict[str, Optional[set[str]]] = {}

    def __contains__(self, item: str) -> bool:
        return item in self._groups

    def __iter__(self) -> Iterator[str]:
        return iter(self._groups)

    def __len__(self) -> int:
        return len(self._groups)

    def add(self, item: str) -> None:
        """Register a new item as its own, singleton group.

        Does nothing if the item is already registered.
        """
        self._groups.setdefault(item, None)

    def merge(self, a: str, b: str) -> None:
        """Merge the groups containing `a` and `b` into a single group.

        Registers `a` and/or `b` first via [`add()`][acl_anthology.utils.similarity.SimilarityGroups.add] if either isn't already registered.

        Parameters:
            a: An item.
            b: Another item.
        """
        self.add(a)
        self.add(b)
        group_a, group_b = self._groups[a], self._groups[b]
        if group_a is not None and group_a is group_b:
            return  # already in the same group

        if group_a is None and group_b is None:
            new_group = {a, b}
            self._groups[a] = new_group
            self._groups[b] = new_group
        elif group_a is None:
            assert group_b is not None
            group_b.add(a)
            self._groups[a] = group_b
        elif group_b is None:
            group_a.add(b)
            self._groups[b] = group_a
        else:
            if len(group_a) < len(group_b):
                group_a, group_b = group_b, group_a
            group_a |= group_b
            for item in group_b:
                self._groups[item] = group_a

    def connected(self, a: str, b: str) -> bool:
        """Return whether `a` and `b` are currently in the same group.

        Returns:
            False if either item isn't registered.
        """
        if a not in self._groups or b not in self._groups:
            return False
        group_a = self._groups[a]
        if group_a is None:
            return a == b
        return group_a is self._groups[b]

    def subset(self, item: str) -> set[str]:
        """Return the group containing `item`.

        Parameters:
            item: An item.

        Returns:
            A new `set` containing every item grouped with `item`, including `item` itself. If `item` isn't registered, or isn't grouped with anything, returns `{item}`.
        """
        group = self._groups.get(item)
        if group is None:
            return {item}
        return set(group)

    def remove(self, item: str) -> None:
        """Remove `item` from its group, and from this structure entirely.

        Unlike `scipy.cluster.hierarchy.DisjointSet`, this is supported, and takes constant time. Does nothing if `item` isn't registered.

        Parameters:
            item: An item.
        """
        if item not in self._groups:
            return
        group = self._groups.pop(item)
        if group is not None:
            group.discard(item)
