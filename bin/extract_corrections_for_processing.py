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
Extracts attachments from the CSV output of our Attachments form at
https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAMAABqTSThUN0I2VEdZMTk4Sks3S042MVkxUEZQUVdOUS4u .
Each extracted line can then be passed directly to ./add_attachment.py as arguments for ingestion.

e.g.,

    cat attachments.csv | ./extract_attachments_from_csv.py > attachments.txt
    for line in $(grep -vi correction attachments.txt); do
      ./add_attachment.py $line
    done

Author: Matt Post
"""

import csv
import os
import sys

from anthology.utils import is_valid_id

def main(args):

    for row in csv.DictReader(args.csv_file):
#    ID,Start time,Completion time,Email,Name,Anthology ID,URL,Type,Explanation,Name,Email,License

        anthology_id = row["Anthology ID"].strip()
        download_path = row["URL where we can download the attachment"]
        attachment_type = row["Attachment type"]
        submitter_name = row["Your name"]
        submitter_email = row["Your email address"]
        submitted = row["Completion time"]
        explanation = row["For corrections or errata, please explain in detailed prose what has changed."]

        if attachment_type not in ["Correction", "Erratum"]:
            continue

        if not is_valid_id(anthology_id):
            print(f"Bad anthology ID {anthology_id}", file=sys.stderr)

        outdir = os.path.join("corrections")
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        with open(os.path.join(outdir, f"{anthology_id}.txt"), "w") as out:
            print(f'{anthology_id} "{download_path}" "{explanation}"', file=out)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=argparse.FileType("r"))
    args = parser.parse_args()

    main(args)
