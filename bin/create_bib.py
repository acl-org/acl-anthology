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

"""Usage: create_bib.py [--builddir=DIR] [-c] [--max-workers=N] [--debug]

Creates anthology.bib files and MODS/Endnote formats for all papers in the Hugo directory.

Options:
  --builddir=DIR           Directory with build files; used both for reading and writing. [default: {scriptdir}/../build/]
  --debug                  Output debug-level log messages.
  -c, --clean              Delete existing files in target directory before generation.
  -n, --max-workers=N      Maximum number of subprocesses that will be spawned.
  -h, --help               Display this helpful text.
"""

import concurrent.futures
import datetime
from docopt import docopt
import gzip
import logging as log
import os
import msgspec
from pathlib import Path
import re
from rich.progress import track
import shutil
import subprocess

from acl_anthology import config
from acl_anthology.utils.ids import infer_year
from acl_anthology.utils.logging import setup_rich_logging
from create_hugo_data import make_progress


BIB2XML = None
XML2END = None


def create_bibtex(builddir, clean=False) -> None:
    """Create full Anthology BibTeX files.

    Requires volume bib files from create_hugo_data.py (for file without abstracts).
    Requires data files from create_hugo_data.py (for file with abstracts).
    """
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
            description="Create anthology.bib.gz...  ",
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
            description="       +abstracts.bib.gz... ",
        ):
            with open(collection_file, "rb") as f:
                data = msgspec.json.decode(f.read())

                # bibtex = "\n".join(entry["bibtex"] for entry in data.values() if "bibtex" in entry)
                # print(bibtex, file=file_anthology_with_abstracts)

                for entry in data.values():
                    if bibtex := entry.get("bibtex"):
                        print(bibtex, file=file_anthology_with_abstracts)


def convert_bibtex(builddir, max_workers=None):
    """Convert BibTeX into other bibliographic formats, and add them to the data files.

    Requires data files from create_hugo_data.py.
    """
    files = list(Path(f"{builddir}/data/papers").glob("*.json"))

    with make_progress() as progress:
        task = progress.add_task("Convert to MODS & Endnote...", total=len(files))

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(convert_collection_file, file) for file in files]
            for _ in concurrent.futures.as_completed(futures):
                progress.update(task, advance=1)


def convert_collection_file(collection_file):
    """Read a single collection data file, convert its BibTeX entries to MODS and Endnote formats, and save those back into the file.

    Important:
        This function should not rely on global objects, as it will be executed concurrently for different files with multiprocessing.
    """

    with open(collection_file, "rb") as f:
        data = msgspec.json.decode(f.read())

    entries = [entry for entry in data.values() if entry.get("bibtex")]
    if not entries:
        return

    bibtex = "\n".join(entry["bibtex"] for entry in entries)
    mods_batch, endf_batch = batch_convert_to_mods_and_endf(bibtex, collection_file.name)
    assert len(entries) == len(mods_batch) == len(endf_batch)
    for entry, mods, endf in zip(entries, mods_batch, endf_batch):
        entry["mods"] = mods
        entry["endf"] = endf

    with open(collection_file, "wb") as f:
        f.write(msgspec.json.encode(data))


def batch_convert_to_mods_and_endf(bibtex, context):
    """Convert a BibTeX string with multiple entries to MODS and Endnote.

    Relies on bibutils to perform the conversion, then returns a list with the individual converted entries.
    """
    mods = subprocess.run(
        [BIB2XML, "-nt"],
        input=bibtex,
        capture_output=True,
        text=True,
    )
    log.debug(f"{context}: {mods.stderr.strip()}")
    endf = subprocess.run(
        [XML2END],
        input=mods.stdout,
        capture_output=True,
        text=True,
    )
    log.debug(f"{context}: {endf.stderr.strip()}")

    mods_header, *mods_entries = re.split(r"<mods ", mods.stdout)
    mods_header = mods_header.lstrip("\ufeff")
    mods_footer = "</modsCollection>\n"
    mods_batch = [
        f"{mods_header}<mods {entry}{mods_footer}" for entry in mods_entries[:-1]
    ] + [f"{mods_header}<mods {mods_entries[-1]}"]

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

    max_workers = int(args["--max-workers"]) if args["--max-workers"] else None
    if (BIB2XML := shutil.which("bib2xml")) is None:
        log.error("bib2xml not found; please install bibutils for MODS XML conversion")
    if (XML2END := shutil.which("xml2end")) is None:
        log.error("xml2end not found; please install bibutils for Endnote conversion")

    create_bibtex(args["--builddir"], clean=args["--clean"])
    if BIB2XML and XML2END:
        convert_bibtex(args["--builddir"], max_workers=max_workers)

    if tracker.highest >= log.ERROR:
        exit(1)
