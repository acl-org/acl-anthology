#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 Xinru Yan <xinru1414@gmail.com>
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
#
# Usage:
#   python -v PATH_TO_VIDEO_DIR -t mp4
#
# Video dir contains a list of videos need to be ingested in .mp4 or .mov format, for example
#
# videos/
#    N13-1001.mp4
#    N13-1002.mp4
#    ...
#
#

import click
import glob
import os
import lxml.etree as et
from typing import List, Tuple
from anthology.utils import deconstruct_anthology_id, make_simple_element, indent

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "../data/xml")


def get_collection_ids(video_dir: str, anth_id_style: str) -> List[str]:
    '''
    Go over all the .mp4 files in the video dir and extract unique collection ids, which will be used to identify xmls that need to be updated.

    param:
    video_dir: directory contains video files, eg: /Users/xinruyan/Dropbox/naacl-2013/
    anth_id_style: str, old anth_id_style example: N13-1001, new anth_id_style example: 2021.emnlp-main.91

    return:
    a list of unique collection ids, eg: ['N13', 'Q13']
    '''
    if anth_id_style == 'old':
        collection_ids = list(
            set(
                [
                    deconstruct_anthology_id(file[len(video_dir) :].split('.')[0])[0]
                    for file in glob.glob(f"{video_dir}/*.mp4")
                ]
            )
        )
    else:
        collection_ids = list(
            set(
                [
                    deconstruct_anthology_id(
                        ('.').join(file[len(video_dir) :].split('.')[:-1])
                    )[0]
                    for file in glob.glob(f"{video_dir}/*.mp4")
                ]
            )
        )
    print(collection_ids)
    return collection_ids


def get_anth_ids(
    video_dir: str, anth_id_style: str, video_type: str
) -> Tuple[List[str], List[List[str]]]:
    '''
    Go over all the .mp4 files in the video dir and extract two types of anthology ids, which will be used to identify papers that needs video tag.

    param:
    video_dir: directory contains video files, eg: /Users/xinruyan/Dropbox/naacl-2013/
    anth_id_style: str, old anth_id_style example: N13-1001, new anth_id_style example: 2021.emnlp-main.91

    return:
    a tuple, (anth_ids_single, anth_ids_multiple),
    anth_ids_single: a list of anth_ids which only has one video to ingest, eg: ['N13-1118', 'N13-1124']
    anth_ids_multiple: a list of list of [anth_ids], [vid_num] which has multiple videos to ingest, eg: [['N13-4001', '1'],['N13-4001', '2'],['N13-4002', '1'],['N13-4002', '2']. vid_num represents the numbered videos.
    '''
    if anth_id_style == 'old':
        anth_ids_single = [
            file[len(video_dir) :].split('.')[0]
            for file in glob.glob(f"{video_dir}/*.{video_type}")
            if len(file[len(video_dir) :].split('.')) == 2
        ]
        anth_ids_multiple = [
            file[len(video_dir) :].split('.')[0:-1]
            for file in glob.glob(f"{video_dir}/*.{video_type}")
            if len(file[len(video_dir) :].split('.')) > 2
        ]
        anth_ids_multiple.sort()
    else:
        anth_ids_single = [
            ('.').join(file[len(video_dir) :].split('.')[:-1])
            for file in glob.glob(f"{video_dir}/*.{video_type}")
        ]
        # for new anth_id_style, each anth_id can only have one video
        anth_ids_multiple = []
    return anth_ids_single, anth_ids_multiple


def add_video_tag_single(anth_id, xml_parse, video_type: str):
    '''
    Add video tag for paper f'{anth_id}'
    '''
    collection_id, volume_id, paper_id = deconstruct_anthology_id(anth_id)
    paper = xml_parse.find(f'./volume[@id="{volume_id}"]/paper[@id="{paper_id}"]')
    video_url = anth_id + f'.{video_type}'

    if video_url not in [video.attrib["href"] for video in paper.iter("video")]:
        make_simple_element('video', attrib={'href': video_url}, parent=paper)


def add_video_tag_multiple(anth_id, vid_num, xml_parse, video_type: str):
    '''
    Add video tag for paper f`{anth_id}` with multiple number of videos
    Adapted from add_video_tags.py
    '''
    collection_id, volume_id, paper_id = deconstruct_anthology_id(anth_id)
    paper = xml_parse.find(f'./volume[@id="{volume_id}"]/paper[@id="{paper_id}"]')
    video_url = anth_id + f'.{vid_num}' + f'.{video_type}'
    make_simple_element("video", attrib={"href": video_url}, parent=paper)


def update_xml(data_dir, collection_id, extention, xml_tree):
    '''
    Update xml
    Adapted from add_video_tags.py
    '''
    with open(os.path.join(data_dir, collection_id + extention), 'wb') as f:
        indent(xml_tree.getroot())
        xml_tree.write(f, encoding="UTF-8", xml_declaration=True)


@click.command()
@click.option(
    '-v',
    '--video_dir',
    help='Directory contains all videos need to be ingested',
)
@click.option(
    '-s',
    '--anth_id_style',
    default='new',
    help='Anthology ID style used in the video file names',
)
@click.option(
    '-t',
    '--video_type',
    default='mp4',
    help='mp4 or mov file',
)
def main(video_dir, anth_id_style, video_type):
    collection_ids = get_collection_ids(video_dir=video_dir, anth_id_style=anth_id_style)

    xml_files = [
        file
        for file in os.listdir(DATA_DIR)
        if os.path.splitext(file)[0] in collection_ids
    ]

    anth_ids_single, anth_ids_multiple = get_anth_ids(
        video_dir=video_dir, anth_id_style=anth_id_style, video_type=video_type
    )

    for file in xml_files:
        collection_id, extention = os.path.splitext(file)
        tree = et.parse(os.path.join(DATA_DIR, file))
        for anth_id in anth_ids_single:
            if collection_id in anth_id:
                add_video_tag_single(
                    anth_id=anth_id, xml_parse=tree, video_type=video_type
                )
                update_xml(
                    data_dir=DATA_DIR,
                    collection_id=collection_id,
                    extention=extention,
                    xml_tree=tree,
                )

        for anth_id_vid_num in anth_ids_multiple:
            anth_id = anth_id_vid_num[0]
            vid_num = anth_id_vid_num[1]
            if collection_id in anth_id:
                add_video_tag_multiple(anth_id=anth_id, vid_num=vid_num, xml_parse=tree)
                update_xml(
                    data_dir=DATA_DIR,
                    collection_id=collection_id,
                    extention=extention,
                    xml_tree=tree,
                )


if __name__ == '__main__':
    main()
