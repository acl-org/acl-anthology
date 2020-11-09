#!/usr/bin/env python3
# Marcel Bollmann <marcel@bollmann.me>, 2019

"""Usage: find_name_variants.py [--importdir=DIR]

Heuristically try to find variants of names not yet covered by name_variants.yaml
Finds names that slugify to the same thing.  Handles missing accents and
mistakes in first/last split, but not things like Tom/Thomas.  Prints output
that can be pasted into name_variants.yaml.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../data/]
  -h, --help               Display this helpful text.
"""

from collections import defaultdict
from docopt import docopt
from slugify import slugify
import re
import os
import yaml, yamlfix

from anthology import Anthology
from anthology.people import PersonName


def score_variant(name):
    """Heuristically assign scores to names, with the idea of assigning higher
    scores to spellings more likely to be the correct canonical variant."""
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


def to_dict(pn):
    return {"first": pn.first, "last": pn.last}


def main(anthology):
    variants = defaultdict(list)
    slugs = {}
    for person in anthology.people.personids():
        name = anthology.people.get_canonical_name(person)
        name_slug = slugify(repr(name))
        if name_slug in slugs:
            variants[slugs[name_slug]].append(repr(name))
        else:
            slugs[name_slug] = repr(name)

    canonical_variants = []
    for var1, varlist in variants.items():
        varlist.append(var1)
        # Determine best canonical variant
        scores = {var: score_variant(var) for var in varlist}
        canonical = max(scores.items(), key=lambda k: k[1])[0]
        canonical_variants.append(
            {
                "canonical": to_dict(PersonName.from_repr(canonical)),
                "variants": [
                    to_dict(PersonName.from_repr(var))
                    for var in varlist
                    if var != canonical
                ],
            }
        )

    canonical_variants.sort(
        key=lambda x: (x["canonical"]["last"], x["canonical"]["first"])
    )
    # flow style to match format of file name_variants.yaml
    print(yaml.dump(canonical_variants, allow_unicode=True, default_flow_style=None))


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )

    anthology = Anthology(importdir=args["--importdir"])
    main(anthology)
