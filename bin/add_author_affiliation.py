#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021, 2022 Xinru Yan <xinru1414@gmail.com>
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
#   python bin/add_author_affiliation.py -i ~/Dropbox/ingests/2023/01-17-emnlp/main/output/ -x data/xml/2022.emnlp.xml -v main
#
#
#
import click
import lxml.etree as et
from ingest_aclpub2 import parse_paper_yaml
from anthology.utils import make_simple_element
from typing import Dict, List, Optional


def find_paper(papers: List[Dict], first_name: str, last_name: str) -> Optional[str]:
    for paper in papers:
        for author in paper['authors']:
            if author['first_name'] == first_name and author['last_name'] == last_name:
                if 'Affiliation' in author.keys():
                    return author['Affiliation']
                else:
                    print(
                        f"{paper['title']} author {author['first_name']} {author['last_name']} does not provide affiliation"
                    )
                    return 'NA'
    return 'NA'


def add_author_affiliation(xml_file, volume_name, papers: List[Dict]):
    tree = et.parse(xml_file)
    root = tree.getroot()
    for volume in root.iter('volume'):
        if volume.attrib.get('id') == volume_name:
            for paper in volume.iter('paper'):
                for author in paper.iter('author'):
                    first_name, last_name = (
                        author.find('first').text,
                        author.find('last').text,
                    )
                    assert first_name is not None, 'first name is none'
                    assert last_name is not None, 'last name is none'
                    affi = find_paper(papers, first_name, last_name)
                    # print(f'affi is {affi}')
                    make_simple_element('affiliation', affi, parent=author)
    tree.write(xml_file, encoding='UTF-8', xml_declaration=True, with_tail=True)


@click.command()
@click.option(
    '-i',
    '--ingestion_dir',
    help='Directory contains proceedings need to be ingested, which includes the papers.yml file',
)
@click.option(
    '-x',
    '--xml_file',
    default='data/xml/2022.emnlp.xml',
    help='xml file that needs author affiliation info ingested',
)
@click.option(
    '-v',
    '--volume',
    default='main',
    help='volume that needs author affiliation info ingested',
)
def main(ingestion_dir, xml_file, volume):
    papers = parse_paper_yaml(ingestion_dir)
    add_author_affiliation(xml_file, volume, papers)


if __name__ == '__main__':
    main()
