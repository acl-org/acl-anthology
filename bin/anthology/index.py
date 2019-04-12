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

import logging as log
import re
import yaml
from collections import defaultdict, Counter
from slugify import slugify
from stop_words import get_stop_words
from .formatter import bibtex_encode
from .people import PersonName
from .venues import VenueIndex

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


BIBKEY_MAX_NAMES = 2


def load_stopwords(language):
    return [t for w in get_stop_words(language) for t in slugify(w).split("-")]


class AnthologyIndex:
    """Keeps an index of persons, their associated papers, paper bibliography
    keys, etc.."""

    def __init__(self, srcdir=None):
        self.bibkeys = set()
        self.stopwords = load_stopwords("en")
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
                _ = self.papers[
                    canonical
                ]  # insert empty entry for canonical if not present
                for variant in variants:
                    variant = PersonName.from_dict(variant)
                    _ = self.papers[variant]  # insert empty entry if not present
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

    def create_bibkey(self, paper):
        """Create a unique bibliography key for the given paper."""
        names = paper.get("author")
        if not names:
            names = paper.get("editor", [])
        if names:
            if len(names) > BIBKEY_MAX_NAMES:
                bibnames = "{}-etal".format(slugify(names[0].last))
            else:
                bibnames = "-".join(slugify(n.last) for n in names)
        else:
            bibnames = "nn"
        title = [
            w
            for w in slugify(paper.get_title("plain")).split("-")
            if w not in self.stopwords
        ]
        bibkey = "{}-{}-{}".format(bibnames, str(paper.get("year")), title.pop(0))
        while bibkey in self.bibkeys:  # guarantee uniqueness
            if title:
                bibkey += "-{}".format(title.pop(0))
            else:
                match = re.search(r"-([0-9]+)$", bibkey)
                if match is not None:
                    num = int(match.group(1)) + 1
                    bibkey = bibkey[:-len(match.group(1))] + "{}".format(num)
                else:
                    bibkey += "-2"
                log.warn("New bibkey: {}".format(bibkey))
        self.bibkeys.add(bibkey)
        return bibkey

    def register(self, paper):
        """Register all names associated with the given paper."""
        from .papers import Paper

        assert isinstance(paper, Paper), "Expected Paper, got {} ({})".format(
            type(paper), repr(paper)
        )
        paper.bibkey = self.create_bibkey(paper)
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
