#!/usr/bin/env python3
"""Fix reversed author names in 2023.ccl.xml.

Based on https://github.com/acl-org/acl-anthology/issues/5786 and
https://github.com/acl-org/acl-anthology/issues/7520

Per chnln's analysis:
- Volume 3 (Evaluations): all good
- Volume 2 (Frontier forums) and 4 (Tutorials): English papers reversed;
  Chinese papers with variant script="latn" also reversed
- Volume 1: English papers reversed; Chinese papers 37, 46, 48, 49
  (those with variant script="latn") also reversed
"""

import re
import xml.etree.ElementTree as ET

XML_PATH = "data/xml/2023.ccl.xml"

# First pass: get language for each (volume_id, paper_id)
tree = ET.parse(XML_PATH)
root = tree.getroot()

paper_languages = {}
for volume in root.findall("volume"):
    vol_id = volume.get("id")
    for paper in volume.findall("paper"):
        paper_id = paper.get("id")
        lang_elem = paper.find("language")
        if lang_elem is not None:
            paper_languages[(vol_id, paper_id)] = lang_elem.text

# Papers to swap (by volume, paper id)
# Volume 1: English papers 50-78; Chinese papers 37, 46, 48, 49
# Volume 2: English papers 2, 4, 8, 9; Chinese paper 7
# Volume 4: English papers 2, 3, 4; Chinese paper 1
# Volume 3: nothing

SWAP_CHINESE_PAPERS = {
    "1": {37, 46, 48, 49},
    "2": {7},
    "4": {1},
}

SKIP_AUTHOR_IDS = {"chao-zhang-cambridge"}

# Second pass: line-by-line processing
with open(XML_PATH, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
current_volume = None
current_paper = None

swap_count = 0
output_lines = []

for line in lines:
    # Track volume
    vol_match = re.match(r"\s*<volume id=\"(\d+)\"", line)
    if vol_match:
        current_volume = vol_match.group(1)

    if re.match(r"\s*</volume>", line):
        current_volume = None

    # Track paper
    paper_match = re.match(r"\s*<paper id=\"(\d+)\"", line)
    if paper_match:
        current_paper = paper_match.group(1)

    if re.match(r"\s*</paper>", line):
        current_paper = None

    # Determine if we should swap this author line
    should_swap = False

    if current_volume and current_paper and "<author" in line and "<first>" in line:
        paper_num = int(current_paper)
        language = paper_languages.get((current_volume, current_paper))

        if current_volume in ("1", "2", "4"):
            if language == "eng":
                should_swap = True
            elif language == "zho":
                chinese_papers = SWAP_CHINESE_PAPERS.get(current_volume, set())
                if paper_num in chinese_papers:
                    should_swap = True

    if should_swap:
        # Check if this author should be skipped (already correct)
        skip = any(f'id="{aid}"' in line for aid in SKIP_AUTHOR_IDS)

        if not skip:
            # Swap <first> and <last> in the MAIN author tag only (not in variant)
            variant_pos = line.find("<variant")
            if variant_pos == -1:
                # No variant tag
                work_part = line
                rest_part = ""
            else:
                work_part = line[:variant_pos]
                rest_part = line[variant_pos:]

            match = re.search(r"(<first>)(.*?)(</first><last>)(.*?)(</last>)", work_part)
            if match:
                old_first = match.group(2)
                old_last = match.group(4)
                work_part = (
                    work_part[: match.start()]
                    + match.group(1)
                    + old_last
                    + match.group(3)
                    + old_first
                    + match.group(5)
                    + work_part[match.end() :]
                )
                swap_count += 1

            line = work_part + rest_part

    output_lines.append(line)

with open(XML_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"Swapped {swap_count} author names.")
