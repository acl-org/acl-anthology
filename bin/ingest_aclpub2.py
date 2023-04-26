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
#   python bin/ingest_aclpub2.py
#
#
#
import click
import yaml
import re
import sys
import os
import glob
import PyPDF2
from pathlib import Path
from datetime import datetime
import lxml.etree as etree
from typing import Dict, List, Tuple, Any, Optional
from ingest import maybe_copy

from normalize_anth import normalize
from anthology.index import AnthologyIndex
from anthology.venues import VenueIndex
from anthology.people import PersonName
from anthology.utils import (
    make_simple_element,
    indent,
    compute_hash_from_file,
)


def disambiguate_name(node, anth_id, people):
    name = PersonName.from_element(node)
    ids = people.get_ids(name)
    choice = -1
    if len(ids) > 1:
        while choice < 0 or choice >= len(ids):
            print(
                f'({anth_id}): ambiguous author {name}; Please choose from the following:'
            )
            for i, id_ in enumerate(ids):
                print(f'[{i}] {id_} ({people.get_comment(id_)})')
            choice = int(input("--> "))

    return ids[choice], choice


def correct_caps(name):
    '''
    Many people submit their names in "ALL CAPS" or "all lowercase".
    Correct this with heuristics.
    '''
    if name.islower() or name.isupper():
        # capitalize all parts
        corrected = " ".join(list(map(lambda x: x.capitalize(), name.split())))
        print(
            f"-> Correcting capitalization of '{name}' to '{corrected}'",
            file=sys.stderr,
        )
        name = corrected
    return name


def parse_conf_yaml(ingestion_dir: str) -> Dict[str, Any]:
    '''
    poss meta keys = [
                 'book_title',
                 'event_name',
                 'cover_subtitle',
                 'anthology_venue_id',
                 'volume',
                 'start_date',
                 'end_date',
                 'isbn',
                 'location',
                 'editors',
                 'publisher'
                 ]
    must meta keys = [
                 'book_title',
                 'anthology_venue_id',
                 'volume_name',
                 'month',
                 'year',
                 'location',
                 'editors',
                 'publisher'
                ]

    anthology_venue_id == abbrev
    event_name == title
    cover_subtitle == shortbooktitle
    '''
    if os.path.exists(Path(ingestion_dir + 'inputs/conference_details.yml')):
        meta = yaml.safe_load(
            Path(ingestion_dir + 'inputs/conference_details.yml').read_text()
        )
    else:
        meta = yaml.safe_load(
            Path(ingestion_dir + 'input/conference_details.yml').read_text()
        )
    meta['month'] = meta['start_date'].strftime('%B')
    meta['year'] = str(meta['start_date'].year)

    must_have_keys = [
        'book_title',
        'anthology_venue_id',
        'volume_name',
        'month',
        'year',
        'location',
        'editors',
        'publisher',
        'event_name',
    ]
    for key in must_have_keys:
        assert key in meta.keys(), f'{key} is missing in the conference_details.yml file'

    meta['volume_name'] = str(meta['volume_name'])
    if re.match(r'^[a-z0-9]+$', meta['volume_name']) is None:
        raise Exception(
            f"Invalid volume key '{meta['volume_name']}' in {ingestion_dir + 'inputs/conference_details.yml'}"
        )

    return meta


def parse_paper_yaml(ingestion_dir: str) -> List[Dict[str, str]]:
    if os.path.exists(Path(ingestion_dir + 'inputs/conference_details.yml')):
        papers = yaml.safe_load(Path(ingestion_dir + 'inputs/papers.yml').read_text())
    else:
        papers = yaml.safe_load(Path(ingestion_dir + 'input/papers.yml').read_text())
    return papers


def add_paper_nums_in_paper_yaml(
    papers: List[Dict[str, str]], ingestion_dir: str
) -> List[Dict[str, str]]:
    start, end = 1, 0
    for paper in papers:
        if 'archival' not in paper.keys():
            paper.update({'archival': '1'})
        assert 'archival' in paper.keys(), f'{paper["id"]} is missing key archival'
        assert 'file' in paper.keys(), f'{paper["id"]} is missing key file'
        if (
            paper['archival'] == 1
            or paper['archival'] is True
            or paper['archival'] == '1'
        ):
            paper_id = str(paper['id'])
            # if 'file' not in paper.keys():
            #     print(f'{paper_id} does not have file key but archive is {paper["archival"]}')
            #     paper_name = paper['title']
            # else:
            paper_name = paper['file']
            if os.path.exists(f'{ingestion_dir}inputs/papers/{paper_id}.pdf'):
                paper_need_read_path = f'{ingestion_dir}inputs/papers/{paper_id}.pdf'
            elif os.path.exists(f'{ingestion_dir}input/papers/{paper_id}.pdf'):
                paper_need_read_path = f'{ingestion_dir}input/papers/{paper_id}.pdf'
            elif os.path.exists(f'{ingestion_dir}inputs/papers/{paper_name}'):
                paper_need_read_path = f'{ingestion_dir}inputs/papers/{paper_name}'
            elif os.path.exists(f'{ingestion_dir}input/papers/{paper_name}'):
                paper_need_read_path = f'{ingestion_dir}input/papers/{paper_name}'
            else:
                paper_need_read_path = None
            assert paper_need_read_path, f'{paper_id} path is None'
            pdf = open(paper_need_read_path, 'rb')
            pdf_reader = PyPDF2.PdfReader(pdf)
            num_of_pages = len(pdf_reader.pages)
            start = end + 1
            end = start + num_of_pages - 1
            paper['pages'] = f'{start}-{end}'
    return papers


def create_des_path(org_dir_name: str, venue_name: str) -> str:
    dest_dir = os.path.join(org_dir_name, venue_name)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    return dest_dir


def find_paper_attachment(paper_name: str, attachments_dir: str) -> Optional[str]:
    '''
    files in the attachments folder need to be named filename.zip
    '''
    attachment_path = None
    for filename in glob.glob(attachments_dir + '/*'):
        if os.path.splitext(os.path.split(filename)[1])[0] == paper_name:
            attachment_path = filename
            break
    return attachment_path


def proceeding2xml(anthology_id: str, meta: Dict[str, Any]):
    fields = [
        'editor',
        'booktitle',
        'month',
        'year',
        'url',
    ]
    paper = make_simple_element('paper', attrib={'id': '0'})
    for field in fields:
        if field == 'editor':
            authors = meta['editors']
            for author in authors:
                name_node = make_simple_element(field, parent=paper)
                make_simple_element('first', author['first_name'], parent=name_node)
                make_simple_element('last', author['last_name'], parent=name_node)
                # add affiliation
                if 'institution' in author.keys():
                    make_simple_element(
                        'affiliation', author['institution'], parent=name_node
                    )
                elif 'affiliation' in author.keys():
                    make_simple_element(
                        'affiliation', author['affiliation'], parent=name_node
                    )
        else:
            if field == 'url':
                value = f'{anthology_id}'
            elif field == 'booktitle':
                value = meta['book_title']
            elif field == 'month':
                value = meta['month']
            elif field == 'year':
                value = meta['year']

            try:
                make_simple_element(field, text=value, parent=paper)
            except Exception:
                print(
                    f"Couldn't process proceeding {paper} for {anthology_id}",
                    file=sys.stderr,
                )
                sys.exit(2)
    return paper


def paper2xml(
    paper_item: Dict[str, str], paper_num: int, anthology_id: str, meta: Dict[str, Any]
):
    '''
    paper keys = ['abstract',
                  'attachments',
                  'attributes',
                  'authors',
                  'decision',
                  'file',
                  'id',
                  'openreview_id',
                  'pdf_file',
                  'title']
    author keys = ['emails',
                   'first_name',
                   'google_scholar_id',
                   'homepage',
                   'last_name',
                   'name',
                   'semantic_scholar_id',
                   'username']
    '''
    fields = [
        'title',
        'author',
        'pages',
        'abstract',
        'url',
        'doi',
        'language',
    ]
    paper = make_simple_element('paper', attrib={'id': str(paper_num)})
    for field in fields:
        if field == 'author':
            authors = paper_item['authors']
            for author in authors:
                name_node = make_simple_element(field, parent=paper)
                make_simple_element('first', author['first_name'], parent=name_node)
                make_simple_element('last', author['last_name'], parent=name_node)
                # add affiliation
                if 'institution' in author.keys():
                    make_simple_element(
                        'affiliation', author['institution'], parent=name_node
                    )
                elif 'affiliation' in author.keys():
                    make_simple_element(
                        'affiliation', author['affiliation'], parent=name_node
                    )
        else:
            if field == 'url':
                value = f'{anthology_id}'
            elif field == 'abstract':
                value = paper_item['abstract'].replace('\n', '')
            elif field == 'title':
                value = paper_item[field]
            elif field == 'pages':
                value = paper_item[field]
            else:
                continue
            try:
                make_simple_element(field, text=value, parent=paper)
            except Exception:
                print(
                    f"Couldn't process {paper} for {anthology_id}, please check the abstract in the papers.yaml file for this paper",
                    file=sys.stderr,
                )
                sys.exit(2)
    return paper


def process_procedding(
    ingestion_dir: str,
    anthology_datadir: str,
    venue_index: VenueIndex,
    venue_keys: List[str],
) -> Tuple[str, Dict[str, Any]]:
    meta = parse_conf_yaml(ingestion_dir)
    venue_abbrev = meta["anthology_venue_id"]
    venue_slug = venue_index.get_slug_from_acronym(venue_abbrev)

    if str(datetime.now().year) in venue_abbrev:
        print(f"Fatal: Venue assembler put year in acronym: '{venue_abbrev}'")
        sys.exit(1)

    if re.match(r".*\d$", venue_abbrev) is not None:
        print(
            f"WARNING: Venue {venue_abbrev} ends in a number, this is probably a mistake"
        )

    if venue_slug not in venue_keys:
        event_name = meta['event_name']
        assert (
            re.match(r'(.)* [Ww]orkshop', event_name) is None
        ), f"event name should start with Workshop or The Workshop, instead it started with {re.match(r'(.)* [Ww]orkshop', event_name)[0]}"
        print(f"Creating new venue '{venue_abbrev}' ({event_name})")
        venue_index.add_venue(anthology_datadir, venue_abbrev, meta['event_name'])

    meta["path"] = ingestion_dir
    meta["collection_id"] = collection_id = meta["year"] + "." + venue_slug
    volume_name = meta["volume_name"].lower()
    volume_full_id = f"{collection_id}-{volume_name}"

    # if "sig" in meta:
    #     print(
    #         f"Add this line to {anthology_datadir}/sigs/{meta['sig'].lower()}.yaml:"
    #     )
    #     print(f"  - {meta['year']}:")
    #     print(f"    - {volume_full_id} # {meta['booktitle']}")

    # print(f'volume_full_id {volume_full_id} meta {meta}')
    return volume_full_id, meta


def copy_pdf_and_attachment(
    meta: Dict[str, Any],
    pdfs_dir: str,
    attachments_dir: str,
    papers: List[Dict[str, str]],
    dry_run: bool,
) -> Tuple[Dict[str, Dict[str, str]], str, str, str]:
    volume = dict()
    collection_id = meta['collection_id']
    venue_name = meta['anthology_venue_id'].lower()
    volume_name = meta['volume_name'].lower()

    pdfs_dest_dir = create_des_path(pdfs_dir, venue_name)

    pdfs_src_dir = os.path.join(meta['path'], 'watermarked_pdfs')

    # copy proceedings.pdf
    proceedings_pdf_src_path = os.path.join(meta['path'], 'proceedings.pdf')
    assert os.path.exists(proceedings_pdf_src_path), 'proceedings.pdf was not found'
    proceedings_pdf_dest_path = (
        os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}") + ".pdf"
    )
    if dry_run:
        print(
            f'would\'ve moved {proceedings_pdf_src_path} to {proceedings_pdf_dest_path}'
        )
    if not dry_run:
        maybe_copy(proceedings_pdf_src_path, proceedings_pdf_dest_path)

    # copy frontmatter
    frontmatter_src_path = os.path.join(pdfs_src_dir, '0.pdf')
    frontmatter_dest_path = (
        os.path.join(pdfs_dest_dir, f"{collection_id}-{volume_name}") + '.0.pdf'
    )
    if dry_run:
        print(f'would\'ve moved {frontmatter_src_path} to {frontmatter_dest_path}')
    if not dry_run:
        maybe_copy(frontmatter_src_path, frontmatter_dest_path)

    paper_id_full = f'{collection_id}-{volume_name}.0'
    volume[0] = {
        'anthology_id': paper_id_full,
        'pdf': frontmatter_dest_path,
        'attachments': [],
    }

    for i, paper in enumerate(papers):
        # archival papers only
        if 'archival' not in paper.keys():
            paper.update({'archival': '1'})
        assert 'archival' in paper.keys(), f'{paper["id"]} is missing key archival'
        assert 'file' in paper.keys(), f'{paper["id"]} is missing key file'
        if (
            paper['archival'] == 1
            or paper['archival'] is True
            or paper['archival'] == '1'
        ):
            # copy pdf
            # if 'file' not in paper.keys():
            #     paper_name = paper['title']
            #     print(f'{paper_name} does not have file key')
            # else:
            paper_name = paper['file']
            # paper_name = paper['file']
            if paper_name != '' or paper_name is not None:
                paper_id = str(paper['id'])
                paper_num = i + 1
                paper_id_full = f'{collection_id}-{volume_name}.{paper_num}'

                if os.path.exists(os.path.join(pdfs_src_dir, paper_name)):
                    pdf_src_path = os.path.join(pdfs_src_dir, paper_name)
                elif os.path.exists(os.path.join(pdfs_src_dir, f'{paper_id}.pdf')):
                    pdf_src_path = os.path.join(pdfs_src_dir, f'{paper_id}.pdf')
                else:
                    pdf_src_path = None
                assert pdf_src_path, f'{paper_name} path is None'
                pdf_dest_path = os.path.join(
                    pdfs_dest_dir, f"{collection_id}-{volume_name}.{paper_num}.pdf"
                )
                if dry_run:
                    print(f'would\'ve moved {pdf_src_path} to {pdf_dest_path}')
                if not dry_run:
                    maybe_copy(pdf_src_path, pdf_dest_path)

                volume[paper_num] = {
                    'anthology_id': paper_id_full,
                    'pdf': pdf_dest_path,
                    'attachments': [],
                }
            # copy attachments
            if 'attachments' in paper.keys() and paper['attachments']:
                attchs_dest_dir = create_des_path(attachments_dir, venue_name)
                attchs_src_dir = os.path.join(meta['path'], 'attachments')
                assert os.path.exists(
                    attchs_src_dir
                ), f'paper {i, paper_name} contains attachments but attachments folder was not found'
                cur_paper = paper['attachments'][0]['file']
                if os.path.split(cur_paper)[0] == 'attachments':
                    cur_paper = os.path.split(cur_paper)[1]
                attch_src_path = attchs_src_dir + '/' + cur_paper
                assert attch_src_path, f'{paper_name} attachment path is None'
                _, attch_src_extension = os.path.splitext(attch_src_path)
                type_ = paper['attachments'][0]['type']
                file_name = f'{collection_id}-{volume_name}.{paper_num}.{type_}{attch_src_extension}'
                attch_dest_path = os.path.join(attchs_dest_dir, file_name)
                print(f'attach src path is {attch_src_path}')
                if dry_run:
                    print(f'would\'ve moved {attch_src_path} to {attch_dest_path}')
                if not dry_run:
                    maybe_copy(attch_src_path, attch_dest_path)
                volume[paper_num]['attachments'].append((attch_dest_path, type_))
    return volume, collection_id, volume_name, proceedings_pdf_dest_path


def create_xml(
    volume: Dict[str, Dict[str, str]],
    anthology_dir: str,
    ingest_date: str,
    collection_id: str,
    volume_name: str,
    meta: Dict[str, Any],
    proceedings_pdf_dest_path: str,
    people,
    papers: List[Dict[str, str]],
) -> None:
    venue_name = meta['anthology_venue_id'].lower()
    collection_file = os.path.join(anthology_dir, 'data', 'xml', f'{collection_id}.xml')
    if os.path.exists(collection_file):
        root_node = etree.parse(collection_file).getroot()
    else:
        root_node = make_simple_element('collection', attrib={'id': collection_id})

    volume_node = make_simple_element(
        'volume',
        attrib={'id': volume_name, 'ingest-date': ingest_date},
    )
    # Replace the existing one if present
    root_node.find(f"./volume[@id='{volume_name}']")
    for i, child in enumerate(root_node):
        if child.attrib['id'] == volume_name:
            root_node[i] = volume_node
            break
    else:
        root_node.append(volume_node)

    meta_node = None

    for paper_num, paper in sorted(volume.items()):
        paper_id_full = paper['anthology_id']
        # print(f'creating xml for paper name {paper}, in papers {papers[paper_num-1]}')
        if paper_num == 0:
            paper_node = proceeding2xml(paper_id_full, meta)
        else:
            paper_node = paper2xml(papers[paper_num - 1], paper_num, paper_id_full, meta)

        if paper_node.attrib['id'] == '0':
            # create metadata subtree
            meta_node = make_simple_element('meta', parent=volume_node)
            title_node = paper_node.find('booktitle')
            meta_node.append(title_node)
            for editor in paper_node.findall('./editor'):
                disamb_name, name_choice = disambiguate_name(
                    editor, paper_id_full, people
                )
                if name_choice != -1:
                    editor.attrib['id'] = disamb_name
                PersonName.from_element(editor)
                for name_part in editor:
                    name_part.text = correct_caps(name_part.text)
                meta_node.append(editor)

            # Get the publisher from the meta file
            publisher_node = make_simple_element('publisher', meta['publisher'])
            meta_node.append(publisher_node)

            # Get the address from the meta file
            address_node = make_simple_element("address", meta['location'])
            meta_node.append(address_node)

            meta_node.append(paper_node.find('month'))
            meta_node.append(paper_node.find('year'))

            make_simple_element(
                'url',
                text=f"{collection_id}-{volume_name}",
                attrib={'hash': compute_hash_from_file(proceedings_pdf_dest_path)},
                parent=meta_node,
            )

            # add the venue tag
            make_simple_element("venue", venue_name, parent=meta_node)

            # modify frontmatter tag
            paper_node.tag = 'frontmatter'
            del paper_node.attrib['id']

        url = paper_node.find('./url')
        # if url is not None:
        url.attrib['hash'] = compute_hash_from_file(paper['pdf'])

        for path, type_ in paper['attachments']:
            make_simple_element(
                'attachment',
                text=os.path.basename(path),
                attrib={
                    'type': type_,
                    'hash': compute_hash_from_file(path),
                },
                parent=paper_node,
            )

        if len(paper_node) > 0:
            volume_node.append(paper_node)

        # Normalize
        for oldnode in paper_node:
            normalize(oldnode, informat='latex')

        # Adjust the language tag
        # language_node = paper_node.find('./language')
        # if language_node is not None:
        #     try:
        #         lang = iso639.languages.get(name=language_node.text)
        #     except KeyError:
        #         raise Exception(f"Can't find language '{language_node.text}'")
        #     language_node.text = lang.part3

        # Fix author names
        for name_node in paper_node.findall('./author'):
            disamb_name, name_choice = disambiguate_name(name_node, paper_id_full, people)
            if name_choice != -1:
                name_node.attrib['id'] = disamb_name
            PersonName.from_element(name_node)
            for name_part in name_node:
                name_part.text = correct_caps(name_part.text)

    # Other data from the meta file
    # if 'isbn' in meta:
    #     make_simple_element('isbn', meta['isbn'], parent=meta_node)

    indent(root_node)
    tree = etree.ElementTree(root_node)
    tree.write(collection_file, encoding='UTF-8', xml_declaration=True, with_tail=True)


@click.command()
@click.option(
    '-i',
    '--ingestion_dir',
    help='Directory contains proceedings need to be ingested',
)
@click.option(
    '-p',
    '--pdfs_dir',
    default=os.path.join(os.environ['HOME'], 'anthology-files', 'pdf'),
    help='Root path for placement of PDF files',
)
@click.option(
    '-a',
    '--attachments_dir',
    default=os.path.join(os.environ['HOME'], 'anthology-files', 'attachments'),
    help='Root path for placement of attachment files',
)
@click.option(
    '-n',
    '--dry_run',
    default=False,
    help='Do not actually copy anything',
)
@click.option(
    '-r',
    '--anthology_dir',
    default=os.path.join(os.path.dirname(sys.argv[0]), ".."),
    help='Root path of ACL Anthology Github repo.',
)
@click.option(
    '-d',
    '--ingest_date',
    default=f'{datetime.now().year}-{datetime.now().month:02d}-{datetime.now().day:02d}',
    help='Ingestion date',
)
def main(ingestion_dir, pdfs_dir, attachments_dir, dry_run, anthology_dir, ingest_date):
    anthology_datadir = os.path.join(os.path.dirname(sys.argv[0]), "..", "data")
    venue_index = VenueIndex(srcdir=anthology_datadir)
    venue_keys = [venue["slug"].lower() for _, venue in venue_index.items()]

    people = AnthologyIndex(srcdir=anthology_datadir)
    # people.bibkeys = load_bibkeys(anthology_datadir)

    volume_full_id, meta = process_procedding(
        ingestion_dir, anthology_datadir, venue_index, venue_keys
    )
    papers = parse_paper_yaml(ingestion_dir)
    # print(f'original paper {papers[0]}')
    papers = add_paper_nums_in_paper_yaml(papers, ingestion_dir)
    # print(f'updated paper {papers[0]}')
    (
        volume,
        collection_id,
        volume_name,
        proceedings_pdf_dest_path,
    ) = copy_pdf_and_attachment(meta, pdfs_dir, attachments_dir, papers, dry_run)
    create_xml(
        volume=volume,
        anthology_dir=anthology_dir,
        ingest_date=ingest_date,
        collection_id=collection_id,
        volume_name=volume_name,
        meta=meta,
        proceedings_pdf_dest_path=proceedings_pdf_dest_path,
        people=people,
        papers=papers,
    )


if __name__ == '__main__':
    main()
