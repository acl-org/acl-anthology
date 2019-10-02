#!/usr/bin/env python3

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
