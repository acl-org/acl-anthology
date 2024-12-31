#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2024 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: create_bib.py [--builddir=DIR] [-c] [--debug]

Creates anthology.bib files and MODS/Endnote formats for all papers in the Hugo directory.

Options:
  --builddir=DIR           Directory with build files; used both for reading and writing. [default: {scriptdir}/../build/]
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -h, --help               Display this helpful text.
"""

import datetime
from docopt import docopt
import gzip
import logging as log
import os
import msgspec
from pathlib import Path
import re
from rich.progress import track
import subprocess

from acl_anthology import config
from acl_anthology.utils.ids import infer_year
from acl_anthology.utils.logging import setup_rich_logging


DECODER = msgspec.json.Decoder()
ENCODER = msgspec.json.Encoder()


def create_bibtex(builddir, clean=False) -> None:
    """Create full Anthology BibTeX files."""
    with (
        open(
            f"{builddir}/data-export/anthology.bib", "wt", encoding="utf-8"
        ) as file_anthology_raw,
        gzip.open(
            f"{builddir}/data-export/anthology.bib.gz", "wt", encoding="utf-8"
        ) as file_anthology,
    ):
        # Add a header to each consolidated bibfile
        for outfh in file_anthology_raw, file_anthology:
            print(
                f"% {config.url_prefix}/{Path(outfh.name).name} generated on {datetime.date.today().isoformat()}\n",
                file=outfh,
            )

        # Add some shortcuts to the uncompressed consolidated bib file
        print(
            "@string{acl = {Association for Computational Linguistics}}",
            file=file_anthology_raw,
        )
        print(f"@string{{anth = {{{config.url_prefix}/}}}}", file=file_anthology_raw)
        print(file=file_anthology_raw)

        for volume_file in track(
            sorted(
                Path(f"{builddir}/data-export/volumes").glob("*.bib"),
                key=lambda p: (infer_year(p.stem), p.stem),
                reverse=True,
            ),
            description="Creating anthology.bib.gz...          ",
        ):
            # reset this each time
            abbrev = None
            volume_id = volume_file.stem

            with open(volume_file, "r") as f:
                bibtex = f.read()
            print(bibtex, file=file_anthology)

            # Space saver (https://github.com/acl-org/acl-anthology/issues/3016) for the
            # uncompressed consolidated bibfile.
            # Replace verbose text with abbreviations to get the file under 50 MB for Overleaf
            concise_contents = bibtex.replace(
                'publisher = "Association for Computational Linguistics",',
                "publisher = acl,",
            )
            concise_contents = re.sub(
                rf'url = "{config.url_prefix}/(.*)"',
                r"url = anth # {\1}",
                concise_contents,
            )

            # Abbreviate the booktitle by extracting it and printing it before
            # the first entry in each volume
            if concise_contents.startswith("@proceedings"):
                # Grab the title string and create the alias
                first_bibkey_comp = re.match(
                    r'@proceedings{([a-z0-9]*)-', concise_contents
                ).group(1)
                abbrev = f"{first_bibkey_comp.upper()}:{infer_year(volume_id)}:{volume_id.split('-')[-1]}"
                try:
                    booktitle = re.match(
                        r"@proceedings{[a-z0-9-]*,\n    title = \"(.*)\",",
                        concise_contents,
                    ).group(1)
                    print(
                        f"@string{{{abbrev} = {{{booktitle}}}}}",
                        file=file_anthology_raw,
                    )
                except AttributeError:
                    log.warning(f"Could not find title for {volume_id}")
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

    with gzip.open(
        f"{builddir}/data-export/anthology+abstracts.bib.gz", "wt", encoding="utf-8"
    ) as file_anthology_with_abstracts:
        for collection_file in track(
            sorted(
                Path(f"{builddir}/data/papers").glob("*.json"),
                key=lambda p: (infer_year(p.stem), p.stem),
                reverse=True,
            ),
            description="Creating anthology+abstracts.bib.gz...",
        ):
            with open(collection_file, "rb") as f:
                data = DECODER.decode(f.read())

                # bibtex = "\n".join(entry["bibtex"] for entry in data.values() if "bibtex" in entry)
                # print(bibtex, file=file_anthology_with_abstracts)

                for entry in data.values():
                    if bibtex := entry.get("bibtex"):
                        print(bibtex, file=file_anthology_with_abstracts)


def convert_bibtex(builddir):
    """Convert BibTeX into other bibliographic formats, and add them to the data files."""
    for collection_file in track(
        list(Path(f"{builddir}/data/papers").glob("*.json")),
        description="Converting to MODS & Endnote...       ",
    ):
        with open(collection_file, "rb") as f:
            data = DECODER.decode(f.read())

        # for entry in data.values():
        #    if bibtex := entry.get("bibtex"):
        #        entry["mods"], entry["endf"] = get_mods_and_endf(bibtex)

        entries = [entry for entry in data.values() if entry.get("bibtex")]
        if not entries:
            continue

        bibtex = "\n".join(entry["bibtex"] for entry in entries)
        mods_batch, endf_batch = batch_convert_to_mods_and_endf(
            bibtex, collection_file.name
        )
        assert len(entries) == len(mods_batch) == len(endf_batch)
        for entry, mods, endf in zip(entries, mods_batch, endf_batch):
            entry["mods"] = mods
            entry["endf"] = endf

        with open(collection_file, "wb") as f:
            f.write(ENCODER.encode(data))


def batch_convert_to_mods_and_endf(bibtex, context):
    mods = subprocess.run(
        ["/usr/bin/bib2xml", "-nt"],
        input=bibtex,
        capture_output=True,
        text=True,
    )
    log.debug(f"{context}: {mods.stderr.strip()}")
    endf = subprocess.run(
        ["/usr/bin/xml2end"],
        input=mods.stdout,
        capture_output=True,
        text=True,
    )
    log.debug(f"{context}: {endf.stderr.strip()}")

    mods_header, *mods_entries = re.split(r"<mods ", mods.stdout)
    mods_header = mods_header.lstrip("\ufeff")
    mods_footer = "</modsCollection>\n"
    mods_batch = [f"{mods_header}{entry}{mods_footer}" for entry in mods_entries[:-1]] + [
        f"{mods_header}{mods_entries[:-1]}"
    ]

    endf_batch = endf.stdout.strip("\ufeff\r\n").split("\n\n")

    return mods_batch, endf_batch


if __name__ == "__main__":
    args = docopt(__doc__)
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    if "{scriptdir}" in args["--builddir"]:
        args["--builddir"] = os.path.abspath(
            args["--builddir"].format(scriptdir=scriptdir)
        )

    log_level = log.DEBUG if args["--debug"] else log.INFO
    tracker = setup_rich_logging(level=log_level)

    create_bibtex(args["--builddir"], clean=args["--clean"])
    convert_bibtex(args["--builddir"])
    if tracker.highest >= log.ERROR:
        exit(1)
