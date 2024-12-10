#!/usr/bin/env python3
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

"""Usage: create_bibtex.py [--importdir=DIR] [--exportdir=DIR] [-c] [--debug]

Creates .bib files for all papers in the Hugo directory.

Options:
  --importdir=DIR          Directory to import XML files from. [default: {scriptdir}/../data/]
  --exportdir=DIR          Directory to write exported files to.   [default: {scriptdir}/../build/data-export/]
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -h, --help               Display this helpful text.
"""

import re
import gzip
import logging as log
import os
import datetime

from docopt import docopt
from tqdm import tqdm
from pathlib import Path

from anthology import Anthology
from anthology.utils import SeverityTracker, deconstruct_anthology_id, infer_year
from create_hugo_pages import check_directory


def volume_sorter(volume_tuple):
    """
    Extracts the year so that we can sort by the year and then
    the collection ID.
    """
    volume_id = volume_tuple[0]
    collection_id, year, _ = deconstruct_anthology_id(volume_id)
    year = infer_year(collection_id)
    return year, volume_id


def create_bibtex(anthology, trgdir, limit=0, clean=False) -> None:
    """Creates .bib files for all papers.

    :param anthology: The Anthology object.
    :param trgdir: The target directory to write to
    :param limit: If nonzero, only generate {limit} entries per volume
    :param clean: Clean the directory first
    """
    if not check_directory("{}/papers".format(trgdir), clean=clean):
        return
    if not check_directory("{}/volumes".format(trgdir), clean=clean):
        return

    log.info("Creating BibTeX files for all papers...")
    with open(
        "{}/anthology.bib".format(trgdir), "wt", encoding="utf-8"
    ) as file_anthology_raw, gzip.open(
        "{}/anthology.bib.gz".format(trgdir), "wt", encoding="utf-8"
    ) as file_anthology, gzip.open(
        "{}/anthology+abstracts.bib.gz".format(trgdir), "wt", encoding="utf-8"
    ) as file_anthology_with_abstracts:
        # Add a header to each consolidated bibfile
        for outfh in file_anthology_raw, file_anthology, file_anthology_with_abstracts:
            print(
                f"% https://aclanthology.org/{Path(outfh.name).name} generated on {datetime.date.today().isoformat()}\n",
                file=outfh,
            )

        # Add some shortcuts to the uncompressed consolidated bib file
        print(
            "@string{acl = {Association for Computational Linguistics}}",
            file=file_anthology_raw,
        )
        print("@string{anth = {https://aclanthology.org/}}", file=file_anthology_raw)
        print(file=file_anthology_raw)

        for volume_id, volume in tqdm(
            sorted(anthology.volumes.items(), key=volume_sorter, reverse=True)
        ):
            # reset this each time
            abbrev = None

            volume_dir = trgdir
            if not os.path.exists(volume_dir):
                os.makedirs(volume_dir)
            with open("{}/volumes/{}.bib".format(trgdir, volume_id), "w") as file_volume:
                for i, paper in enumerate(volume, 1):
                    if limit and i > limit:
                        break

                    with open(
                        "{}/{}.bib".format(volume_dir, paper.full_id), "w"
                    ) as file_paper:
                        contents = paper.as_bibtex()
                        print(contents, file=file_paper)
                        print(contents, file=file_anthology_with_abstracts)

                        concise_contents = paper.as_bibtex(concise=True)
                        print(concise_contents, file=file_volume)
                        print(concise_contents, file=file_anthology)

                        # Space saver (https://github.com/acl-org/acl-anthology/issues/3016) for the
                        # uncompressed consolidated bibfile.
                        # Replace verbose text with abbreviations to get the file under 50 MB for Overleaf
                        concise_contents = concise_contents.replace(
                            'publisher = "Association for Computational Linguistics",',
                            "publisher = acl,",
                        )
                        concise_contents = re.sub(
                            r'url = "https://aclanthology.org/(.*)"',
                            r"url = anth # {\1}",
                            concise_contents,
                        )

                        # Abbreviate the booktitle by extracting it and printing it before
                        # the first entry in each volume
                        if concise_contents.startswith("@proceedings"):
                            # Grab the title string and create the alias
                            abbrev = f"{volume.get_venues()[0].upper()}:{infer_year(volume.collection_id)}:{volume.volume_id}"
                            try:
                                booktitle = re.search(
                                    r"    title = \"(.*)\",", concise_contents
                                ).group(1)
                                print(
                                    f"@string{{{abbrev} = {{{booktitle}}}}}",
                                    file=file_anthology_raw,
                                )
                            except AttributeError:
                                import sys

                                print(
                                    f"Could not find title for {volume_id}",
                                    file=sys.stderr,
                                )
                                abbrev = None

                        if abbrev is not None and "booktitle" in concise_contents:
                            # substitute the alias for the booktitle
                            concise_contents = re.sub(
                                r"    booktitle = (\".*\"),",
                                f"    booktitle = {abbrev},",
                                concise_contents,
                            )

                        # Remove whitespace to save space and keep things under 50 MB
                        concise_contents = re.sub(r",\n +", ",", concise_contents)
                        concise_contents = re.sub(r"  and\n +", " and ", concise_contents)
                        concise_contents = re.sub(r",\n}", "}", concise_contents)

                        print(concise_contents, file=file_anthology_raw)


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--importdir"]:
        args["--importdir"] = os.path.abspath(
            args["--importdir"].format(scriptdir=scriptdir)
        )
    if "{scriptdir}" in args["--exportdir"]:
        args["--exportdir"] = os.path.abspath(
            args["--exportdir"].format(scriptdir=scriptdir)
        )

    log_level = log.DEBUG if args["--debug"] else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    # If NOBIB is set, generate only three bibs per volume
    limit = 0 if os.environ.get("NOBIB", "false") == "false" else 3
    if limit != 0:
        log.info(f"NOBIB=true, generating only {limit} BibTEX files per volume")

    anthology = Anthology(importdir=args["--importdir"], fast_load=True)
    create_bibtex(anthology, args["--exportdir"], limit=limit, clean=args["--clean"])

    if tracker.highest >= log.ERROR:
        exit(1)
