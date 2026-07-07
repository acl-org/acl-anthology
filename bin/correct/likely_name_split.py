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
import json
import os
import warnings
import logging as log

# ruff: noqa: F403, F405
from math import log as LOG
from math import inf

from acl_anthology import Anthology
from acl_anthology.exceptions import NameSpecResolutionWarning
from acl_anthology.people import Name
from acl_anthology.utils.logging import setup_rich_logging


def log0(x):
    if x == 0:
        return -inf
    else:
        return LOG(x)


class NameSplitter:
    def __init__(self, anthology=None):
        # counts of how often each name appears
        self.first_count = defaultdict(lambda: 0.0)  # "Maria" "Victoria"
        self.first_full_count = defaultdict(lambda: 0.0)  # "Maria Victoria"
        self.last_count = defaultdict(lambda: 0.0)  # "van" "den" "Bosch"
        self.last_full_count = defaultdict(lambda: 0.0)  # "van den Bosch"
        self.first_total = 0
        self.last_total = 0

        if os.path.exists("names.cache"):
            self.load_cache()
        else:
            if anthology is None:
                self.anthology = Anthology.from_within_repo()
            else:
                self.anthology = anthology
            self.count_names(anthology)
            self.dump_cache()

    def load_cache(self):
        with open("names.cache", "r") as cache:
            p = json.load(cache)
            self.first_count = defaultdict(int, p["first_count"])
            self.first_full_count = defaultdict(int, p["first_full_count"])
            self.first_total = p["first_total"]
            self.last_count = defaultdict(int, p["last_count"])
            self.last_full_count = defaultdict(int, p["last_full_count"])
            self.last_total = p["last_total"]
        log.info("Loaded cache from names.cache")

    def dump_cache(self):
        with open("names.cache", "w") as cache:
            p = {
                "first_count": self.first_count,
                "first_full_count": self.first_full_count,
                "first_total": self.first_total,
                "last_count": self.last_count,
                "last_full_count": self.last_full_count,
                "last_total": self.last_total,
            }
            print(json.dumps(p), file=cache)
        log.info("Dumped counts to names.cache")

    # counts names in anthology database into global vars
    # first_count last_count (dicts)
    # first_full_count last_full_count (dicts)
    # first_total last_total (floats)
    def count_names(self, anthology):
        for person in self.anthology.people.values():
            name = person.canonical_name
            if name.first is None:
                continue
            num_papers = sum(1 for paper in person.papers()) + 0.0
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
    def best_split(self, nameobj):
        name = nameobj.as_first_last()

        if "," in name and "Jr." not in name:
            # Short-circuit names that are already split
            # comma in "William Baumgartner, Jr." does not count as a split
            surname, given_names = name.split(",")
            return Name(given_names.strip(), surname.strip())

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
                # more smoothing for first than last name,
                # so that default is one-word last name when all counts are zero
                LOG((self.first_count[x] + 0.1) / self.first_total)
                for x in words[0:i]
            ]
            first_score = max(
                # no smoothing for multiword name: log(0) => -inf
                log0((self.first_full_count[first]) / self.first_total),
                sum(first_probs),
            )
            last_probs = [
                LOG((self.last_count[x] + 0.01) / self.last_total) for x in words[i:]
            ]
            last_score = max(
                log0((self.last_full_count[last]) / self.last_total), sum(last_probs)
            )

            if first_score + last_score > best_score:
                best_score = first_score + last_score
                best = (first, last)
            # end of loop over split points
        return Name.from_(best)


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )

    log_level = log.DEBUG  # if not args.quiet else log.INFO
    tracker = setup_rich_logging(level=log_level)
    log.getLogger("acl-anthology").setLevel(log.WARNING)
    log.getLogger("git.cmd").setLevel(log.WARNING)
    log.getLogger("urllib3.connectionpool").setLevel(log.WARNING)

    with warnings.catch_warnings(category=NameSpecResolutionWarning, action="ignore"):
        anthology = Anthology.from_within_repo()
        anthology.load_all()

    splitter = NameSplitter(anthology)

    # for all names currently in anthology,
    # see if they match what we predict
    for person in anthology.people.values():
        name = person.canonical_name
        if name.first is None:
            continue

        # find our prediction of split
        best = splitter.best_split(name)

        # if current split does not match our prediction
        if best != name:
            # print suggested replacement
            print(name.as_last_first(), "  ==>  ", best.as_last_first())
