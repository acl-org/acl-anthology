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

from functools import cached_property
import re
from slugify import slugify
import anthology.formatter as my_formatter


def score_variant(name):
    """Heuristically assign scores to names, with the idea of assigning higher
    scores to spellings more likely to be the correct canonical variant."""
    name = repr(name)
    # Prefer longer variants
    score = len(name)
    # Prefer variants with non-ASCII characters
    score += sum((ord(c) > 127) for c in name)
    # Penalize upper-case characters after word boundaries
    score -= sum(any(c.isupper() for c in w[1:]) for w in re.split(r"\W+", name))
    # Penalize lower-case characters at word boundaries
    score -= sum(w[0].islower() if w else 0 for w in re.split(r"\W+", name))
    if name[0].islower():  # extra penalty for first name
        score -= 1

    return score


class PersonName:
    first, last = "", ""

    def __init__(self, first, last, script="roman", variant: "PersonName" = None):
        self.first = first if first is not None else ""
        self.last = last
        self.script = script
        self.variant = variant

    def from_element(person_element):
        """
        Reads from the XML, which includes an optional first name, a last name,
        and an optional variant (itself containing an optional first name, and a
        last name).
        """
        first, last = "", ""
        # The name variant script, defaults to roman
        script = person_element.attrib.get("script", "roman")
        variant = None
        for element in person_element:
            tag = element.tag

            # These are guaranteed to occur at most once by the schema
            if tag == "first":
                first = element.text or ""
            elif tag == "last":
                last = element.text or ""
            elif tag == "variant":
                variant = PersonName.from_element(element)

        return PersonName(first, last, script=script, variant=variant)

    def from_repr(repr_):
        parts = repr_.split(" || ")
        if len(parts) > 1:
            first, last = parts[0], parts[1]
        else:
            first, last = "", parts[0]
        return PersonName(first, last)

    def from_dict(dict_):
        first = dict_.get("first", "")
        if first is None:
            first = ""
        last = dict_["last"]
        return PersonName(first, last)

    @cached_property
    def full(self):
        """
        Return the full rendering of the name.
        This includes any name variant in parentheses.
        Currently handles both Roman and Han scripts.
        """
        if self.script.startswith("han"):
            form = f"{self.last}{self.first}"
        else:  # default to "roman"
            form = f"{self.first} {self.last}"

        if self.variant is not None:
            return f"{form} ({self.variant.full})"
        else:
            return form

    @cached_property
    def slug(self):
        # This is effectively used as the person's "id".
        # If two names slugify to the same thing, we assume they are the same person.
        # This happens when there are missing accents in one version, or
        # when we have an inconsistent first/last split for multiword names.
        # These cases have in practice always referred to the same person.
        slug = slugify(repr(self))
        if not slug:
            slug = "none"
        return slug

    @cached_property
    def score(self):
        return score_variant(self)

    @property
    def id_(self):
        return repr(self)

    def as_bibtex(self):
        if not self.first:
            return f"{{{my_formatter.bibtex_encode(self.last)}}}"
        return my_formatter.bibtex_encode(f"{self.last}, {self.first}")

    def as_citeproc_json(self):
        if not self.first:
            return {"family": self.last}
        return {"family": self.last, "given": self.first}

    def as_dict(self):
        return {"first": self.first, "last": self.last, "full": self.full}

    def without_variant(self):
        if self.variant is None:
            return self
        return PersonName(self.first, self.last)

    def __eq__(self, other):
        if other is None:
            return False
        return (
            (self.first == other.first)
            and (self.last == other.last)
            and (self.script == other.script)
            and (self.variant == other.variant)
        )

    def __lt__(self, other):
        return self.full < other.full

    def __str__(self):
        return self.full

    def __repr__(self):
        if not self.first:
            return self.last
        return f"{self.first} || {self.last}"

    def __hash__(self):
        return hash(self.full)
