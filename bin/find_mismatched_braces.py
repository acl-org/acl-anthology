#! /usr/bin/env python3
#
# Copyright 2023 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: find_mismatched_braces.py [--importdir=DIR] [-c | --commit] [--debug]

Checks XML files for wrongly escaped TeX commands (e.g. "{textbf" instead of
"\textbf") and mismatched curly braces.

Options:
  --importdir=DIR          Directory to import XML files from.
                             [default: {scriptdir}/../data/]
  -c, --commit             Commit (=write) the changes to the XML files;
                             will only do a dry run otherwise.
  --debug                  Output debug-level log messages.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
import logging as log
import os
import re

from anthology import Anthology
from anthology.texmath import TexMath
from anthology.utils import SeverityTracker, make_simple_element, indent

import lxml.etree as ET

KNOWN_LATEX_COMMANDS = [
    "frac",
    "mathrm",
    "textrm",
    "text",
    "mathbf",
    "textbf",
    "boldsymbol",
    "mathit",
    "textit",
    "textsc",
    "texttt",
    "textsubscript",
    "textsuperscript",
    "emph",
    "mathcal",
    "bf",
    "rm",
    "it",
    "sc",
    "ref",
    "footnote",
    "underline",
    "url",
    "href",
    "cite",
    "citet",
    "citep",
]
KNOWN_LATEX_COMMANDS.extend(TexMath().cmd_map.keys())


def fix_texmath(match):
    if len(match.group(0)) < 2:
        return match.group(0)
    cmd = match.group(0)[1:]
    if cmd in KNOWN_LATEX_COMMANDS:
        return f"\\{cmd}"
    return match.group(0)


def find_mismatched_braces(anthology, srcdir, commit=False):
    mismatched_braces, fixable_braces = set(), set()

    for volume_id, volume in anthology.volumes.items():
        new_abstracts = {}

        if not volume.has_abstracts:
            continue

        for paper in volume:
            if not paper.has_abstract:
                continue

            abstract = paper.get_abstract("xml")
            brace_l = abstract.count("{")
            brace_r = abstract.count("}")
            if brace_l == brace_r:
                continue

            mismatched_braces.add(paper.full_id)

            # Fixing strategy
            if brace_r > brace_l:
                log.warning(
                    f"Can't fix {paper.full_id}: more right braces than left braces"
                )
            else:
                new_abstract = re.sub(r"{\w+\b", fix_texmath, abstract)
                new_abstract = re.sub("{%", "\\%", new_abstract)
                new_abstract = re.sub("{&amp;", "\\&amp;", new_abstract)
                new_abstract = re.sub("{ ", " ", new_abstract)
                brace_l = new_abstract.count("{")
                if brace_r != brace_l:
                    log.warning(
                        f"Can't fix {paper.full_id}: still unbalanced after substitution"
                    )
                else:
                    fixable_braces.add(paper.full_id)
                    new_abstracts[paper.full_id] = new_abstract

        if not (new_abstracts and commit):
            continue

        # Attempt to fix in XML file
        xml_file = os.path.join(srcdir, "xml", f"{volume.collection_id}.xml")
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for full_id, new_abstract in new_abstracts.items():
            paper = anthology.papers[full_id]

            if paper.paper_id == "0":
                node = root.find(f"./volume[@id='{paper.volume_id}']/frontmatter")
                if node is None:  # dummy frontmatter
                    continue
            else:
                node = root.find(
                    f"./volume[@id='{paper.volume_id}']/paper[@id='{paper.paper_id}']"
                )
            if node is None:
                log.error(f"Paper {paper.full_id} not found in {xml_file}")
                continue

            child = node.find("abstract")
            node.remove(child)
            make_simple_element("abstract", new_abstract, parent=node)

        indent(root)
        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)

    if mismatched_braces:
        unfixable_braces = mismatched_braces - fixable_braces
        log.info(
            f"Found {len(mismatched_braces):3d} abstracts with mismatched braces, can auto-fix {len(fixable_braces):3d} of those."
        )
        log.info(f"    Fixable abstracts: {', '.join(sorted(list(fixable_braces)))}")
        log.info(f"  Unfixable abstracts: {', '.join(sorted(list(unfixable_braces)))}")


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )

    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    log.info("Instantiating the Anthology...")
    anthology = Anthology(importdir=args["--importdir"], require_bibkeys=False)
    log.info("Scanning for mismatched braces...")
    find_mismatched_braces(anthology, args["--importdir"], commit=bool(args["--commit"]))

    if not args["--commit"]:
        if tracker.highest >= log.ERROR:
            log.warning(
                "There were errors! Please check them carefully before re-running this script with -c/--commit."
            )
        else:
            log.info(
                "Re-run this script with -c/--commit to save these changes to the XML files."
            )

    if tracker.highest >= log.ERROR:
        exit(1)
