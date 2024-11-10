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
from functools import lru_cache
import itertools as it
from slugify import slugify
from stop_words import get_stop_words
from .people import PersonName

from typing import List, Dict

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


BIBKEY_MAX_NAMES = 2


def load_stopwords(language):
    return [t for w in get_stop_words(language) for t in slugify(w).split("-")]


# Temporary hack until we refactor person/name handling
class defaultdict_names(defaultdict):
    """This is a defaultdict that indexes PersonName objects, but without regard
    for any locally defined name variant, so that PersonName('X', 'Y') and
    PersonName('X', 'Y', variant=foo) will key to the same thing.
    """

    def __getitem__(self, key: PersonName):
        return super().__getitem__(key.without_variant())

    def __setitem__(self, key: PersonName, val):
        return super().__setitem__(key.without_variant(), val)

    def __delitem__(self, key: PersonName):
        return super().__delitem__(key.without_variant())

    def __contains__(self, key: PersonName):
        return super().__contains__(key.without_variant())

    def get(self, key: PersonName, default=None):
        return super().get(key.without_variant(), default)


class AnthologyIndex:
    """Keeps an index of people and papers.

    This class provides:
    - An index of people (authors/editors) with their internal IDs, canonical
      names, and name variants.
    - A mapping of people to all papers associated with them.
    - A set of all bibliography keys used within the Anthology and a method to
      create new ones, guaranteeing uniqueness.

    The index is NOT automatically populated when instantiating this class, but
    rather gets its data from papers being registered in it as they are loaded
    from the XML by the main `Anthology` class.

    :param srcdir: Path to the Anthology data directory. Only used for loading
    the list of name variants.
    :param fast_load: Whether to disable some error checking in favor of faster
    loading.
    :param require_bibkeys: Whether to log an error when a paper being added
    does not have a bibkey. Should only be set to False during the ingestion of
    new papers, when this class is being used to generate new, unique bibkeys.
    """

    def __init__(self, srcdir=None, fast_load=False, require_bibkeys=True, parent=None):
        self._parent = parent
        self._fast_load = fast_load
        self._require_bibkeys = require_bibkeys
        self.bibkeys = set()
        self.stopwords = load_stopwords("en")
        self.id_to_canonical = {}  # maps ids to canonical names
        self._id_to_used = defaultdict(set)  # maps ids to all names actually used
        self.name_to_ids = defaultdict_names(list)  # maps canonical/variant names to ids
        self._coauthors = defaultdict(Counter)  # maps ids to co-author ids
        self.comments = (
            {}
        )  # maps ids to comments (used for distinguishing authors with same name)
        self._similar = defaultdict(set)
        self.id_to_papers = defaultdict(lambda: defaultdict(list))  # id -> role -> papers
        self.name_to_papers = defaultdict_names(
            lambda: defaultdict(list)
        )  # name -> (explicit id?) -> papers; used only for error checking
        if srcdir is not None:
            self.load_variant_list(srcdir)

    def load_variant_list(self, directory):
        with open(f"{directory}/yaml/name_variants.yaml", "r") as f:
            name_list = yaml.load(f, Loader=Loader)

            # Reserve ids for people with explicit ids in variant list
            for entry in name_list:
                if "id" in entry:
                    id_ = entry["id"]
                    canonical = entry["canonical"]
                    canonical = PersonName.from_dict(canonical)
                    self.set_canonical_name(id_, canonical)
            # Automatically add people with same canonical name to similar list
            if not self._fast_load:
                for name, ids in self.name_to_ids.items():
                    if len(ids) > 1:
                        for id1, id2 in it.permutations(ids, 2):
                            self._similar[id1].add(id2)
            for entry in name_list:
                try:
                    canonical = entry["canonical"]
                    variants = entry.get("variants", [])
                    id_ = entry.get("id", None)
                except (KeyError, TypeError):
                    log.error(f"Couldn't parse name variant entry: {entry}")
                    continue
                canonical = PersonName.from_dict(canonical)
                if id_ is None:
                    if canonical in self.name_to_ids:
                        log.error(
                            f"Canonical name '{canonical}' is ambiguous but doesn't have an id; please add one"
                        )
                    id_ = canonical.slug
                    self.set_canonical_name(id_, canonical)
                for variant in variants:
                    variant = PersonName.from_dict(variant)
                    if variant in self.name_to_ids:
                        log.error(
                            "Tried to add '{}' as variant of '{}', but is already a variant of '{}'".format(
                                repr(variant),
                                repr(canonical),
                                repr(self.id_to_canonical[self.name_to_ids[variant][0]]),
                            )
                        )
                        continue
                    self.add_variant_name(id_, variant)
                if "comment" in entry:
                    self.comments[id_] = entry["comment"]
                if "similar" in entry and not self._fast_load:
                    self._similar[id_].update(entry["similar"])
                    for other in entry["similar"]:
                        if id_ not in self._similar[other]:
                            log.debug(f'inferring similar name {other} -> {id_}')
                        self._similar[other].add(id_)

        # form transitive closure of self._similar
        if not self._fast_load:
            again = True
            while again:
                again = False
                for x in list(self._similar):
                    for y in list(self._similar[x]):
                        for z in list(self._similar[y]):
                            if z != x and z not in self._similar[x]:
                                self._similar[x].add(z)
                                log.debug(f'inferring similar name {x} -> {z}')
                                again = True

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

    def create_bibkey(self, paper, vidx=None):
        """Create a unique bibliography key for the given paper."""
        if self._fast_load:
            raise Exception(
                "Cannot create bibkeys when AnthologyIndex is instantiated with fast_load=True"
            )

        # Regular papers use the first title word, then add title words until uniqueness is achieved
        title = [
            w
            for w in slugify(paper.get_title("plain")).split("-")
            if not self._is_stopword(w, paper)
        ]

        if paper.is_volume:
            # Proceedings volumes use venue acronym instead of authors/editors, e.g., lrec-tutorials-2024
            bibnames = slugify(paper.get_venue_acronym())
            bibkey = f"{bibnames}-{paper.get('year')}-{paper.volume_id}"
        else:
            # Regular papers use author/editor names
            names = paper.get("author")
            if not names:
                names = paper.get("editor", [])
            if names:
                if len(names) > BIBKEY_MAX_NAMES:
                    bibnames = f"{slugify(names[0][0].last)}-etal"
                else:
                    bibnames = "-".join(slugify(n.last) for n, _ in names)
            else:
                bibnames = "nn"

            bibkey = f"{bibnames}-{paper.get('year')}-{title.pop(0)}"

        while bibkey in self.bibkeys:  # guarantee uniqueness
            if title:
                bibkey += f"-{title.pop(0)}"
            else:
                match = re.search(r"-([0-9][0-9]?)$", bibkey)
                if match is not None:
                    num = int(match.group(1)) + 1
                    bibkey = bibkey[: -len(match.group(1))] + f"{num}"
                else:
                    bibkey += "-2"
                log.debug(
                    f"New bibkey for clash that can't be resolved by adding title words: {bibkey}"
                )
        paper.bibkey = bibkey
        self.register_bibkey(paper)
        return bibkey

    def register_bibkey(self, paper):
        """Register a paper's bibkey in Anthology-wide set to ensure uniqueness."""
        key = paper.bibkey
        if key is None:
            if self._require_bibkeys:
                log.error(f"Paper {paper.full_id} has no bibkey!")
            return
        if key in self.bibkeys:
            log.error(f"Paper {paper.full_id} has bibkey that is not unique ({key})!")
            return
        self.bibkeys.add(key)

    def register(self, paper, dummy=False):
        """Register bibkey and names associated with the given paper.

        :param dummy: If True, will only resolve the author/editor names without
        actually linking them to the given paper.  This is used for volumes
        without frontmatter to make sure their editors still get registered
        here, but without creating links to a non-existent paper.
        """
        from .papers import Paper

        assert isinstance(
            paper, Paper
        ), f"Expected Paper, got {type(paper)} ({repr(paper)})"
        # Make sure paper has a bibkey and it is unique (except for dummy
        # frontmatter, as it is not an actual paper)
        if not dummy and not self._fast_load:
            self.register_bibkey(paper)
        # Resolve and register authors/editors for this paper
        for role in ("author", "editor"):
            for name, id_ in paper.get(role, []):
                if id_ is None:
                    if len(self.name_to_ids.get(name, [])) > 1:
                        log.error(
                            f"Paper {paper.full_id} uses ambiguous name '{name}' without id"
                        )
                        log.error(
                            "  Please add an id, for example: {}".format(
                                " ".join(self.name_to_ids[name])
                            )
                        )
                    id_ = self.resolve_name(name)["id"]
                    explicit = False
                else:
                    if id_ not in self.id_to_canonical:
                        log.error(
                            f"Paper {paper.full_id} uses name '{name}' with id '{id_}' that does not exist"
                        )
                    explicit = True

                if not self._fast_load:
                    self._id_to_used[id_].add(name)

                if not dummy and (role == "author" or paper.is_volume):
                    # Register paper
                    self.id_to_papers[id_][role].append(paper.full_id)
                    if not self._fast_load:
                        self.name_to_papers[name][explicit].append(paper.full_id)
                        # Register co-author(s)
                        for co_name, co_id in paper.get(role):
                            if co_id is None:
                                co_id = self.resolve_name(co_name)["id"]
                            if co_id != id_:
                                self._coauthors[id_][co_id] += 1

    @property
    def id_to_used(self):
        if self._fast_load and not self._id_to_used:
            for paper in self._parent.papers.values():
                for name, id_, _ in paper.iter_people():
                    self._id_to_used[id_].add(name)
        return self._id_to_used

    @property
    def coauthors(self):
        if self._fast_load and not self._coauthors:
            for paper in self._parent.papers.values():
                people = list(paper.iter_people())
                for p1, p2 in it.permutations(people, 2):
                    name1, id1, role1 = p1
                    name2, id2, role2 = p2
                    if role1 != role2:
                        continue
                    if id1 is None:
                        id1 = self.resolve_name(name1)["id"]
                    if id2 is None:
                        id2 = self.resolve_name(name2)["id"]
                    self._coauthors[id1][id2] += 1
        return self._coauthors

    @property
    def similar(self):
        if self._fast_load:
            raise Exception(
                "Cannot retrieve list of similar names when AnthologyIndex is instantiated with fast_load=True"
            )
        return self._similar

    def personids(self):
        return self.id_to_canonical.keys()

    def get_canonical_name(self, id_):
        return self.id_to_canonical[id_]

    def set_canonical_name(self, id_, name):
        if (id_ not in self.id_to_canonical) or (
            name.score > self.id_to_canonical[id_].score
        ):
            # if name not seen yet, or if this version has more accents
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
            id_ = name.slug
            self.set_canonical_name(id_, name)

        return sorted(self.name_to_ids[name])

    def get_comment(self, id_: str) -> str:
        """
        Returns the comment associated with the name ID.

        :param id_: The name ID (e.g., "fei-liu-utdallas")
        :return: The comment (e.g., "UT Dallas, Bosch, CMU, University of Central Florida")
        """
        return self.comments.get(id_, None)

    @lru_cache(maxsize=2**16)
    def resolve_name(self, name, id_=None) -> Dict:
        """Find person named 'name' and return a dict with fields
        'first', 'last', 'id'"""
        if id_ is None:
            ids = self.get_ids(name)
            assert len(ids) > 0
            if len(ids) > 1:
                log.debug(
                    "Name '{}' is ambiguous between {}".format(
                        repr(name), ", ".join(f"'{i}'" for i in ids)
                    )
                )
            # Just return the first
            id_ = ids[0]
        d = name.as_dict()
        d["id"] = id_
        return d

    def get_papers(self, id_, role=None):
        if role is None:
            return [p for p_list in self.id_to_papers[id_].values() for p in p_list]
        return self.id_to_papers[id_][role]

    def get_coauthors(self, id_):
        return self.coauthors[id_].items()

    def get_venues(self, id_):
        """Get a list of venues a person has published in, with counts."""
        venues = Counter()
        for paper in self.get_papers(id_):
            for venue in self._parent.papers[paper].parent_volume.get_venues():
                venues[venue] += 1
        return venues
