#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Matt Post <post@cs.jhu.edu>
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

"""
Extracts corrections from the CSV output of our Attachments form at
https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAMAABqTSThUN0I2VEdZMTk4Sks3S042MVkxUEZQUVdOUS4u .
Each extracted line can then be passed directly to ./add_revision.py as arguments for ingestion.

e.g.,

    cat attachments.csv | ./extract_corrections_for_processing.py
    for file in corrections/*; do
      add_revision.py $(cat $file)
    done

Author: Matt Post
"""

import csv
import os
import sys

from anthology.utils import is_valid_id
from datetime import datetime


def main(args):

    for row in csv.DictReader(args.csv_file):
        #    ID,Start time,Completion time,Email,Name,Anthology ID,URL,Type,Explanation,Name,Email,License

        anthology_id = row["Anthology ID"].strip()
        download_path = row["URL"]
        attachment_type = row["Attachment type"]
        submitter_name = row["Your name"]
        submitter_email = row["Your email address"]
        submitted = row["Completion time"]
        explanation = row["Explanation"]

        date = datetime.strptime(submitted.split()[0], "%m/%d/%y").date().isoformat()

        if attachment_type not in ["Correction", "Erratum"]:
            print(f"Skipping {anthology_id} (type={attachment_type})", file=sys.stderr)
            continue

        if not is_valid_id(anthology_id):
            print(f"Bad anthology ID {anthology_id}", file=sys.stderr)

        outdir = os.path.join("corrections")
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        outfile = os.path.join(outdir, f"{anthology_id}.txt")
        if os.path.exists(outfile):
            print(
                f"* Refusing to overwrite existing file {outfile}, skipping",
                file=sys.stderr,
            )
            continue
        else:
            with open(outfile, "w") as out:
                erratum_flag = '' if attachment_type == 'Correction' else '-e '
                print(
                    f'{erratum_flag}{anthology_id} -d {date} "{download_path}" "{explanation}"',
                    file=out,
                )
                print(f"Wrote line for {anthology_id} to {outfile}", file=sys.stderr)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=argparse.FileType("r"))
    args = parser.parse_args()

    main(args)
