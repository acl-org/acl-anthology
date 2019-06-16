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
import anthology.formatter as my_formatter


class PersonName:
    first, last = "", ""

    def __init__(self, first, last):
        self.first = first.strip() if first is not None else ""
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
        if first is None: first = ""
        last = dict_["last"]
        return PersonName(first, last)

    @property
    def full(self):
        return "{} {}".format(self.first, self.last).strip()

    @property
    def id_(self):
        return repr(self)

    def as_bibtex(self):
        if not self.first:
            return "{{{}}}".format(my_formatter.bibtex_encode(self.last))
        return my_formatter.bibtex_encode("{}, {}".format(self.last, self.first))

    def as_dict(self):
        return {"first": self.first, "last": self.last, "full": self.full}

    def __eq__(self, other):
        return (self.first == other.first) and (self.last == other.last)

    def __str__(self):
        return self.full

    def __repr__(self):
        if not self.first:
            return self.last
        return "{} || {}".format(self.first, self.last)

    def __hash__(self):
        return hash(repr(self))
