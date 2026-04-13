#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2025 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: transition_to_people_yaml.py [options]

Creates people.yaml and rewrites author IDs in the XML according to <https://github.com/acl-org/acl-anthology/wiki/Author-Page-Plan#transitioning-the-metadata>.

Options:
  --debug                  Output debug-level log messages.
  -d, --datadir=DIR        Directory with data files. [default: {scriptdir}/../../data]
  -x, --write-xml          Write changes to the XML files.
  -y, --write-yaml         Write the new people.yaml.
  -h, --help               Display this helpful text.
"""

from collections import defaultdict
from docopt import docopt
from importlib.metadata import version as get_version
import functools
import itertools as it
import logging as log
import os
import re
import sys
from pathlib import Path
import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:  # pragma: no cover
    from yaml import Loader, Dumper  # type: ignore

from acl_anthology import Anthology
from acl_anthology.people import Name
from acl_anthology.utils.logging import setup_rich_logging

RE_ORCID = re.compile(r"[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]")
"""A regular expression matching any string that looks like an ORCID."""


def is_valid_orcid(orcid: str) -> bool:
    """Validate that a string looks like an ORCID and has the correct checksum.

    Returns:
        True if the ORCID validates, False otherwise.
    """
    if RE_ORCID.fullmatch(orcid) is None:
        return False
    # <https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier>
    total = functools.reduce(
        lambda x, y: (x + int(y)) * 2, orcid[:-1].replace("-", ""), 0
    )
    checksum = (12 - (total % 11)) % 11
    return orcid[-1] == str(checksum) if checksum < 10 else orcid[-1] == "X"


def parse_variant_list(anthology):
    # We create a dictionary mapping person IDs to their original entry in
    # name_variants.yaml; this is because there are fields in name_variants.yaml
    # that the Python library does not store (such as 'orcid' or 'degree'), and
    # we might want to transfer them to the new people.yaml
    name_variants = {}
    with open(
        anthology.datadir / "yaml" / "name_variants.yaml", "r", encoding="utf-8"
    ) as f:
        variant_list = yaml.load(f, Loader=Loader)
    for entry in variant_list:
        if "id" in entry:
            name_variants[entry["id"]] = entry
        else:
            people = anthology.people.get_by_name(Name.from_dict(entry["canonical"]))
            assert len(people) == 1, (
                "Canonical name in name_variants.yaml shouldn't be ambiguous"
            )
            name_variants[people[0].id] = entry
    return name_variants


# This exists to serialize names in "flow" style (i.e. one-liner {first: ...,
# last: ...}), without having to force flow style on the entire YAML document
class YAMLName(yaml.YAMLObject):
    yaml_dumper = Dumper
    yaml_tag = "tag:yaml.org,2002:map"  # serialize like a dictionary
    yaml_flow_style = True  # force flow style

    def __eq__(self, other):
        return (
            getattr(self, "first", "") == getattr(other, "first", "")
            and getattr(self, "last", "") == getattr(other, "last", "")
            and getattr(self, "script", "") == getattr(other, "script", "")
        )

    def __init__(self, first, last, script):
        if first is not None:
            self.first = first
        self.last = last
        if script is not None:
            self.script = script

    def score(self):
        name = Name(getattr(self, "first", None), self.last)
        return name.score()

    def full(self):  # only for testing
        if getattr(self, "first", None):
            return f"{self.first} | {self.last}"
        return self.last


def name_to_yaml(name):
    return YAMLName(name.first, name.last, name.script)


def refactor(anthology, name_variants):
    new_people_dict = {}
    c_removed, c_added = 0, 0

    # These two are to infer if we need to set disable_name_matching: true somewhere
    names_to_ids = defaultdict(list)
    names_with_catchall_id = []
    c_disable_name_matching = 0

    # This is for comparing to the ORCIDs stored in the XML
    orcid_to_id = {}
    invalid_orcids = set()

    # PART A
    # ======
    # Iterate over all entries in name_variants.yaml and map them to the new author
    # system, adding/changing IDs on their papers accordingly.
    for pid, person in anthology.people.items():
        # We only consider people who are currently defined in name_variants.yaml
        if not person.is_explicit:
            continue

        orig_entry = name_variants[pid]
        orcid = orig_entry.get("orcid", None)

        # name_variants.yaml may define IDs that are actually never used
        if not person.item_ids:
            log.warning(
                f"Person '{pid}' derived from name_variants.yaml has no papers; discarding"
            )
            continue

        # If person has a comment like "May refer to multiple people" or "May
        # refer to several people", their identity is "unverified", so we:
        #   - Don't write them to people.yaml
        #   - Remove their ID from the XML
        if person.comment is not None and person.comment.startswith("May refer"):
            log.debug(f"Removing ID '{pid}' ('{person.comment}')")
            for paper in person.papers():
                # Remove their ID from the XML
                for namespec in it.chain(paper.authors, paper.get_editors()):
                    if namespec.id == pid:
                        namespec.id = None
                        c_removed += 1

            # Record the name(s) of this person so we can check later if this ID
            # was important for disambiguation
            names_with_catchall_id.extend(person.names)

            # Don't process this person further
            continue

        # If we reach this point, this person should be considered "verified"
        # under the new system.  However, maybe not all of their *names* should
        # go into people.yaml---a name can have been added to `person.names` in
        # different ways:
        #
        #   1. It was listed explicitly in `name_variants.yaml` -- keep
        #   2. It was in the XML with this person's explicit ID -- keep
        #   3. It was added to this person via the name matching mechanism that
        #      compares slugified names -- don't keep, as it was inferred heuristically
        #
        # (This happens in <https://github.com/acl-org/acl-anthology/blob/170ff9706aba87de0e353da690e6b0bb33ea6a98/python/acl_anthology/people/index.py#L252-L299>)
        c = 0
        names_to_keep = {Name.from_dict(orig_entry["canonical"])} | {
            Name.from_dict(name) for name in orig_entry.get("variants", [])
        }  # Case 1

        for paper in person.papers():
            namespecs = list(
                it.chain(paper.authors, paper.get_editors())
                if paper.is_frontmatter
                else it.chain(paper.authors, paper.editors)
            )

            found_explicit_id = False
            for namespec in namespecs:
                if namespec.id == pid:
                    names_to_keep.add(namespec.name)  # Case 2
                    found_explicit_id = True

            if not found_explicit_id:
                # Does *not* already have an explicit ID in the XML; add it.
                # ---
                # NOTE: Doing this in a separate loop to avoid the edge case where
                # a paper might have two authors with identical names,
                # disambiguated by their ID---not sure if that ever happens, but
                # better be safe than sorry.
                found_matching_name = False
                for namespec in namespecs:
                    if person.has_name(namespec.name):
                        found_matching_name = True
                        if namespec.name in names_to_keep:  # Avoid case 3
                            namespec.id = pid
                            c += 1
                            c_added += 1

                if not found_matching_name:
                    # Should never happen
                    log.error(
                        f"Did not find '{pid}' on paper '{paper.full_id}' connected to them",
                    )

            # Also check if there is an ORCID here, and if so, record it
            if orcid is None:
                for namespec in namespecs:
                    if namespec.id == pid and namespec.orcid is not None:
                        # Is it valid?
                        if not is_valid_orcid(namespec.orcid):
                            namespec.orcid = None
                            log.warning(f"Removing invalid ORCID: {namespec.orcid}")
                            invalid_orcids.add(namespec.orcid)
                        else:
                            orcid = namespec.orcid
                        break

        if c > 0:
            log.debug(f"Added explicit ID '{pid}' to {c} papers")

        for name in person.names:
            names_to_ids[name].append(pid)

        # Construct entry for new people.yaml
        canonical = Name.from_dict(orig_entry["canonical"])
        entry = {
            # First name is always the canonical one
            "names": [
                name_to_yaml(name)
                for name in it.chain((canonical,), names_to_keep - {canonical})
            ],
        }
        if person.comment is not None:
            entry["comment"] = person.comment
        # These are keys we copy over from the old name_variants.yaml
        for key in ("degree", "similar"):
            if key in orig_entry:
                entry[key] = orig_entry[key]

        if orcid is not None:
            if is_valid_orcid(orcid):
                if orcid in orcid_to_id:
                    log.error(
                        f"Can't assign ORCID {orcid} to {pid}; already assigned to {orcid_to_id[orcid]}"
                    )
                else:
                    entry["orcid"] = orcid
                    orcid_to_id[orcid] = pid
            else:
                log.warning(f"Removing invalid ORCID: {orcid}")
                invalid_orcids.add(orcid)

        new_people_dict[pid] = entry

    # PART B
    # ======
    # Iterate over all papers with recorded ORCIDs that aren't assigned to
    # explicit IDs, and create one for them.
    inferred_from_orcid = defaultdict(list)
    for paper in anthology.papers():
        # Look at the namespecs directly attached to this paper
        for namespec in it.chain(paper.authors, paper.editors):
            if (orcid := namespec.orcid) is not None:
                # Is it valid?
                if not is_valid_orcid(orcid):
                    namespec.orcid = None
                    log.warning(f"Removing invalid ORCID: {orcid}")
                    invalid_orcids.add(orcid)
                    continue

                # Does namespec have an explicit ID?
                if (pid := namespec.id) is not None:
                    # This was handled in PART A, but double-check for consistency
                    if orcid_to_id.get(orcid) != pid:
                        log.error(
                            f"ORCID {orcid} used with {pid}, but assigned to {orcid_to_id.get(orcid)}"
                        )
                else:
                    # No explicit ID recorded — do we know the ORCID already?
                    if orcid in orcid_to_id:
                        # Yes — use the known person
                        pid = orcid_to_id[orcid]
                        # ...and make sure this particular name is connected with the person
                        name = name_to_yaml(namespec.name)
                        if name not in new_people_dict[pid]["names"]:
                            canonical = new_people_dict[pid]["names"][0]
                            if (
                                pid in inferred_from_orcid
                                and name.score() > canonical.score()
                            ):
                                # This name should be considered canonical
                                # according to our logic – set as canonical and
                                # also update the auto-generated ID
                                old_pid = pid
                                new_pid = namespec.name.slugify()
                                if old_pid != new_pid and new_pid not in new_people_dict:
                                    # ID has changed and is not already in use
                                    for processed_namespec in inferred_from_orcid[
                                        old_pid
                                    ]:
                                        processed_namespec.id = new_pid
                                    new_people_dict[new_pid] = new_people_dict.pop(
                                        old_pid
                                    )
                                    orcid_to_id[orcid] = new_pid
                                    inferred_from_orcid[new_pid] = (
                                        inferred_from_orcid.pop(old_pid)
                                    )
                                    pid = new_pid
                                new_people_dict[pid]["names"].insert(0, name)
                            else:
                                new_people_dict[pid]["names"].append(name)
                        inferred_from_orcid[pid].append(namespec)
                    else:
                        # No — create that person
                        entry = {
                            "names": [name_to_yaml(namespec.name)],
                            "orcid": orcid,
                        }
                        pid = namespec.name.slugify()
                        if pid in new_people_dict:
                            # ID is already in use; add last four digits of ORCID to disambiguate
                            pid = f"{pid}-{orcid[-4:].lower()}"
                        new_people_dict[pid] = entry
                        orcid_to_id[orcid] = pid
                        inferred_from_orcid[pid].append(namespec)
                    # Add the ID to the namespec
                    namespec.id = pid
                    c_added += 1

    # Check where we need to set "disable_name_matching: true"
    for name in names_with_catchall_id:
        pids = names_to_ids.get(name, [])
        if len(pids) == 1:
            # There is only one "verified" person with this name, but there was
            # a catch-all ID ("May refer to several people") with this name too,
            # so we need to disable name matching under the new system
            new_people_dict[pids[0]]["disable_name_matching"] = True
            c_disable_name_matching += 1

    log.info(
        f"Removed {c_removed:>5d} explicit IDs from the XML ('May refer to several people' etc.)"
    )
    log.info(f"  Added {c_added:>5d} explicit IDs to the XML")
    log.info(f"Created {len(new_people_dict):>5d} entries for people.yaml")
    log.info(
        f"        {c_disable_name_matching:>5d} of those have `disable_name_matching: true`"
    )
    log.info(f"Removed {len(invalid_orcids):>5d} unique invalid ORCIDs")

    return new_people_dict


if __name__ == "__main__":
    args = docopt(__doc__)

    log_level = log.DEBUG if args["--debug"] else log.INFO
    tracker = setup_rich_logging(level=log_level)

    try:
        from acl_anthology.people.index import VARIANTS_FILE  # noqa: F401

        assert get_version("acl_anthology") == "0.5.4"
    except (ImportError, AssertionError):
        log.error("Library does not support name_variants.yaml")
        print(
            """
This script must be run with v0.5.4 of the acl-anthology library; you either use
an older or the in-repo version of the library.  Create a new virtualenv, then:

    pip install acl-anthology==0.5.4

Then re-run this script.""",
            file=sys.stderr,
        )
        exit(1)

    if "{scriptdir}" in args["--datadir"]:
        args["--datadir"] = os.path.abspath(
            args["--datadir"].format(scriptdir=os.path.dirname(os.path.abspath(__file__)))
        )
    datadir = Path(args["--datadir"])
    log.info(f"Using data directory {datadir}")

    anthology = Anthology(datadir=datadir)
    anthology.load_all()

    name_variants = parse_variant_list(anthology)
    log.info(f"  Found {len(name_variants):>5d} entries in name_variants.yaml")

    new_people_dict = refactor(anthology, name_variants)

    if tracker.highest >= log.ERROR:
        log.warning("There were errors; aborting without saving")
        exit(1)

    if args["--write-yaml"]:
        log.info("Writing new people.yaml...")
        with open(datadir / "yaml" / "people.yaml", "w", encoding="utf-8") as f:
            yaml.dump(new_people_dict, f, allow_unicode=True, Dumper=Dumper)
        vf = anthology.datadir / "yaml" / "name_variants.yaml"
        vf.unlink()
    else:
        log.warning("Not writing people.yaml; use -y/--write-yaml flag")

    if args["--write-xml"]:
        log.info("Saving XML files...")
        for collection in anthology.collections.values():
            collection.save()
    else:
        log.warning("Not modifying XML files; use -x/--write-xml flag")
