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
import sys

reader = csv.reader(sys.stdin)
header = list(next(reader))

for row in reader:
    anthology_id, url, attach_type = row[5:8]
    if not (url.endswith('.pdf') or url.endswith('.pptx')):
        print(f'{anthology_id} bad {attach_type} {url}', file=sys.stderr)
    print(anthology_id, url, attach_type, sep='\t')
