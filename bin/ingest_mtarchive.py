#!/usr/bin/env python3
"""
Takes a conference TSV file and, optionally, a conference metadata
file, and creates the Anthology XML in the ACL Anthology repository.
This file can then be added to the repo and committed.

Example usage:

- First, fork [the ACL Anthology](https://github.com/acl-org/acl-anthology) to your Github account, and clone it to your drive
- Grab one of the [conference TSV files](https://drive.google.com/drive/u/0/folders/1hC7FDlsXWVM2HSYgdluz01yotdEd0zW8)
- Export the [conference list file](https://docs.google.com/spreadsheets/d/1fpxmdV_BPwR6BQHyU9VJQxXeSOmy4__5nQCHBEviyAw/edit#gid=0) to conference-meta.tsv

Then run it as

    scripts/ingest_tsv.py [--anthology /path/to/anthology] eamt/eamt.1997.tsv conference-metadata.tsv

this will create a file `/path/to/anthology/data/xml/1997.eamt.xml`.
You can then commit this to your Anthology repo, push to your Github, and create a PR.

This was used for ingesting many of the conferences in the MT Archive.

Author: Matt Post
March 2020
"""

import csv
import lxml.etree as etree
import os
import shutil
import ssl
import subprocess
import sys
import urllib.request

from anthology.utils import (
    make_simple_element,
    indent,
    compute_hash_from_file,
    retrieve_url,
)
from datetime import datetime
from normalize_anth import normalize


def extract_pages(source_path, page_range, local_path):
    if os.path.exists(local_path):
        print(f"{local_path} already exists, not re-extracting", file=sys.stderr)
        return True
    if not os.path.exists(source_path):
        print(f"{source_path} does not exists", file=sys.stderr)
        raise Exception(f"Could not extract pdf")
    try:
        if "--" in page_range:
            page_range = page_range.replace("--", "-")
        page_range = ' A'.join(page_range.split(','))
        print(
            f"-> Extracting pages {page_range} from {source_path} to {local_path}",
            file=sys.stderr,
        )
        command = [f"pdftk A={source_path} cat {page_range} output {local_path}"]
        print(command, file=sys.stderr)
        subprocess.check_call(command, shell=True)
    except ssl.SSLError:
        raise Exception(f"Could not extract pdf")

    return True


def main(args):
    year, venue, _ = os.path.basename(args.tsv_file.name).split(".")

    # Set the volume name from the collection file, or default to 1
    # The file name is either "2012.eamt.tsv" or "2012.eamt-main.tsv".
    # The default volume name is "1".
    if "-" in venue:
        venue, volume_id = venue.split("-")
    else:
        volume_id = "1"

    collection_id = f"{year}.{venue}"

    tree = etree.ElementTree(
        make_simple_element("collection", attrib={"id": collection_id})
    )

    now = datetime.now()
    today = f"{now.year}-{now.month:02d}-{now.day:02d}"

    volume = make_simple_element("volume", attrib={"id": volume_id, "ingest-date": today})
    tree.getroot().insert(0, volume)

    # Location of entire-proceedings PDF
    proceedings_pdf = args.proceedings

    # Create the metadata for the paper
    meta = None
    for row in csv.DictReader(args.meta_file, delimiter=args.delimiter):
        current_collection_id = f"{row['Year']}.{row['Conference code']}"
        if current_collection_id == collection_id:
            meta = make_simple_element("meta", parent=volume)
            make_simple_element("booktitle", row["Conference title"], parent=meta)
            make_simple_element("publisher", row["Publisher"], parent=meta)
            make_simple_element("address", row["Location"], parent=meta)
            make_simple_element("month", row["Dates held"], parent=meta)
            make_simple_element("year", row["Year"], parent=meta)

            url = row["URL"]

            if url.endswith(".pdf"):
                if proceedings_pdf:
                    print(
                        "Overriding --proceedings with proceedings PDF found in conference list",
                        file=sys.stderr,
                    )
                proceedings_pdf = url

            elif "Complete PDF" in row and row["Complete PDF"] != "":
                proceedings_pdf = row["Complete PDF"]

            # volume PDF
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

            if row["Editors"] != "" and "?" not in row["Editors"]:
                editors = row["Editors"].split(" and ")
                for editor_name in editors:
                    editor = make_simple_element("editor", parent=meta)
                    if ", " in editor_name:
                        last, first = editor_name.split(", ")
                    else:
                        first, last = (
                            ' '.join(editor_name.split()[:-1]),
                            editor_name.split()[-1],
                        )
                    make_simple_element("first", first, parent=editor)
                    make_simple_element("last", last, parent=editor)
            break
    else:
        print(
            f"Couldn't find conference code {collection_id} in 'Conference code' field of metadata file {args.meta_file.name}",
            file=sys.stderr,
        )
        sys.exit(1)

    paperid = 0
    # Create entries for all the papers
    for row in csv.DictReader(args.tsv_file, delimiter=args.delimiter):
        pages = row.get("Pagenumbers", None)

        title_text = row["Title"]

        # The first row might be front matter (needs a special name)
        if title_text == "Frontmatter" and paperid == 0:
            paper = make_simple_element("frontmatter", parent=volume)

        else:
            paperid += 1
            paper = make_simple_element(
                "paper", attrib={"id": str(paperid)}, parent=volume
            )
            # Only make the title for not-the-frontmatter
            make_simple_element("title", title_text, parent=paper)

            author_list = row["Authors"].split(" and ")
            for author_name in author_list:
                if author_name == "":
                    continue
                author = make_simple_element("author", parent=paper)
                if ", " in author_name:
                    last, first = author_name.split(", ")
                else:
                    first, last = (
                        ' '.join(author_name.split()[:-1]),
                        author_name.split()[-1],
                    )
                make_simple_element("first", first, parent=author)
                make_simple_element("last", last, parent=author)

        if pages is not None:
            make_simple_element("pages", pages, parent=paper)

        # Find the PDF, either listed directly, or extracted from the proceedings PDF
        anth_id = f"{collection_id}-{volume_id}.{paperid}"
        pdf_local_path = os.path.join(args.anthology_files_path, venue, f"{anth_id}.pdf")
        url = None
        if "Pdf" in row and row["Pdf"] != "":
            if retrieve_url(row["Pdf"], pdf_local_path):
                url = anth_id

        elif "pages in pdf" in row:
            pdf_pages = row["pages in pdf"]
            extract_pages(proceedings_pdf, pdf_pages, pdf_local_path)
            url = anth_id

        if url is not None:
            checksum = compute_hash_from_file(pdf_local_path)

            make_simple_element("url", url, attrib={"hash": checksum}, parent=paper)

        if "Abstract" in row:
            make_simple_element("abstract", row["Abstract"], parent=paper)

        if "Presentation" in row:
            url = row["Presentation"]
            if url is not None and url != "" and url != "None":
                extension = row["Presentation"].split(".")[-1]
                name = f"{anth_id}.Presentation.{extension}"
                local_path = os.path.join(
                    args.anthology_files_path,
                    "..",
                    "attachments",
                    venue,
                    name,
                )
                if retrieve_url(row["Presentation"], local_path):
                    checksum = compute_hash_from_file(local_path)
                    make_simple_element(
                        "attachment",
                        name,
                        attrib={"type": "presentation", "hash": checksum},
                        parent=paper,
                    )

        # Normalize
        for node in paper:
            normalize(node, informat="latex")

    indent(tree.getroot())

    # Write the file to disk: acl-anthology/data/xml/{collection_id}.xml
    collection_file = os.path.join(args.anthology, "data", "xml", f"{collection_id}.xml")
    tree.write(collection_file, encoding="UTF-8", xml_declaration=True, with_tail=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('tsv_file', type=argparse.FileType("r"))
    parser.add_argument(
        'meta_file', type=argparse.FileType("r"), help="Path to conference metadata file"
    )
    parser.add_argument(
        '--anthology',
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
    parser.add_argument('--proceedings', help="Path to PDF with conference proceedings")
    parser.add_argument('--frontmatter', action="store_true")
    parser.add_argument("--force", "-f", action="store_true")
    args = parser.parse_args()

    main(args)
