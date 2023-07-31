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

"""Usage: _make_journals_explicit.py [--importdir=DIR] [-c | --commit] [--debug]

Options:
  --importdir=DIR          Directory to import XML files from.
                             [default: {scriptdir}/../data/]
  -c, --commit             Commit (=write) the changes to the XML files;
                             will only do a dry run otherwise.
  --debug                  Output debug-level log messages.
  -h, --help               Display this helpful text.
"""

from docopt import docopt
from pathlib import Path
import logging as log
import os
import re

from anthology.formatter import MarkupFormatter
from anthology.utils import (
    SeverityTracker,
    build_anthology_id,
    make_simple_element,
    indent,
    is_newstyle_id,
)

import lxml.etree as ET


### Copy-pasted from data.py and utils.py

JOURNAL_IDS = ("cl", "tacl", "tal", "lilt", "ijclclp")


def is_journal(anthology_id):
    if is_newstyle_id(anthology_id):
        # TODO: this function is sometimes called with "full_id", sometimes with
        # "collection_id", so we're not using `deconstruct_anthology_id` here at
        # the moment
        venue = anthology_id.split("-")[0].split(".")[-1]
        # TODO: this is currently hard-coded, but should be moved to the XML representation
        return venue in JOURNAL_IDS
    else:
        return anthology_id[0] in ("J", "Q")


def match_volume_and_issue(booktitle) -> tuple[str, str]:
    """Parses a volume name and issue name from a title.

    Examples:
    - <booktitle>Computational Linguistics, Volume 26, Number 1, March 2000</booktitle>
    - <booktitle>Traitement Automatique des Langues 2011 Volume 52 Numéro 1</booktitle>
    - <booktitle>Computational Linguistics, Volume 26, Number 1, March 2000</booktitle>

    :param booktitle: The booktitle
    :return: the volume and issue numbers
    """
    volume_no = re.search(r"Volume\s*(\d+)", booktitle, flags=re.IGNORECASE)
    if volume_no is not None:
        volume_no = volume_no.group(1)

    issue_no = re.search(
        r"(Number|Numéro|Issue)\s*(\d+-?\d*)", booktitle, flags=re.IGNORECASE
    )
    if issue_no is not None:
        issue_no = issue_no.group(2)

    return volume_no, issue_no


def get_journal_info(top_level_id, volume_title) -> tuple[str, str, str]:
    """Returns info about the journal: title, volume no., and issue no.
    Currently (Feb 2023), this information is parsed from the <booktitle> tag!
    We should move instead to an explicit representation. See

        https://github.com/acl-org/acl-anthology/issues/2379

    :param top_level_id: The collection ID
    :param volume_title: The text from the <booktitle> tag
    :return: The journal title, volume number, and issue number
    """

    # TODO: consider moving this from code to data (perhaps
    # under <booktitle> in the volume metadata

    top_level_id = top_level_id.split(".")[-1]  # for new-style IDs; is a no-op otherwise

    journal_title = None
    volume_no = None
    issue_no = None

    if top_level_id == "cl":
        # <booktitle>Computational Linguistics, Volume 26, Number 1, March 2000</booktitle>
        journal_title = "Computational Linguistics"
        volume_no, issue_no = match_volume_and_issue(volume_title)

    elif top_level_id == "lilt":
        # <booktitle>Linguistic Issues in Language Technology, Volume 10, 2015</booktitle>
        journal_title = "Linguistic Issues in Language Technology"
        volume_no, _ = match_volume_and_issue(volume_title)

    elif top_level_id == "tal":
        # <booktitle>Traitement Automatique des Langues 2011 Volume 52 Numéro 1</booktitle>
        journal_title = "Traitement Automatique des Langues"
        volume_no, issue_no = match_volume_and_issue(volume_title)

    elif top_level_id == "ijclclp":
        journal_title = "International Journal of Computational Linguistics & Chinese Language Processing"
        volume_no, issue_no = match_volume_and_issue(volume_title)

    elif top_level_id == "nejlt":
        journal_title = "Northern European Journal of Language Technology"
        volume_no, _ = match_volume_and_issue(volume_title)

    elif top_level_id[0] == "J":
        # <booktitle>Computational Linguistics, Volume 26, Number 1, March 2000</booktitle>
        year = int(top_level_id[1:3])
        if year >= 65 and year <= 83:
            journal_title = "American Journal of Computational Linguistics"
        else:
            journal_title = "Computational Linguistics"

        volume_no, issue_no = match_volume_and_issue(volume_title)

    elif top_level_id[0] == "Q" or top_level_id == "tacl":
        journal_title = "Transactions of the Association for Computational Linguistics"
        volume_no, _ = match_volume_and_issue(volume_title)

    else:
        journal_title = volume_title

    return journal_title, volume_no, issue_no


### End copy-paste


formatter = MarkupFormatter()


def fix_journals(srcdir, commit=False):
    for xml_file in Path(srcdir).glob("xml/*.xml"):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        id_ = root.get("id")
        volume_type = "journal" if is_journal(id_) else "proceedings"

        for meta in root.findall("./volume/meta"):
            build_anthology_id(id_, meta.getparent().get('id'))
            if meta.getparent().get("type") is not None:
                continue

            meta.getparent().set("type", volume_type)

            if not is_journal(id_):
                continue

            xml_booktitle = meta.find("booktitle")
            booktitle = formatter.as_text(xml_booktitle)

            title, volume_no, issue_no = get_journal_info(id_, booktitle)
            # xml_booktitle.clear()
            # xml_booktitle.text = title
            if volume_no is not None:
                make_simple_element("journal-volume", text=volume_no, parent=meta)
            if issue_no is not None:
                make_simple_element("journal-issue", text=issue_no, parent=meta)
            if title == "American Journal of Computational Linguistics":
                make_simple_element("journal-title", text=title, parent=meta)

        if commit:
            indent(root)
            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            # log.info(f"Wrote {added} years to {xml_file.name}")


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

    fix_journals(args["--importdir"], commit=bool(args["--commit"]))

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
