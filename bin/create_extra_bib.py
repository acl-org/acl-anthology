#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2026 Marcel Bollmann <marcel@bollmann.me>
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

"""Usage: create_extra_bib.py [--builddir=DIR] [-c] [--max-workers=N] [--debug]

Creates full Anthology BibTeX files and MODS/Endnote formats for all papers in the Hugo directory.

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
import multiprocessing
from pathlib import Path
import re
from rich.console import Console
from rich.progress import track
import shutil
import subprocess


from acl_anthology import config
from acl_anthology.utils.ids import infer_year
from acl_anthology.utils.logging import setup_rich_logging
from create_hugo_data import make_progress

BIB2XML = None
XML2END = None
CONSOLE = Console(stderr=True)

# Max shard size in MiB
MAX_SHARD_MB = 49


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
        ) as file_anthology_gzip,
    ):
        # Add a header to each consolidated bibfile
        for outfh in file_anthology_raw, file_anthology_gzip:
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
            console=CONSOLE,
        ):
            with open(volume_file, "r") as f:
                bibtex = f.read()

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

            # Remove whitespace to save space and keep things under 50 MB
            concise_contents = re.sub(r",\n +", ",", concise_contents)
            concise_contents = re.sub(r"  and\n +", " and ", concise_contents)
            concise_contents = re.sub(r",?\n}", "}", concise_contents)

            print(concise_contents, file=file_anthology_raw)
            print(bibtex, file=file_anthology_gzip)

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
            console=CONSOLE,
        ):
            with open(collection_file, "rb") as f:
                data = msgspec.json.decode(f.read())

                # bibtex = "\n".join(entry["bibtex"] for entry in data.values() if "bibtex" in entry)
                # print(bibtex, file=file_anthology_with_abstracts)

                for entry in data.values():
                    if bibtex := entry.get("bibtex"):
                        print(bibtex, file=file_anthology_with_abstracts)


# filepath: /Users/mattpost/src/acl-anthology/bin/create_extra_bib.py
def create_shards(
    builddir: str, max_shard_mb: int = MAX_SHARD_MB, prefix: str = "anthology"
) -> None:
    """Split data-export/<prefix>.bib into numbered shards each <= max_shard_mb MiB."""
    max_bytes = int(max_shard_mb * 1024 * 1024)
    bib_path = Path(f"{builddir}/data-export/{prefix}.bib")
    if not bib_path.exists():
        log.warning(f"{bib_path} not found; skipping shard generation")
        return

    with bib_path.open(encoding="utf-8") as f:
        header = f.readline()
        entries_text = f.read()

    # Split entries at each next line starting with '@' (preserves the leading '@')
    entries = re.split(r"(?=@[A-Za-z]+)", entries_text)
    entries = [e.strip() for e in entries if e.strip()]

    if not entries:
        log.warning(f"No entries parsed from {bib_path}; skipping shards")
        return

    shards = []
    current_shard = []
    header_bytes_len = len(header.encode("utf-8"))
    current_size = header_bytes_len

    for entry in entries:
        entry_bytes = (entry + "\n").encode("utf-8")
        # Close current shard if this entry would overflow it
        if current_shard and (current_size + len(entry_bytes) > max_bytes):
            shards.append(current_shard)
            current_shard = []
            current_size = header_bytes_len

        # Warn if a single entry is larger than the shard limit
        if not current_shard and len(entry_bytes) > max_bytes:
            log.warning(
                f"Single BibTeX entry exceeds {max_shard_mb} MiB; it will occupy a single shard."
            )

        current_shard.append(entry)
        current_size += len(entry_bytes)

    if current_shard:
        shards.append(current_shard)

    def extract_year(entry: str):
        """Extract the year from a string containing a BibTeX entry containing field year = "XXXX"."""
        match = re.search(r'year = "(\d{4})"', entry)
        return int(match.group(1)) if match else None

    # Write shards with header + shard list comment
    shard_filenames = [f"{prefix}-{i}.bib" for i in range(1, len(shards) + 1)]
    shard_ranges = []
    for shard_entries in shards:
        # entries may be missing the year, so search from the front and
        # back until we have one for the range
        for e in shard_entries:
            top_year = extract_year(e)
            if top_year:
                break
        for e in reversed(shard_entries):
            bottom_year = extract_year(e)
            if bottom_year:
                break

        shard_ranges.append(
            f"{bottom_year}-{top_year}" if top_year and bottom_year else ""
        )

    shard_header_lines = [
        "% This file is one of multiple shards of the consolidated anthology.bib file.",
        "% The shards have been created to fit under size limits.",
        "%",
    ]
    for fname, yr in zip(shard_filenames, shard_ranges):
        shard_header_lines.append(f"% - {config.url_prefix}/{fname} ({yr})")
    shard_header = "\n".join(shard_header_lines)

    # Write shards with header + shard list comment
    for i, shard_entries in enumerate(shards, start=1):
        out_path = bib_path.with_name(f"{prefix}-{i}.bib")
        with open(out_path, "wt", encoding="utf-8") as fh:
            fh.write(shard_header + "\n%\n")
            fh.write("% Original file:\n")
            fh.write(header.strip() + "\n\n")
            fh.write("\n".join(shard_entries))
            fh.write("\n")

    log.info(
        f"Wrote {len(shards)} shards for {bib_path.name}: {', '.join(shard_filenames)}"
    )


def convert_bibtex(builddir, max_workers=None):
    """Convert BibTeX into other bibliographic formats, for both data files and volume-level bibliography files.

    Requires data files from create_hugo_data.py.
    """
    data_files = list(Path(f"{builddir}/data/papers").glob("*.json"))
    bib_files = list(Path(f"{builddir}/data-export/volumes").glob("*.bib"))

    with make_progress() as progress:
        task = progress.add_task(
            "Convert to MODS & Endnote...", total=len(data_files) + len(bib_files)
        )

        if max_workers == 1:
            # Mainly for debugging purposes
            for file in data_files:
                convert_collection_file(file)
                progress.update(task, advance=1)
            for file in bib_files:
                convert_volume_bib_file(file)
                progress.update(task, advance=1)
        else:
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=max_workers, mp_context=multiprocessing.get_context("fork")
            ) as executor:
                futures = [
                    executor.submit(convert_collection_file, file) for file in data_files
                ] + [executor.submit(convert_volume_bib_file, file) for file in bib_files]
                for future in concurrent.futures.as_completed(futures):
                    progress.update(task, advance=1)
                    if (exc := future.exception()) is not None:
                        log.exception(exc)


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


def convert_volume_bib_file(volume_bib_file):
    """Read a single volume bib file, and convert it to MODS and Endnote formats.

    Important:
        This function should not rely on global objects, as it will be executed concurrently for different files with multiprocessing.
    """

    volume_mods_file = volume_bib_file.with_suffix(".xml")
    volume_endf_file = volume_bib_file.with_suffix(".enw")

    with open(volume_bib_file, "rb") as bib, open(volume_mods_file, "wb") as mods:
        subprocess.run(
            [BIB2XML, "-nt"],
            stdin=bib,
            stdout=mods,
            stderr=subprocess.PIPE,
            check=True,
        )
    with open(volume_mods_file, "rb") as mods, open(volume_endf_file, "wb") as endf:
        subprocess.run(
            [XML2END],
            stdin=mods,
            stdout=endf,
            stderr=subprocess.PIPE,
            check=True,
        )


def batch_convert_to_mods_and_endf(bibtex, context):
    """Convert a BibTeX string with multiple entries to MODS and Endnote.

    Relies on bibutils to perform the conversion, then returns a list with the individual converted entries.
    """
    mods = subprocess.run(
        [BIB2XML, "-nt"],
        input=bibtex,
        capture_output=True,
        text=True,
        check=True,
    )
    log.debug(f"{context}: {mods.stderr.strip()}")
    endf = subprocess.run(
        [XML2END],
        input=mods.stdout,
        capture_output=True,
        text=True,
        check=True,
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
    tracker = setup_rich_logging(console=CONSOLE, level=log_level)

    max_workers = int(args["--max-workers"]) if args["--max-workers"] else None
    if (BIB2XML := shutil.which("bib2xml")) is None:
        log.error("bib2xml not found; please install bibutils for MODS XML conversion")
    if (XML2END := shutil.which("xml2end")) is None:
        log.error("xml2end not found; please install bibutils for Endnote conversion")

    create_bibtex(args["--builddir"], clean=args["--clean"])
    # Generate chunked shards in addition to the consolidated file
    create_shards(args["--builddir"], max_shard_mb=MAX_SHARD_MB, prefix="anthology")

    if BIB2XML and XML2END:
        convert_bibtex(args["--builddir"], max_workers=max_workers)

    if tracker.highest >= log.ERROR:
        exit(1)
