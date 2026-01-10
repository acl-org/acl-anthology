#!/usr/bin/env python3

import re

hashes = []
with open("/tmp/hashes") as f:
    for line in f:
        hashes.append(line.rstrip())

for line in open("2025.wmt.xml"):
    line = line.rstrip()
    if "hash=" in line:
        line = re.sub(r'hash=".*?">', f'hash="{hashes.pop(0)}">', line)

    print(line)
