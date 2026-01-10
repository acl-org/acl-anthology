#!/usr/bin/env python3
# -*- coding: utf-8  -*-
#
# Copyright 2022 Matt Post <post@cs.jhu.edu>
# Modified for author page splitting by paper ID list
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
Adds an ID tag to specific author instances in specific papers based on Anthology IDs,
or adds an ID to all OTHER instances not in a specified list.

Usage for specific papers:
    ./add_author_id_by_papers.py zhiyu-chen-lehigh --last-name Chen --papers 2025.acl-long.641 2024.emnlp-industry.42

Usage for all EXCEPT specific papers:
    ./add_author_id_by_papers.py zhiyu-chen --last-name Chen --exclude-papers 2025.acl-long.641 2024.emnlp-industry.42
"""

import argparse
import os

from anthology.utils import indent
from itertools import chain

import lxml.etree as ET


def parse_anthology_id(anthology_id):
    """Parse anthology ID to get collection and paper ID."""
    # Examples: 
    # 2024.acl-long.295 -> collection=2024.acl, paper_id=295
    # 2023.findings-emnlp.134 -> collection=2023.findings, paper_id=134
    # 2024.lrec-main.533 -> collection=2024.lrec, paper_id=533
    
    parts = anthology_id.split('.')
    if len(parts) >= 3:
        year = parts[0]
        venue_volume = parts[1]  # e.g., "acl-long", "findings-emnlp", "lrec-main"
        paper_id = parts[2]  # Just the numeric paper ID
        
        # Extract base venue for collection name
        if '-' in venue_volume:
            venue = venue_volume.split('-')[0]
            if venue_volume.startswith('findings-'):
                collection = f"{year}.findings"
            else:
                collection = f"{year}.{venue}"
        else:
            collection = f"{year}.{venue_volume}"
    else:
        # Handle legacy format
        collection = anthology_id.split('-')[0] if '-' in anthology_id else anthology_id[:-4]
        paper_id = anthology_id.split('-')[-1] if '-' in anthology_id else anthology_id[-4:]
    
    return collection, paper_id


def main(args):
    # Parse paper list
    target_papers = set()
    
    if args.papers:
        target_papers.update(args.papers)
    
    if args.exclude_papers:
        target_papers.update(args.exclude_papers)
    
    if args.papers_file:
        with open(args.papers_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    target_papers.add(line)
    
    exclude_mode = bool(args.exclude_papers)
    
    if target_papers:
        print(f"Target papers: {sorted(target_papers)}")
        print(f"Mode: {'EXCLUDE' if exclude_mode else 'INCLUDE'} these papers")
    
    # Group papers by collection
    collections = {}
    for paper in target_papers:
        collection, paper_id = parse_anthology_id(paper)
        if collection not in collections:
            collections[collection] = set()
        collections[collection].add(paper_id)
    
    # Process each XML file
    for xml_file in os.listdir(args.data_dir):
        if not xml_file.endswith(".xml"):
            continue
            
        base_name = xml_file[:-4]  # Remove .xml
        changed_one = False
        tree = ET.parse(os.path.join(args.data_dir, xml_file))
        
        for paper_xml in chain(
            tree.getroot().findall(".//paper"), tree.getroot().findall(".//meta")
        ):
            paper_id = paper_xml.attrib.get("id", "0")
            
            # Check if this paper should be processed
            should_process = True
            if target_papers:
                is_target_paper = (base_name in collections and paper_id in collections[base_name])
                if exclude_mode:
                    should_process = not is_target_paper  # Process everything EXCEPT target papers
                else:
                    should_process = is_target_paper      # Process ONLY target papers
            
            if not should_process:
                continue
                
            for author_xml in chain(
                paper_xml.findall("./author"), paper_xml.findall("./editor")
            ):
                if "id" in author_xml.attrib:
                    continue
                    
                last_name_elem = author_xml.find("./last")
                if last_name_elem is None:
                    continue
                    
                last_name = last_name_elem.text
                if last_name == args.last_name:
                    # Also check first name if specified
                    if args.first_name:
                        first_name_elem = author_xml.find("./first")
                        if first_name_elem is None or first_name_elem.text != args.first_name:
                            continue
                    
                    anth_id = f"{base_name}.{paper_id}"
                    print(f"    Adding {args.id} to {anth_id} for {args.first_name or ''} {last_name}")
                    author_xml.attrib["id"] = args.id
                    changed_one = True

        if changed_one:
            indent(tree.getroot())
            tree.write(os.path.join(args.data_dir, xml_file), encoding="UTF-8", xml_declaration=True)
            print(f"  Updated {xml_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("id", help="Author ID to add")
    parser.add_argument("--last-name", required=True, help="Author's last name")
    parser.add_argument("--first-name", help="Author's first name (optional, for additional filtering)")
    parser.add_argument("--papers", nargs="+", help="List of Anthology IDs to INCLUDE (e.g., 2025.acl-long.641)")
    parser.add_argument("--exclude-papers", nargs="+", help="List of Anthology IDs to EXCLUDE (tag all others)")
    parser.add_argument("--papers-file", help="File containing list of Anthology IDs, one per line")
    parser.add_argument(
        "--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data", "xml")
    )
    args = parser.parse_args()

    main(args)
