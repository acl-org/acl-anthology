#!/usr/bin/env python3
"""
Takes a conference TSV file and paths_to_all_papers/presentations, and creates the Anthology XML in the ACL Anthology repository.
This file can then be added to the repo and committed.

Expects fields name like BibTeX files.

Example usage:

    python bin/ingest_tsv.py --tsv-file ~/Dropbox/ingests/2022/2022-09-03-amta/ACL_Delivery_2022.amta/2022.amta-upg/2022.amta-upg.tsv --anthology-dir PATH_TO_ANTH_DIR amta upg 2022 --proceedings-pdf ~/Dropbox/ingests/2022/2022-09-03-amta/ACL_Delivery_2022.amta/2022.amta-upg/2022.amta-upg.pdf --source_path ~/Dropbox/ingests/2022/2022-09-03-amta/ACL_Delivery_2022.amta/2022.amta-upg/

where the tsv has TSV fields:

* author
    - author names should be listed as LastName FirstName, LastName FirstName, LastName FirstName
* title
* booktitle
* month
* year
* address
* publisher
* pages
* pdf
* presentation (optional)

source_path: the root dir that contains
* the tsv file
* a Paper dir that contains all the paper pdfs (including frontmatter pdf, excluding the full proceedings pdf). Paper pdf name should correspond to the pdf column value in the tsv file.
* a Presentation dir (optional) that contains all the presentation pdfs. Presentation pdf name should correspond to the presentation column value in the tsv file.
* the full proceedings pdf (--proceedings-pdf)

Author: Matt Post, Xinru Yan
Last updated Sept 2022
"""

import csv
import lxml.etree as etree
import os
import sys

from anthology.utils import (
    make_simple_element,
    indent,
    compute_hash_from_file,
    retrieve_url,
)
from datetime import datetime
from normalize_anth import normalize
from likely_name_split import NameSplitter
from ingest_mtarchive import extract_pages


def main(args):
    year = args.year
    venue = args.venue
    volume_id = args.volume
    collection_id = f"{year}.{venue}"
    source_path_prefix = args.source_path

    splitter = NameSplitter(anthology_dir=args.anthology_dir)

    collection_file = os.path.join(
        args.anthology_dir, "data", "xml", f"{collection_id}.xml"
    )
    if os.path.exists(collection_file):
        tree = etree.parse(collection_file)
    else:
        tree = etree.ElementTree(
            make_simple_element("collection", attrib={"id": collection_id})
        )

    now = datetime.now()
    today = f"{now.year}-{now.month:02d}-{now.day:02d}"

    volume_node = tree.getroot().find(f"./volume[@id='{volume_id}']")
    if volume_node is not None:
        tree.getroot().remove(volume_node)

    volume = make_simple_element(
        "volume", attrib={"id": volume_id, "ingest-date": today}, parent=tree.getroot()
    )

    if not os.path.exists(collection_id):
        print(f"Creating {collection_id}", file=sys.stderr)
        os.makedirs(collection_id)

    # Create entries for all the papers
    for paperid, row in enumerate(
        csv.DictReader(args.tsv_file, delimiter=args.delimiter)
    ):
        pages = row.get("pages", None)

        if paperid == 0:
            meta = make_simple_element("meta", parent=volume)
            make_simple_element("booktitle", row["booktitle"], parent=meta)
            make_simple_element("publisher", row["publisher"], parent=meta)
            make_simple_element("address", row["address"], parent=meta)
            make_simple_element("month", row["month"], parent=meta)
            make_simple_element("year", year, parent=meta)

            editors = row["author"].split(", ")
            row["author"] = ""
            for editor_name in editors:
                editor = make_simple_element("editor", parent=meta)
                surname, givenname = splitter.best_split(editor_name)
                make_simple_element("first", givenname, parent=editor)
                make_simple_element("last", surname, parent=editor)

            # volume PDF
            proceedings_pdf = args.proceedings_pdf
            if proceedings_pdf is not None:
                volume_anth_id = f"{collection_id}-{volume_id}"
                pdf_local_path = os.path.join(
                    args.anthology_files_path, venue, f"{volume_anth_id}.pdf"
                )
                retrieve_url(proceedings_pdf, pdf_local_path)
                checksum = compute_hash_from_file(pdf_local_path)
                make_simple_element(
                    "url", volume_anth_id, attrib={"hash": checksum}, parent=meta
                )
                proceedings_pdf = pdf_local_path

        title_text = row["title"]

        # The first row might be front matter (needs a special name)
        if paperid == 0 and title_text.lower() in ["frontmatter", "front matter"]:
            paper = make_simple_element("frontmatter", parent=volume)
        else:
            if paperid == 0:
                # Not frontmatter, so paper 1
                paperid += 1

            paper = make_simple_element(
                "paper", attrib={"id": str(paperid)}, parent=volume
            )
            # Only make the title for not-the-frontmatter
            make_simple_element("title", title_text, parent=paper)

        author_list = row["author"].split(", ")

        for author_name in author_list:
            if author_name == "":
                continue
            author = make_simple_element("author", parent=paper)
            surname, givenname = splitter.best_split(author_name)
            make_simple_element("first", givenname, parent=author)
            make_simple_element("last", surname, parent=author)

        if pages is not None and pages != "":
            make_simple_element("pages", pages, parent=paper)

        # Find the PDF, either listed directly, or extracted from the proceedings PDF
        anth_id = f"{collection_id}-{volume_id}.{paperid}"
        pdf_local_path = os.path.join(args.anthology_files_path, venue, f"{anth_id}.pdf")
        url = None
        if "pdf" in row and row["pdf"] != "" and row["pdf"] is not None:
            pdf_source_path = source_path_prefix + 'Papers/' + row["pdf"]
            if retrieve_url(pdf_source_path, pdf_local_path):
                url = anth_id
            else:
                print("Can't find", row["pdf"])

        elif "pages in pdf" in row:
            pdf_pages = row["pages"]
            extract_pages(proceedings_pdf, pdf_pages, pdf_local_path)
            url = anth_id

        if url is not None:
            checksum = compute_hash_from_file(pdf_local_path)

            make_simple_element("url", url, attrib={"hash": checksum}, parent=paper)

        if "abstract" in row and row["abstract"] != "":
            make_simple_element("abstract", row["abstract"], parent=paper)

        if "presentation" in row:
            if (
                row["presentation"] is not None
                and row["presentation"] != ""
                and row["presentation"] != "None"
            ):
                presentation_source_path = (
                    source_path_prefix + 'Presentations/' + row["presentation"]
                )
                extension = row["presentation"].split(".")[-1]
                name = f"{anth_id}.Presentation.{extension}"
                local_path = os.path.join(
                    args.anthology_files_path,
                    "..",
                    "attachments",
                    venue,
                    name,
                )
                if retrieve_url(presentation_source_path, local_path):
                    make_simple_element(
                        "attachment",
                        name,
                        attrib={
                            "type": "presentation",
                            "hash": compute_hash_from_file(local_path),
                        },
                        parent=paper,
                    )

        # Normalize
        for node in paper:
            normalize(node, informat="latex")

    indent(tree.getroot())

    # Write the file to disk: acl-anthology/data/xml/{collection_id}.xml
    tree.write(collection_file, encoding="UTF-8", xml_declaration=True, with_tail=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--tsv-file', nargs="?", default=sys.stdin, type=argparse.FileType("r")
    )
    parser.add_argument(
        '--anthology-dir',
        default=f"{os.environ.get('HOME')}/code/acl-anthology",
        help="Path to Anthology repo (cloned from https://github.com/acl-org/acl-anthology)",
    )
    parser.add_argument(
        '--anthology-files-path',
        default=f"{os.environ.get('HOME')}/anthology-files/pdf",
        help="Path to Anthology files (Default: ~/anthology-files",
    )
    parser.add_argument(
        "--delimiter", "-d", default="\t", help="CSV file delimiter (default: TAB)"
    )
    parser.add_argument(
        '--proceedings-pdf', help="Path to PDF with conference proceedings"
    )
    parser.add_argument("venue", help="Venue code, e.g., acl")
    parser.add_argument("volume", help="Volume name, e.g., main or 1")
    parser.add_argument("year", help="Full year, e.g., 2020")
    parser.add_argument(
        '--source_path',
        default=sys.stdin,
        help="the source dir for all pdfs and presentations",
    )
    args = parser.parse_args()

    main(args)
