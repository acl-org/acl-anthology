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
#
# First, make sure the ACLPUB2_DIR subscribes to the following format.
#
# aclpub2/
#   front_matter.pdf
#   proceedings.pdf
#   papers.yml   # updated with relative paths for attachments and PDFs
#   conference_details.yml  # this could probably be unchanged
#   pdfs/
#     1.pdf
#     ...
#   attachments/
#     49_software.zip
#     17_dataset.tgz
#     ...
#
# It sometimes doesn't because the format is not set in stone, so files
# may be scattered. Use symlinks or move everything around to make it all
# right.
#
# Then, run
#
#     python bin/ingest_aclpub2.py -i ACLPUB2_DIR
#
# It will:
# - Create the volumes in the acl-anthology directory (updating if they exist)
# - Copy PDFs and attachments to ~/anthology-files/{pdf,attachments}
#
# Check things over, then commit and push the changes and synchronize the files.

# TODO:
# - check for venue YAML, create/complain if non-existent
# - add verification model to ensure format is correct

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

# Whether papers are archival by default
ARCHIVAL_DEFAULT = True


def disambiguate_name(node, anth_id, people):
    """
    There may be multiple matching names. If so, ask the ingester to choose
    which one is the disambiguated one. Ideally, this would be determined
    automatically from metadata or providing orcids or other disambiguators.
    """
    name = PersonName.from_element(node)
    ids = people.get_ids(name)

    choice = -1
    if len(ids) > 1:
        # TEMPORARY
        choice = 0

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
    if name is not None and (name.islower() or name.isupper()):
        # capitalize all parts
        corrected = " ".join(list(map(lambda x: x.capitalize(), name.split())))
        if name != corrected:
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
    ingestion_dir = Path(ingestion_dir)

    paths_to_check = [
        ingestion_dir / 'inputs' / 'conference_details.yml',
        ingestion_dir / 'conference_details.yml',
    ]
    meta = None
    for path in paths_to_check:
        if path.exists():
            meta = yaml.safe_load(path.read_text())
            break
    else:
        raise Exception("Can't find conference_details.yml (looked in {paths_to_check})")

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
            f"Invalid volume key '{meta['volume_name']}' in {ingestion_dir / 'inputs' / 'conference_details.yml'}"
        )

    return meta


def parse_paper_yaml(ingestion_dir: str) -> List[Dict[str, str]]:
    """
    Reads papers.yml to get metadata. Skips non-archival papers.
    """
    ingestion_dir = Path(ingestion_dir)

    paths_to_check = [
        ingestion_dir / 'inputs' / 'papers.yml',
        ingestion_dir / 'papers.yml',
    ]
    papers = None
    for path in paths_to_check:
        if path.exists():
            papers = yaml.safe_load(path.read_text())
            break
    else:
        raise Exception("Can't find papers.yml (looked in root dir and under inputs/)")

    for paper in papers:
        if "archival" not in paper:
            paper["archival"] = ARCHIVAL_DEFAULT

    return papers


def add_paper_nums_in_paper_yaml(
    papers: List[Dict[str, str]], ingestion_dir: str
) -> List[Dict[str, str]]:
    """
    Reads PDFs to get page numbers for metadata.
    """
    ingestion_dir = Path(ingestion_dir)

    start, end = 1, 0
    for paper in papers:
        if paper["archival"]:
            assert 'file' in paper.keys(), f'{paper["id"]} is missing key "file"'

            paper_id = str(paper['id'])
            # if 'file' not in paper.keys():
            #     print(f'{paper_id} does not have file key but archive is {paper["archival"]}')
            #     paper_name = paper['title']
            # else:

            paper_path = paper['file']

            # TODO: we should just be able to read paper_path directly, and throw an
            # error if it doesn't exist
            paper_need_read_path = None
            paths_to_check = [
                ingestion_dir / "watermarked_pdfs" / paper_path,
                ingestion_dir / "watermarked_pdfs" / f"{paper_id}.pdf",
            ]
            paper_need_read_path = None
            for path in paths_to_check:
                if path.exists():
                    paper_need_read_path = str(path)
                    break
            else:
                raise Exception(
                    f"* Fatal: could not find paper ID {paper_id} ({paths_to_check})"
                )

            pdf = open(paper_need_read_path, 'rb')
            pdf_reader = PyPDF2.PdfReader(pdf)
            num_of_pages = len(pdf_reader.pages)
            start = end + 1
            end = start + num_of_pages - 1
            paper['pages'] = f'{start}-{end}'

    return papers


def create_dest_path(org_dir_name: str, venue_name: str) -> str:
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


def correct_names(author):
    """
    A set of corrections we apply to upstream name parsing.
    """
    if "middle_name" in author and author["middle_name"].lower() == "de":
        author["last_name"] = author["middle_name"] + " " + author["last_name"]
        del author["middle_name"]

    return author


def join_names(author, fields=["first_name", "middle_name"]):
    """
    Joins name fields. If you want to merge first names with middle names,
    set fields to ["first_name", "middle_name"]. However, many people enter
    their middle names without the expectation that it will appear.
    """
    names = []
    for field in fields:
        if author.get(field) is not None:
            names.append(author[field])
    return " ".join(names)


def proceeding2xml(anthology_id: str, meta: Dict[str, Any], frontmatter):
    """
    Creates the XML meta block for a volume from the paper YAML data structure.
    If the frontmatter PDF is not set, we skip the "url" field, which downstream
    will cause the <frontmatter> block not to be generated.
    """
    fields = [
        'editor',
        'booktitle',
        'month',
        'year',
        'url',
    ]

    frontmatter_node = make_simple_element('frontmatter', attrib={'id': '0'})
    for field in fields:
        if field == 'editor':
            authors = meta['editors']
            for author in authors:
                author = correct_names(author)
                name_node = make_simple_element(field, parent=frontmatter_node)
                make_simple_element('first', join_names(author), parent=name_node)
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
                if "pdf" in frontmatter:
                    # Only create the entry if the PDF exists
                    value = f'{anthology_id}'
                else:
                    print(
                        f"Warning: skipping PDF for {anthology_id}: {meta}",
                        file=sys.stderr,
                    )
                    value = None
            elif field == 'booktitle':
                value = meta['book_title']
            elif field == 'month':
                value = meta['month']
            elif field == 'year':
                value = meta['year']

            if value is not None:
                make_simple_element(field, text=value, parent=frontmatter_node)

    return frontmatter_node


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
    paper = make_simple_element('paper', attrib={"id": str(paper_num)})
    for field in fields:
        if field == 'author':
            authors = paper_item['authors']
            for author in authors:
                author = correct_names(author)

                name_node = make_simple_element(field, parent=paper)

                # swap names (<last> can't be empty)
                first_name = join_names(author)
                last_name = author['last_name']
                if first_name != "" and last_name == "":
                    first_name, last_name = last_name, first_name

                make_simple_element('first', first_name, parent=name_node)
                make_simple_element('last', last_name, parent=name_node)

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
                value = None
                if "abstract" in paper_item and paper_item["abstract"] is not None:
                    value = paper_item["abstract"].replace('\n', '')
            elif field == 'title':
                value = paper_item[field]
            elif field == 'pages':
                value = paper_item[field]
            else:
                continue

            try:
                if value is not None:
                    make_simple_element(field, text=value, parent=paper)
            except Exception as e:
                print("* ERROR:", e, file=sys.stderr)
                print(
                    f"* Couldn't process {field}='{value}' for {anthology_id}, please check the abstract in the papers.yaml file for this paper",
                    file=sys.stderr,
                )
                for key, value in paper_item.items():
                    print(f"* -> {key} => {value}", file=sys.stderr)
                sys.exit(2)
    return paper


def process_proceeding(
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
        if re.match(r'(.)* [Ww]orkshop', event_name) is None:
            print(
                "* Warning: event name should start with Workshop, instead it started with",
                re.match(r'(.)* [Ww]orkshop', event_name),
                file=sys.stderr,
            )
        print(f"Creating new venue '{venue_abbrev}' ({event_name})")
        venue_index.add_venue(anthology_datadir, venue_abbrev, meta['event_name'])

    meta["path"] = Path(ingestion_dir)
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
) -> Tuple[Dict[str, Dict[str, str]], str, str, str]:
    """
    Copies PDFs and attachments to ready them for upload. Creates
    data structures used to subsequently generate the XML.
    """

    volume = dict()
    collection_id = meta['collection_id']
    venue_name = meta['anthology_venue_id'].lower()
    volume_name = meta['volume_name'].lower()

    pdfs_src_dir = None
    paths_to_check = [
        meta['path'] / 'watermarked_pdfs',
    ]
    for path in paths_to_check:
        if path.exists() and path.is_dir():
            pdfs_src_dir = path
            break
    else:
        raise FileNotFoundError(f"Could not find watermarked PDFs in {paths_to_check}")

    pdfs_dest_dir = Path(create_dest_path(pdfs_dir, venue_name))

    # copy proceedings.pdf
    proceedings_pdf_src_path = None
    paths_to_check = [
        meta['path'] / 'proceedings.pdf',
        meta['path'] / "build" / 'proceedings.pdf',
    ]
    for path in paths_to_check:
        if path.exists():
            proceedings_pdf_src_path = str(path)
            break
    else:
        print(
            f"Warning: could not find proceedings.pdf in {paths_to_check}",
            file=sys.stderr,
        )

    proceedings_pdf_dest_path = None
    if proceedings_pdf_src_path is not None:
        proceedings_pdf_dest_path = pdfs_dest_dir / f"{collection_id}-{volume_name}.pdf"
        maybe_copy(proceedings_pdf_src_path, proceedings_pdf_dest_path)
    else:
        print("Warning: proceedings.pdf was not found, skipping", file=sys.stderr)

    # Create entry for frontmatter, even if the PDF isn't there. We need this entry
    # because it is used to create the <meta> block for the volume.
    volume[0] = {
        "anthology_id": f"{collection_id}-{volume_name}.0",
        "attachments": [],
        "archival": True,
    }

    frontmatter_src_path = None
    paths_to_check = [
        meta['path'] / 'front_matter.pdf',
        meta['path'] / "watermarked_pdfs" / 'front_matter.pdf',
        meta['path'] / "watermarked_pdfs" / '0.pdf',
    ]
    for path in paths_to_check:
        if path.exists():
            frontmatter_src_path = str(path)
            print(f"Found frontmatter at {frontmatter_src_path}", file=sys.stderr)
            break
    else:
        print(
            f"Warning: could not find front matter in {paths_to_check}", file=sys.stderr
        )

    if frontmatter_src_path is not None:
        frontmatter_dest_path = pdfs_dest_dir / f"{collection_id}-{volume_name}.0.pdf"
        maybe_copy(frontmatter_src_path, frontmatter_dest_path)

        # create the PDF entry so that we'll get <frontmatter>
        volume[0]['pdf'] = frontmatter_dest_path

    paper_num = 0
    for i, paper in enumerate(papers):
        assert 'archival' in paper.keys(), f'{paper["id"]} is missing key "archival"'

        paper_num += 1
        paper_id_full = f'{collection_id}-{volume_name}.{paper_num}'

        is_archival = paper["archival"]

        volume[paper_num] = {
            'anthology_id': paper_id_full,
            'attachments': [],
            'archival': is_archival,
        }

        if is_archival:
            assert 'file' in paper.keys(), f'{paper["id"]} is missing key "file"'
            paper_name = paper['file']
            paper_id = str(paper['id'])

            pdf_src_path = None
            if (pdfs_src_dir / paper_name).exists():
                pdf_src_path = pdfs_src_dir / paper_name
            elif pdfs_src_dir / f'{paper_id}.pdf':
                pdf_src_path = pdfs_src_dir / f'{paper_id}.pdf'

            assert (
                pdf_src_path
            ), f"Couldn't find {paper_name} or {paper_id} in {pdfs_src_dir}"
            pdf_dest_path = pdfs_dest_dir / f"{paper_id_full}.pdf"
            maybe_copy(pdf_src_path, pdf_dest_path)

            volume[paper_num]["pdf"] = pdf_dest_path

            # copy attachments
            if 'attachments' in paper:
                attachs_dest_dir = create_dest_path(attachments_dir, venue_name)
                attachs_src_dir = meta['path'] / 'attachments'
                # assert (
                #     attachs_src_dir.exists()
                # ), f'paper {i, paper_name} contains attachments but attachments folder was not found'

                for attachment in paper['attachments']:
                    file_path = Path(attachment.get('file', None))
                    if file_path is None:
                        continue

                    attach_src_path = None
                    paths_to_check = [
                        attachs_src_dir / file_path,
                        attachs_src_dir / file_path.name,
                    ]
                    for path in paths_to_check:
                        if path.exists():
                            attach_src_path = str(path)
                            break
                    else:
                        print(
                            f"Warning: paper {paper_id} attachment {file_path} not found, skipping",
                            file=sys.stderr,
                        )
                        continue

                    attach_src_extension = attach_src_path.split(".")[-1]
                    type_ = attachment['type'].replace(" ", "")
                    file_name = f'{collection_id}-{volume_name}.{paper_num}.{type_}.{attach_src_extension}'

                    # the destination path
                    attach_dest_path = os.path.join(attachs_dest_dir, file_name).replace(
                        " ", ""
                    )

                    if Path(attach_src_path).exists():
                        maybe_copy(attach_src_path, attach_dest_path)
                        print(f"Attaching {attach_dest_path} ({type_}) to {paper_num}")
                        volume[paper_num]['attachments'].append((attach_dest_path, type_))

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
        attrib={'id': volume_name, 'ingest-date': ingest_date, "type": "proceedings"},
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
        if not paper["archival"]:
            print(f"Skipping non-archival paper #{paper_num}", file=sys.stderr)
            continue

        paper_id_full = paper['anthology_id']
        # print(f'creating xml for paper name {paper}, in papers {papers[paper_num-1]}')
        if paper_num == 0:
            paper_node = proceeding2xml(paper_id_full, meta, volume[0])
            # year, venue = collection_id.split(".")
            # bibkey = f"{venue}-{year}-{volume_name}"
        else:
            paper_node = paper2xml(papers[paper_num - 1], paper_num, paper_id_full, meta)
            # bibkey = anthology.pindex.create_bibkey(paper_node, vidx=anthology.venues)

        # Ideally this would be here, but it requires a Paper object, which requires a Volume object, etc
        # Just a little bit complicated
        # make_simple_element("bibkey", "", parent=paper)

        paper_id = paper_node.attrib['id']
        if paper_id == '0':
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
                    if name_part.text is not None and name_part.tag in [
                        "first",
                        "middle",
                        "last",
                    ]:
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

            # Create the entry for the PDF, if defined
            if proceedings_pdf_dest_path is not None:
                make_simple_element(
                    'url',
                    text=f"{collection_id}-{volume_name}",
                    attrib={'hash': compute_hash_from_file(proceedings_pdf_dest_path)},
                    parent=meta_node,
                )

            # add the venue tag
            make_simple_element("venue", venue_name, parent=meta_node)

            # modify frontmatter tag
            paper_node.tag = "frontmatter"
            del paper_node.attrib['id']

        url = paper_node.find('./url')
        if url is not None:
            url.attrib['hash'] = compute_hash_from_file(paper['pdf'])

        for path, type_ in paper['attachments']:
            # skip copyrights
            if type_ == "copyright":
                continue

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
        else:
            print("Not appending", paper_node, file=sys.stderr)

        # Normalize fields from LaTeX
        for oldnode in paper_node:
            try:
                normalize(oldnode, informat='latex')
            except UnicodeError:
                print(
                    f"Fatal on paper {paper_num} field {oldnode.tag}: {oldnode.text}",
                    file=sys.stderr,
                )
                sys.exit(1)

        # Adjust the language tag
        # language_node = paper_node.find('./language')
        # if language_node is not None:
        #     try:
        #         lang = iso639.languages.get(name=language_node.text)
        #     except KeyError:
        #         raise Exception(f"Can't find language '{language_node.text}'")
        #     language_node.text = lang.part3

        # Fix abstracts
        # People love cutting and pasting their LaTeX-infused abstracts directly
        # from their papers. We attempt to parse this but there are failure cases
        # particularly with embedded LaTeX commands. Here we use a simple heuristic
        # to remove likely-failed parsing instances: delete abstracts with stray
        # latex commands (a backslash followed at some distance by a {).
        abstract_node = paper_node.find('./abstract')
        # TODO: this doesn't work because the XML is hierarchical, need to render
        # to text first
        if abstract_node is not None:
            if abstract_node.text is not None and '\\' in abstract_node.text:
                print(
                    f"* WARNING: paper {paper_id_full}: deleting abstract node containing a backslash: {abstract_node.text}",
                    file=sys.stderr,
                )
                paper_node.remove(abstract_node)

        # Fix author names
        for name_node in paper_node.findall('./author'):
            disamb_name, name_choice = disambiguate_name(name_node, paper_id_full, people)
            if name_choice != -1:
                name_node.attrib['id'] = disamb_name
            PersonName.from_element(name_node)
            for name_part in name_node:
                if name_part.text is None:
                    print(
                        f"* WARNING: element {name_part.tag} has null text",
                        file=sys.stderr,
                    )
                if name_part is not None and name_part.tag in ["first", "middle", "last"]:
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
def main(ingestion_dir, pdfs_dir, attachments_dir, anthology_dir, ingest_date):
    anthology_datadir = Path(sys.argv[0]).parent / ".." / "data"
    # anthology = Anthology(
    #     importdir=anthology_datadir, require_bibkeys=False
    # )

    venue_index = VenueIndex(srcdir=anthology_datadir)
    venue_keys = [venue["slug"].lower() for _, venue in venue_index.items()]

    people = AnthologyIndex(srcdir=anthology_datadir)
    # people.bibkeys = load_bibkeys(anthology_datadir)

    volume_full_id, meta = process_proceeding(
        ingestion_dir, anthology_datadir, venue_index, venue_keys
    )

    # Load the papers.yaml file, skipping non-archival papers
    papers = parse_paper_yaml(ingestion_dir)
    print(
        "Found",
        len([p for p in papers if p["archival"]]),
        "archival papers",
        file=sys.stderr,
    )

    # add page numbering by parsing the PDFs
    papers = add_paper_nums_in_paper_yaml(papers, ingestion_dir)

    (
        volume,
        collection_id,
        volume_name,
        proceedings_pdf_dest_path,
    ) = copy_pdf_and_attachment(meta, pdfs_dir, attachments_dir, papers)

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
