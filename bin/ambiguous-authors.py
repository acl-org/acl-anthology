#!/usr/bin/env python3

"""
Takes a list of collection IDs as arguments, and outputs a TSV
(name, Anthology ID, paper title) containing every person who
is the first author of a paper and has no other papers in the
Anthology.

Place in acl-anthology/bin and run

   ./bin/new-authors.py 2020.acl

which returns all first authors who had their first paper at ACL 
2020. Note that this doesn't ignore future volumes, so if run in
2024, this will no longer work for 2020.

Author: Matt Post
"""

import os
import sys

from anthology import Anthology
from anthology.people import PersonName
from anthology.utils import deconstruct_anthology_id

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser()
  args = parser.parse_args()

  anthology = Anthology(importdir=os.path.join(os.path.dirname(sys.argv[0]), "..", "data"))

  for key, value in anthology.people.name_to_ids.items():
    if len(value) > 1:
      print(key, "->", value)
