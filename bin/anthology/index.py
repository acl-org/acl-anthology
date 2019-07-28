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

from typing import List

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

    def __init__(self, parent, srcdir=None):
        self._parent = parent
        self.bibkeys = set()
        self.stopwords = load_stopwords("en")
        self.id_to_canonical = {}  # maps ids to canonical names
        self.id_to_used = defaultdict(set)  # maps ids to all names actually used
        self.name_to_ids = defaultdict(list)  # maps canonical/variant names to ids
        self.coauthors = defaultdict(Counter)  # maps ids to co-author ids
        self.comments = {}  # maps ids to comments (used for distinguishing authors with same name)
        self.similar = defaultdict(set)
        self.id_to_papers = defaultdict(lambda: defaultdict(list))  # id -> role -> papers
        self.name_to_papers = defaultdict(lambda: defaultdict(list))  # name -> (explicit id?) -> papers; used only for error checking
        if srcdir is not None:
            self.load_variant_list(srcdir)

    def load_variant_list(self, directory):
        with open("{}/yaml/name_variants.yaml".format(directory), "r") as f:
            name_list = yaml.load(f, Loader=Loader)

            # Reserve ids for people with explicit ids in variant list
            for entry in name_list:
                if "id" in entry:
                    id_ = entry["id"]
                    canonical = entry["canonical"]
                    canonical = PersonName.from_dict(canonical)
                    self.set_canonical_name(id_, canonical)
            # Automatically add people with same canonical name to similar list
            for name, ids in self.name_to_ids.items():
                if len(ids) > 1:
                    for id1 in ids:
                        for id2 in ids:
                            if id2 != id1:
                                self.similar[id1].add(id2)
            for entry in name_list:
                try:
                    canonical = entry["canonical"]
                    variants = entry.get("variants", [])
                    id_ = entry.get("id", None)
                except (KeyError, TypeError):
                    log.error("Couldn't parse name variant entry: {}".format(entry))
                    continue
                canonical = PersonName.from_dict(canonical)
                if id_ is None:
                    if canonical in self.name_to_ids:
                        log.error(
                            "Canonical name '{}' is ambiguous but doesn't have an id; please add one". format(canonical))
                    id_ = self.fresh_id(canonical)
                    self.set_canonical_name(id_, canonical)
                for variant in variants:
                    variant = PersonName.from_dict(variant)
                    if variant in self.name_to_ids:
                        log.error(
                            "Tried to add '{}' as variant of '{}', but is already a variant of '{}'".format(
                                repr(variant),
                                repr(canonical),
                                repr(self.id_to_canonical[
                                    self.name_to_ids[variant][0]
                                ]),
                            )
                        )
                        continue
                    self.add_variant_name(id_, variant)
                if "comment" in entry:
                    self.comments[id_] = entry["comment"]
                if "similar" in entry:
                    self.similar[id_].update(entry["similar"])

    def _is_stopword(self, word, paper):
        """Determines if a given word should be considered a stopword for
        the purpose of generating BibTeX keys."""
        if word in self.stopwords:
            return True
        if paper.is_volume:
            # Some simple heuristics to exclude probably uninformative words
            # -- these are not perfect
            if word in (
                "proceedings",
                "volume",
                "conference",
                "workshop",
                "annual",
                "meeting",
                "computational",
            ):
                return True
            elif (
                re.match(r"[0-9]+(st|nd|rd|th)", word)
                or word.endswith("ieth")
                or word.endswith("enth")
                or word
                in (
                    "first",
                    "second",
                    "third",
                    "fourth",
                    "fifth",
                    "sixth",
                    "eighth",
                    "ninth",
                    "twelfth",
                )
            ):
                return True
        return False

    def create_bibkey(self, paper):
        """Create a unique bibliography key for the given paper."""
        if paper.is_volume:
            # Proceedings volumes use venue acronym instead of authors/editors
            bibnames = slugify(self._parent.venues.get_by_letter(paper.full_id[0]))
        else:
            # Regular papers use author/editor names
            names = paper.get("author")
            if not names:
                names = paper.get("editor", [])
            if names:
                if len(names) > BIBKEY_MAX_NAMES:
                    bibnames = "{}-etal".format(slugify(names[0][0].last))
                else:
                    bibnames = "-".join(slugify(n.last) for n, _ in names)
            else:
                bibnames = "nn"
        title = [
            w
            for w in slugify(paper.get_title("plain")).split("-")
            if not self._is_stopword(w, paper)
        ]
        bibkey = "{}-{}-{}".format(bibnames, str(paper.get("year")), title.pop(0))
        while bibkey in self.bibkeys:  # guarantee uniqueness
            if title:
                bibkey += "-{}".format(title.pop(0))
            else:
                match = re.search(r"-([0-9][0-9]?)$", bibkey)
                if match is not None:
                    num = int(match.group(1)) + 1
                    bibkey = bibkey[: -len(match.group(1))] + "{}".format(num)
                else:
                    bibkey += "-2"
                log.debug(
                    "New bibkey for clash that can't be resolved by adding title words: {}".format(
                        bibkey
                    )
                )
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
            for name, id_ in paper.get(role, []):
                if id_ is None:
                    if len(self.name_to_ids.get(name, [])) > 1:
                        log.error("Paper {} uses ambiguous name '{}' without id".format(paper.full_id, name))
                        log.error("  Please add an id, for example: {}".format(" ".join(self.name_to_ids[name])))
                    id_ = self.resolve_name(name)["id"]
                    explicit = False
                else:
                    if id_ not in self.id_to_canonical:
                        log.error("Paper {} uses name '{}' with id '{}' that does not exist".format(paper.full_id, name, id_))
                    explicit = True
                    
                self.id_to_used[id_].add(name)
                # Register paper
                self.id_to_papers[id_][role].append(paper.full_id)
                self.name_to_papers[name][explicit].append(paper.full_id)
                # Register co-author(s)
                for co_name, co_id in paper.get(role):
                    if co_id is None:
                        co_id = self.resolve_name(co_name)["id"]
                    if co_id != id_:
                        self.coauthors[id_][co_id] += 1

    def verify(self):
        for name, ids in self.name_to_ids.items():
            for id_ in ids:
                cname = self.id_to_canonical[id_]
                if name != cname and name not in self.id_to_used[id_]:
                    log.warning(
                        "Variant name '{}' of '{}' is not used".format(
                            repr(name),
                            repr(cname)))
        for name, d in self.name_to_papers.items():
            if len(d[False]) > 0 and len(d[True]) > 0:
                log.error("Name '{}' is used both with and without explicit id".format(repr(name)))
                log.error(
                    "  Please add an id to paper(s):   {}".format(
                        " ".join(d[False])
                    )
                )
                log.error(
                    "  Or remove the id from paper(s): {}".format(
                        " ".join(d[True])
                    )
                )
        
    def personids(self):
        return self.id_to_canonical.keys()

    def get_canonical_name(self, id_):
        return self.id_to_canonical[id_]

    def set_canonical_name(self, id_, name):
        if id_ in self.id_to_canonical:
            log.error("Person id '{}' is used by both '{}' and '{}'".format(id_, name, self.id_to_canonical[id_]))
        self.id_to_canonical[id_] = name
        self.name_to_ids[name].append(id_)

    def add_variant_name(self, id_, name):
        self.name_to_ids[name].append(id_)

    def get_used_names(self, id_):
        """Return a list of all names used for a given person."""
        return self.id_to_used[id_]

    def get_ids(self, name: PersonName) -> List[str]:
        """
        Returns a list of distinct IDs (people) associated with a surface form.

        :param name: The name (surface form) of the person being searched (id field ignored).
        :return: A list of name ID strings.
        """
        if name not in self.name_to_ids:
            id_ = self.fresh_id(name)
            self.set_canonical_name(id_, name)

        return sorted(self.name_to_ids[name])

    def resolve_name(self, name, id_=None):
        """Find person named 'name' and return a dict with fields
        'first', 'last', 'id'"""
        if id_ is None:
            ids = self.get_ids(name)
            assert len(ids) > 0
            if len(ids) > 1:
                log.debug("Name '{}' is ambiguous between {}".format(
                    repr(name),
                    ', '.join("'{}'".format(i) for i in ids)
                ))
            # Just return the first
            id_ = ids[0]
        d = name.as_dict()
        d["id"] = id_
        return d

    def fresh_id(self, name):
        assert name not in self.name_to_ids, name
        slug, i = slugify(repr(name)), 0
        while slug == "" or slug in self.id_to_canonical:
            i += 1
            slug = "{}{}".format(slugify(repr(name)), i)
        return slug

    def get_papers(self, id_, role=None):
        if role is None:
            return [p for p_list in self.id_to_papers[id_].values() for p in p_list]
        return self.id_to_papers[id_][role]

    def get_coauthors(self, id_):
        return self.coauthors[id_].items()

    def get_venues(self, vidx: VenueIndex, id_):
        """Get a list of venues a person has published in, with counts."""
        venues = Counter()
        for paper in self.get_papers(id_):
            for venue in vidx.get_associated_venues(paper):
                venues[venue] += 1
        return venues
