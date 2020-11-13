#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 Namratha Urs <namrathaurs@my.unt.edu>
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

"""This script is used to add video tags to the Anthology towards ingestion of videos.

Usage:
    add_video_tags.py TSV_files

        where TSV_files are the tab-separated values (TSV) files containing the tuples (anthology_id, presentation_id)

    Consolidates all the TSV files passed to the script, edits the XML by adding a properly-indented video tag to the
    end of the <paper> element and rewrites the XML.
"""

import pandas as pd
import os
import lxml.etree as et
import argparse

from anthology.utils import deconstruct_anthology_id, make_simple_element, indent

root = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(root, "../data/xml")


def combine_tsv(files):
    combined_df = pd.concat(
        [pd.read_csv(os.path.join(root, fname), sep="\t") for fname in files]
    )
    return combined_df


def split_anth_id(anth_id):
    coll_id, _, _ = deconstruct_anthology_id(anth_id)
    return coll_id


def add_video_tag(anth_paper, xml_parse):
    coll_id, vol_id, paper_id = deconstruct_anthology_id(anth_paper.anthology_id)
    paper = xml_parse.find(f'./volume[@id="{vol_id}"]/paper[@id="{paper_id}"]')

    video_url = "http://slideslive.com/{}".format(anth_paper.presentation_id)
    make_simple_element("video", attrib={"tag": "video", "href": video_url}, parent=paper)


def main(args):
    combo_df = combine_tsv(args['tsv_files'])
    combo_df_uniques = combo_df['anthology_id'].apply(split_anth_id).unique()

    for xml in os.listdir(data_dir):
        fname, ext = os.path.splitext(xml)
        if fname in combo_df_uniques.tolist() or fname == "2020.acl":
            tree = et.parse(os.path.join(data_dir, xml))

            df_subset = combo_df[combo_df['anthology_id'].str.startswith(fname)]
            df_subset.apply(add_video_tag, axis=1, xml_parse=tree)

            with open(os.path.join(data_dir, fname + ".xml"), 'wb') as f:
                indent(tree.getroot())
                tree.write(f, encoding="UTF-8", xml_declaration=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Adds video tags to the anthology XML.')
    parser.add_argument(
        'tsv_files',
        nargs='+',
        help='Two-column TSV containing (anthology_id, presentation_id)',
    )

    cl_args = parser.parse_args()
    if cl_args == 0:
        parser.print_help()
    else:
        main(
            vars(cl_args)
        )  # vars converts the argparse's Namespace object to a dictionary
