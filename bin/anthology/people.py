# -*- coding: utf-8 -*-
#
# Copyright 2019 Marcel Bollmann <marcel@bollmann.me>
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

from collections import defaultdict, Counter
from slugify import slugify
import logging as log
import yaml
from .formatter import bibtex_encode
from .venues import VenueIndex

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class PersonName:
    first, last = "", ""

    def __init__(self, first, last):
        self.first = first.strip()
        self.last = last.strip()

    def from_element(person_element):
        first, last = "", ""
        for element in person_element:
            tag = element.tag
            # These are guaranteed to occur at most once by the schema
            if tag == "first":
                first = element.text or ""
            elif tag == "last":
                last = element.text or ""
        return PersonName(first, last)

    def from_repr(repr_):
        parts = repr_.split(" || ")
        if len(parts) > 1:
            first, last = parts[0], parts[1]
        else:
            first, last = "", parts[0]
        return PersonName(first, last)

    def from_dict(dict_):
        first = dict_.get("first", "")
        last = dict_["last"]
        return PersonName(first, last)

    @property
    def full(self):
        return "{} {}".format(self.first, self.last).strip()

    @property
    def id_(self):
        return repr(self)

    def as_bibtex(self):
        return bibtex_encode("{}, {}".format(self.last, self.first))

    def as_dict(self):
        return {"first": self.first, "last": self.last, "full": self.full}

    def __eq__(self, other):
        return (self.first == other.first) and (self.last == other.last)

    def __str__(self):
        return self.full

    def __repr__(self):
        if self.first:
            return "{} || {}".format(self.first, self.last)
        else:
            return self.last

    def __hash__(self):
        return hash(repr(self))


class PersonIndex:
    """Keeps an index of persons and their associated papers."""

    def __init__(self, srcdir=None):
        self.canonical = defaultdict(list)  # maps canonical names to variants
        self.variants = {}  # maps variant names to canonical names
        self._all_slugs = set([""])
        self.slugs = {}  # maps names to unique slugs
        self.coauthors = defaultdict(Counter)  # maps names to co-author names
        self.papers = defaultdict(lambda: defaultdict(list))
        if srcdir is not None:
            self.load_variant_list(srcdir)

    def load_variant_list(self, directory):
        with open("{}/yaml/name_variants.yaml".format(directory), "r") as f:
            name_list = yaml.load(f, Loader=Loader)
            for entry in name_list:
                try:
                    canonical = entry["canonical"]
                    variants = entry["variants"]
                except (KeyError, TypeError):
                    log.error("Couldn't parse name variant entry: {}".format(entry))
                    continue
                canonical = PersonName.from_dict(canonical)
                _ = self.papers[canonical] # insert empty entry for canonical if not present
                for variant in variants:
                    variant = PersonName.from_dict(variant)
                    _ = self.papers[variant] # insert empty entry if not present
                    if variant in self.variants:
                        log.error(
                            "Tried to add '{}' as variant of '{}', but is already a variant of '{}'".format(
                                repr(variant),
                                repr(canonical),
                                repr(self.variants[variant]),
                            )
                        )
                        continue
                    self.variants[variant] = canonical
                    self.canonical[canonical].append(variant)

    def register(self, paper):
        """Register all names associated with the given paper."""
        from .papers import Paper

        assert isinstance(paper, Paper), "Expected Paper, got {} ({})".format(
            type(paper), repr(paper)
        )
        for role in ("author", "editor"):
            for name in paper.get(role, []):
                # Register paper
                self.papers[name][role].append(paper.full_id)
                # Make sure canonical names are prioritized for slugs
                if self.is_canonical(name):
                    self.get_slug(name)
                # Register co-author(s)
                for author in paper.get(role):
                    if author != name:
                        self.coauthors[name][author] += 1

    def names(self):
        return self.papers.keys()

    def __len__(self):
        return len(self.papers)

    def is_canonical(self, name):
        return name not in self.variants

    def has_variants(self, name):
        return name in self.canonical

    def get_canonical_variant(self, name):
        """Maps a name to its canonical variant."""
        return self.variants.get(name, name)

    def get_all_variants(self, name):
        """Return a list of all variants for a given name.

        Includes the supplied name itself.
        """
        if not self.is_canonical(name):
            name = self.get_canonical_variant(name)
        return self.canonical[name] + [name]

    def get_registered_variants(self, name):
        """Return a list of variants for a given name that are actually
        associated with papers.

        Will only return true variants, not including the canonical name.
        """
        if not self.is_canonical(name):
            name = self.get_canonical_variant(name)
        return [n for n in self.canonical[name] if n in self.papers]

    def get_slug(self, name):
        if name in self.slugs:
            return self.slugs[name]
        slug, i = slugify(repr(name)), 0
        while slug in self._all_slugs:
            i += 1
            slug = "{}{}".format(slugify(repr(name)), i)
        self._all_slugs.add(slug)
        self.slugs[name] = slug
        return slug

    def get_papers(self, name, role=None, include_variants=False):
        if include_variants:
            return [
                p
                for n in self.get_all_variants(name)
                for p in self.get_papers(n, role=role)
            ]
        if role is None:
            return [p for p_list in self.papers[name].values() for p in p_list]
        return self.papers[name][role]

    def get_coauthors(self, name, include_variants=False):
        if include_variants:
            return [
                p for n in self.get_all_variants(name) for p in self.get_coauthors(n)
            ]
        return self.coauthors[name].items()

    def get_venues(self, vidx: VenueIndex, name, include_variants=False):
        """Get a list of venues a person has published in, with counts."""
        venues = Counter()
        if include_variants:
            for n in self.get_all_variants(name):
                venues.update(self.get_venues(vidx, n))
        else:
            for paper in self.get_papers(name):
                for venue in vidx.get_associated_venues(paper):
                    venues[venue] += 1
        return venues
