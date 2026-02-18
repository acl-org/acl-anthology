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

import click
import yaml
import re
import sys
import os
import PyPDF2

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from acl_anthology import Anthology
from acl_anthology.collections.types import EventLink, PaperType, VolumeType
from acl_anthology.files import (
    AttachmentReference,
    PDFReference,
    compute_checksum_from_file,
)
from acl_anthology.people import Name, NameSpecification

from ingest import (
    correct_caps,
    maybe_copy,
    normalize_latex_title,
    normalize_abstract,
    venue_slug_from_acronym,
)

ARCHIVAL_DEFAULT = True


def parse_conf_yaml(ingestion_dir: str) -> Dict[str, Any]:
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
        raise Exception(f"Can't find conference_details.yml (looked in {paths_to_check})")

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


def parse_paper_yaml(ingestion_dir: str) -> List[Dict[str, Any]]:
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
        if 'archival' not in paper:
            paper['archival'] = ARCHIVAL_DEFAULT

    return papers


def add_page_numbers(
    papers: List[Dict[str, Any]], ingestion_dir: str
) -> List[Dict[str, Any]]:
    ingestion_dir = Path(ingestion_dir)

    start, end = 1, 0
    for paper in papers:
        if not paper['archival']:
            continue

        assert 'file' in paper.keys(), f"{paper['id']} is missing key 'file'"

        paper_id = str(paper['id'])
        paper_path = paper['file']

        paths_to_check = [
            ingestion_dir / 'watermarked_pdfs' / paper_path,
            ingestion_dir / 'watermarked_pdfs' / f'{paper_id}.pdf',
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

        with open(paper_need_read_path, 'rb') as pdf:
            pdf_reader = PyPDF2.PdfReader(pdf)
            num_of_pages = len(pdf_reader.pages)
            start = end + 1
            end = start + num_of_pages - 1
            paper['pages'] = f'{start}-{end}'

    return papers


def trim_orcid(orcid: str) -> str:
    match = re.match(r'.*(\d{4}-\d{4}-\d{4}-\d{3}[\dX]).*', orcid, re.IGNORECASE)
    if match is not None:
        return match.group(1).upper()
    return orcid


def correct_names(author: Dict[str, Any]) -> Dict[str, Any]:
    if author.get('middle_name') is not None and author['middle_name'].lower() == 'de':
        author['last_name'] = author['middle_name'] + ' ' + author['last_name']
        del author['middle_name']
    return author


def join_names(author: Dict[str, Any], fields=None) -> str:
    if fields is None:
        fields = ['first_name', 'middle_name']
    names = []
    for field in fields:
        if author.get(field) is not None:
            names.append(author[field])
    return ' '.join(names)


def namespec_from_author(author: Dict[str, Any]) -> NameSpecification:
    author = correct_names(dict(author))

    first_name = correct_caps(join_names(author).strip())
    last_name = correct_caps((author.get('last_name') or '').strip())
    if first_name and not last_name:
        first_name, last_name = last_name, first_name

    if not last_name:
        raise Exception(f'BAD AUTHOR: {author}')

    kwargs: Dict[str, Any] = {
        'name': Name(first_name if first_name else None, last_name),
    }

    if 'orcid' in author and author['orcid']:
        kwargs['orcid'] = trim_orcid(str(author['orcid']))

    affiliation = author.get('institution') or author.get('affiliation')
    if affiliation:
        kwargs['affiliation'] = affiliation

    return NameSpecification(**kwargs)


def create_dest_path(org_dir_name: str, venue_name: str) -> str:
    dest_dir = os.path.join(org_dir_name, venue_name)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    return dest_dir


def process_proceeding(
    ingestion_dir: str, anthology: Anthology
) -> Tuple[str, Dict[str, Any]]:
    meta = parse_conf_yaml(ingestion_dir)
    venue_abbrev = meta['anthology_venue_id']
    venue_slug = venue_slug_from_acronym(venue_abbrev)

    if str(datetime.now().year) in venue_abbrev:
        print(f"Fatal: Venue assembler put year in acronym: '{venue_abbrev}'")
        sys.exit(1)

    if re.match(r'.*\d$', venue_abbrev) is not None:
        print(
            f'WARNING: Venue {venue_abbrev} ends in a number, this is probably a mistake'
        )

    if venue_slug not in anthology.venues:
        event_name = meta['event_name']
        if re.match(r'(.)* [Ww]orkshop', event_name) is None:
            print(
                '* Warning: event name should start with Workshop, instead it started with',
                event_name,
                file=sys.stderr,
            )
        print(f"Creating new venue '{venue_abbrev}' ({event_name})")
        anthology.venues.create(id=venue_slug, acronym=venue_abbrev, name=event_name)

    meta['path'] = Path(ingestion_dir)
    meta['collection_id'] = collection_id = meta['year'] + '.' + venue_slug
    volume_name = meta['volume_name'].lower()
    volume_full_id = f'{collection_id}-{volume_name}'

    return volume_full_id, meta


def copy_pdf_and_attachment(
    meta: Dict[str, Any],
    pdfs_dir: str,
    attachments_dir: str,
    papers: List[Dict[str, Any]],
) -> Tuple[Dict[int, Dict[str, Any]], str, str, Optional[str], Optional[str]]:
    volume: Dict[int, Dict[str, Any]] = {}
    collection_id = meta['collection_id']
    venue_name = meta['anthology_venue_id'].lower()
    volume_name = meta['volume_name'].lower()

    pdfs_src_dir = None
    for path in [meta['path'] / 'watermarked_pdfs']:
        if path.exists() and path.is_dir():
            pdfs_src_dir = path
            break
    else:
        raise FileNotFoundError(
            f'Could not find watermarked PDFs in {[meta["path"] / "watermarked_pdfs"]}'
        )

    pdfs_dest_dir = Path(create_dest_path(pdfs_dir, venue_name))

    proceedings_pdf_src_path = None
    for path in [
        meta['path'] / 'proceedings.pdf',
        meta['path'] / 'build' / 'proceedings.pdf',
    ]:
        if path.exists():
            proceedings_pdf_src_path = str(path)
            break
    if proceedings_pdf_src_path is None:
        print('Warning: proceedings.pdf was not found, skipping', file=sys.stderr)

    proceedings_pdf_dest_path = None
    if proceedings_pdf_src_path is not None:
        proceedings_pdf_dest_path = str(
            pdfs_dest_dir / f'{collection_id}-{volume_name}.pdf'
        )
        maybe_copy(proceedings_pdf_src_path, proceedings_pdf_dest_path)

    volume[0] = {
        'anthology_id': f'{collection_id}-{volume_name}.0',
        'attachments': [],
        'archival': True,
    }

    frontmatter_src_path = None
    for path in [
        meta['path'] / 'front_matter.pdf',
        meta['path'] / 'watermarked_pdfs' / 'front_matter.pdf',
        meta['path'] / 'watermarked_pdfs' / '0.pdf',
    ]:
        if path.exists():
            frontmatter_src_path = str(path)
            print(f'Found frontmatter at {frontmatter_src_path}', file=sys.stderr)
            break

    if frontmatter_src_path is not None:
        frontmatter_dest_path = str(
            pdfs_dest_dir / f'{collection_id}-{volume_name}.0.pdf'
        )
        maybe_copy(frontmatter_src_path, frontmatter_dest_path)
        volume[0]['pdf_src'] = frontmatter_src_path
        volume[0]['pdf_dest'] = frontmatter_dest_path

    paper_num = 0
    for paper in papers:
        assert 'archival' in paper.keys(), f"{paper['id']} is missing key 'archival'"
        paper_num += 1
        paper_id_full = f'{collection_id}-{volume_name}.{paper_num}'

        is_archival = paper['archival']
        volume[paper_num] = {
            'anthology_id': paper_id_full,
            'attachments': [],
            'archival': is_archival,
        }

        if not is_archival:
            continue

        assert 'file' in paper.keys(), f"{paper['id']} is missing key 'file'"
        paper_name = paper['file']
        paper_id = str(paper['id'])

        pdf_src_path = None
        if (pdfs_src_dir / paper_name).exists():
            pdf_src_path = str(pdfs_src_dir / paper_name)
        elif (pdfs_src_dir / f'{paper_id}.pdf').exists():
            pdf_src_path = str(pdfs_src_dir / f'{paper_id}.pdf')

        assert pdf_src_path, f"Couldn't find {paper_name} or {paper_id} in {pdfs_src_dir}"

        pdf_dest_path = str(pdfs_dest_dir / f'{paper_id_full}.pdf')
        maybe_copy(pdf_src_path, pdf_dest_path)

        volume[paper_num]['pdf_src'] = pdf_src_path
        volume[paper_num]['pdf_dest'] = pdf_dest_path

        if 'attachments' in paper:
            attachs_dest_dir = create_dest_path(attachments_dir, venue_name)
            attachs_src_dir = meta['path'] / 'attachments'

            for attachment in paper['attachments']:
                file_path_value = attachment.get('file', None)
                if file_path_value is None:
                    continue
                file_path = Path(file_path_value)

                attach_src_path = None
                for path in [
                    attachs_src_dir / file_path,
                    attachs_src_dir / file_path.name,
                ]:
                    if path.exists():
                        attach_src_path = str(path)
                        break
                if attach_src_path is None:
                    print(
                        f"Warning: paper {paper_id} attachment {file_path} not found, skipping",
                        file=sys.stderr,
                    )
                    continue

                attach_src_extension = attach_src_path.split('.')[-1]
                type_ = str(attachment['type']).replace(' ', '')
                file_name = f'{collection_id}-{volume_name}.{paper_num}.{type_}.{attach_src_extension}'
                attach_dest_path = os.path.join(attachs_dest_dir, file_name).replace(
                    ' ', ''
                )

                if Path(attach_src_path).exists():
                    maybe_copy(attach_src_path, attach_dest_path)
                    print(f'Attaching {attach_dest_path} ({type_}) to {paper_num}')
                    volume[paper_num]['attachments'].append(
                        {
                            'src': attach_src_path,
                            'dest': attach_dest_path,
                            'type': type_,
                        }
                    )

    return (
        volume,
        collection_id,
        volume_name,
        proceedings_pdf_src_path,
        proceedings_pdf_dest_path,
    )


def set_disambiguation_ids(
    name_specs: List[NameSpecification], anthology: Anthology
) -> None:
    for name_spec in name_specs:
        matches = anthology.people.get_by_name(name_spec.name)
        if len(matches) > 1:
            name_spec.id = matches[0].id


def pdf_reference_from_paths(
    anthology_id: str, src_path: str, dest_path: str
) -> PDFReference:
    if os.path.exists(dest_path):
        return PDFReference.from_file(dest_path)
    return PDFReference(name=anthology_id, checksum=compute_checksum_from_file(src_path))


def attachment_reference_from_paths(src_path: str, dest_path: str) -> AttachmentReference:
    if os.path.exists(dest_path):
        return AttachmentReference.from_file(dest_path)
    return AttachmentReference(
        name=os.path.basename(dest_path), checksum=compute_checksum_from_file(src_path)
    )


def create_volume_with_library(
    anthology: Anthology,
    volume_data: Dict[int, Dict[str, Any]],
    collection_id: str,
    volume_name: str,
    meta: Dict[str, Any],
    papers: List[Dict[str, Any]],
    proceedings_pdf_src_path: Optional[str],
    proceedings_pdf_dest_path: Optional[str],
    ingest_date: str,
    is_workshop: bool,
) -> None:
    venue_name = meta['anthology_venue_id'].lower()

    collection = anthology.get_collection(collection_id)
    if collection is None:
        collection = anthology.collections.create(collection_id)

    if collection.get(volume_name) is not None:
        del collection[volume_name]
        collection.is_modified = True

    editors = [namespec_from_author(author) for author in meta['editors']]
    set_disambiguation_ids(editors, anthology)

    venue_ids = [venue_name]
    if is_workshop:
        venue_ids.append('ws')

    volume_kwargs: Dict[str, Any] = {
        'id': volume_name,
        'title': normalize_latex_title(meta['book_title']) or meta['book_title'],
        'year': str(meta['year']),
        'type': VolumeType.PROCEEDINGS,
        'ingest_date': ingest_date,
        'editors': editors,
        'venue_ids': venue_ids,
        'publisher': meta.get('publisher'),
        'address': meta.get('location'),
        'month': meta.get('month'),
    }

    if 'isbn' in meta and meta['isbn']:
        volume_kwargs['isbn'] = str(meta['isbn'])

    if proceedings_pdf_src_path is not None and proceedings_pdf_dest_path is not None:
        volume_kwargs['pdf'] = pdf_reference_from_paths(
            anthology_id=f'{collection_id}-{volume_name}',
            src_path=proceedings_pdf_src_path,
            dest_path=proceedings_pdf_dest_path,
        )

    volume_obj = collection.create_volume(**volume_kwargs)

    frontmatter_kwargs: Dict[str, Any] = {
        'id': '0',
        'type': PaperType.FRONTMATTER,
        'title': normalize_latex_title(meta['book_title']) or meta['book_title'],
        'editors': editors,
    }

    frontmatter = volume_data.get(0, {})
    if 'pdf_src' in frontmatter and 'pdf_dest' in frontmatter:
        frontmatter_kwargs['pdf'] = pdf_reference_from_paths(
            anthology_id=f'{collection_id}-{volume_name}.0',
            src_path=frontmatter['pdf_src'],
            dest_path=frontmatter['pdf_dest'],
        )

    volume_obj.create_paper(**frontmatter_kwargs)

    for paper_num, volume_entry in sorted(volume_data.items()):
        if paper_num == 0:
            continue
        if not volume_entry['archival']:
            print(f'Skipping non-archival paper #{paper_num}', file=sys.stderr)
            continue

        paper = papers[paper_num - 1]
        title = normalize_latex_title(paper.get('title'))

        abstract = paper.get('abstract')
        if abstract is not None:
            abstract = abstract.replace('\n', '')
            abstract = normalize_abstract(abstract)

        authors = [namespec_from_author(author) for author in paper.get('authors', [])]
        set_disambiguation_ids(authors, anthology)

        kwargs: Dict[str, Any] = {
            'id': str(paper_num),
            'title': title,
            'authors': authors,
            'pages': paper.get('pages'),
            'pdf': pdf_reference_from_paths(
                anthology_id=volume_entry['anthology_id'],
                src_path=volume_entry['pdf_src'],
                dest_path=volume_entry['pdf_dest'],
            ),
        }

        if abstract:
            kwargs['abstract'] = abstract

        attachment_refs = []
        for attachment in volume_entry['attachments']:
            if 'copyright' in attachment['type']:
                continue
            attachment_refs.append(
                (
                    attachment['type'],
                    attachment_reference_from_paths(
                        src_path=attachment['src'],
                        dest_path=attachment['dest'],
                    ),
                )
            )
        if attachment_refs:
            kwargs['attachments'] = attachment_refs

        volume_obj.create_paper(**kwargs)


@click.command()
@click.option(
    '-i',
    '--ingestion_dir',
    help='Directory contains proceedings need to be ingested',
)
@click.option(
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
    default=os.path.join(os.path.dirname(sys.argv[0]), '..'),
    help='Root path of ACL Anthology Github repo.',
)
@click.option(
    '-d',
    '--ingest_date',
    default=f'{datetime.now().year}-{datetime.now().month:02d}-{datetime.now().day:02d}',
    help='Ingestion date',
)
@click.option(
    '-w',
    '--workshop',
    is_flag=True,
    default=False,
    help='Event is a workshop (add workshop venue tag)',
)
@click.option(
    '-p',
    '--parent-event',
    default=None,
    help='Event ID (e.g., naacl-2025) workshop was colocated with',
)
def main(
    ingestion_dir,
    pdfs_dir,
    attachments_dir,
    anthology_dir,
    ingest_date,
    workshop,
    parent_event,
):
    anthology_datadir = Path(anthology_dir) / 'data'
    anthology = Anthology(datadir=anthology_datadir)

    anthology.collections.load()
    anthology.venues.load()
    anthology.people.load()

    volume_full_id, meta = process_proceeding(ingestion_dir, anthology)

    papers = parse_paper_yaml(ingestion_dir)
    print(
        'Found',
        len([p for p in papers if p['archival']]),
        'archival papers',
        file=sys.stderr,
    )

    papers = add_page_numbers(papers, ingestion_dir)

    (
        volume_data,
        collection_id,
        volume_name,
        proceedings_pdf_src_path,
        proceedings_pdf_dest_path,
    ) = copy_pdf_and_attachment(meta, pdfs_dir, attachments_dir, papers)

    create_volume_with_library(
        anthology=anthology,
        volume_data=volume_data,
        collection_id=collection_id,
        volume_name=volume_name,
        meta=meta,
        papers=papers,
        proceedings_pdf_src_path=proceedings_pdf_src_path,
        proceedings_pdf_dest_path=proceedings_pdf_dest_path,
        ingest_date=ingest_date,
        is_workshop=workshop,
    )

    if parent_event is not None:
        anthology.events.load()
        event = anthology.get_event(parent_event)
        if event is None:
            print(f"No event node with id '{parent_event}' found", file=sys.stderr)
            sys.exit(1)

        if anthology.get_volume(volume_full_id) is None:
            print(f"No such ingested volume {volume_full_id}", file=sys.stderr)
            sys.exit(1)

        existing = {event_id for (event_id, _) in event.colocated_ids}
        if any(collection_id == c and volume_name == v for (c, v, _) in existing):
            print(
                f'Event {volume_full_id} already listed as colocated with {parent_event}, skipping',
                file=sys.stderr,
            )
        else:
            event.add_colocated(volume_full_id, type_=EventLink.EXPLICIT)
            print(
                f'Created event entry in {parent_event} for {volume_full_id}',
                file=sys.stderr,
            )

    anthology.save_all()


if __name__ == '__main__':
    main()
