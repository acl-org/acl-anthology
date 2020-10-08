#!/usr/bin/env python3
# Daniel Gildea, 2020

"""Usage: likely_name_split.py [--importdir=DIR]

Counts first and last names in anthology.
Predicts best split into first and last.
Checks whether current names match our predictions.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../data/]
  -h, --help               Display this helpful text.
"""

from collections import defaultdict
from docopt import docopt
import re
import os
from math import *

from anthology import Anthology
from anthology.people import PersonName


class NameSplitter:
    def __init__(self, anthology):
        # counts of how often each name appears
        self.first_count = defaultdict(lambda: 0)  # "Maria" "Victoria"
        self.first_full_count = defaultdict(lambda: 0)  # "Maria Victoria"
        self.last_count = defaultdict(lambda: 0)  # "van" "den" "Bosch"
        self.last_full_count = defaultdict(lambda: 0)  # "van den Bosch"
        self.first_total = 0
        self.last_total = 0

        self.count_names(anthology)

    # counts names in anthology database into global vars
    # first_count last_count (dicts)
    # first_full_count last_full_count (dicts)
    # first_total last_total (floats)
    def count_names(self, anthology):
        for person in anthology.people.personids():
            name = anthology.people.get_canonical_name(person)
            num_papers = len(anthology.people.get_papers(person)) + 0.0
            # print(name.last, ", ", name.first, num_papers)
            for w in name.first.split(" "):
                self.first_count[w] += num_papers
            self.first_full_count[name.first] += num_papers
            self.first_total += num_papers

            for w in name.last.split(" "):
                self.last_count[w] += num_papers
            self.last_full_count[name.last] += num_papers
            self.last_total += num_papers

    # takes "Maria Victoria Lopez Gonzalez"
    # returns ("Lopez Gonzalez", "Maria Victoria")
    # uses counts of words in first and last names in current database
    def best_split(self, name):
        if "," in name and not "Jr." in name:
            # Short-circuit names that are already split
            # comma in "William Baumgartner, Jr." does not count as a split
            surname, given_names = name.split(",")
            return (surname.strip(), given_names.strip())

        words = name.split(" ")
        best_score = -inf
        best = ("", "")
        # loop over possible split points between first/last
        for i in range(1, len(words)):  # at least one word in each part
            first = " ".join(words[0:i])
            last = " ".join(words[i:])
            # max of log prob of "Maria Victoria" and
            # log prob of "Maria" + log prob of "Victoria"
            first_probs = [
                log((self.first_count[x] + 0.01) / self.first_total) for x in words[0:i]
            ]
            first_score = max(
                log((self.first_full_count[first] + 0.000001) / self.first_total),
                sum(first_probs),
            )
            last_probs = [
                log((self.last_count[x] + 0.01) / self.last_total) for x in words[i:]
            ]
            last_score = max(
                log((self.last_full_count[last] + 0.000001) / self.last_total),
                sum(last_probs),
            )

            if first_score + last_score > best_score:
                best_score = first_score + last_score
                best = (last, first)
            # end of loop over split points
        return best


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )

    anthology = Anthology(importdir=args["--importdir"])
    splitter = NameSplitter(anthology)

    # for all names currently in anthology,
    # see if they match what we predict
    for person in anthology.people.personids():
        name = anthology.people.get_canonical_name(person)

        # find our prediction of split
        best = splitter.best_split(name.first + " " + name.last)

        # if current split does not match our prediction
        if not (best[0] == name.last and best[1] == name.first):
            # print suggested replacement
            print(name.last, ",", name.first, "  ==>  ", best[0], ",", best[1])
