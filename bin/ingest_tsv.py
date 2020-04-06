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
import ssl
import subprocess
import sys
import urllib.request

from anthology.utils import make_simple_element, indent
from normalize_anth import normalize


def download(remote_path, local_path):
    if os.path.exists(local_path):
        print(f"{local_path} already exists, not re-downloading", file=sys.stderr)
        return True
    local_dir = os.path.dirname(local_path)
    if not os.path.exists(local_dir):
        print(f"Creating directory {local_dir}", file=sys.stderr)
        os.makedirs(local_dir)
    try:
        print(f"-> Downloading file from {remote_path} to {local_path}", file=sys.stderr)
        with urllib.request.urlopen(remote_path) as url, open(
            local_path, mode="wb"
        ) as input_file_fh:
            input_file_fh.write(url.read())
    except ssl.SSLError:
        raise Exception(f"Could not download {remote_path} to {local_path}")
    except urllib.error.HTTPError:
        print(f"-> FAILED to download {remote_path}", file=sys.stderr)
        return False

    return True


def extract_pages(source_path, page_range, local_path):
    if os.path.exists(local_path):
        print(f"{local_path} already exists, not re-extracting", file=sys.stderr)
        return True
    if not os.path.exists(source_path):
        print(f"{source_path} does not exists", file=sys.stderr)
        raise Exception(f"Could not extract pdf")
    try:
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
    venue, year, _ = os.path.basename(args.tsv_file.name).split(".")

    collection_id = f"{year}.{venue}"

    tree = etree.ElementTree(
        make_simple_element("collection", attrib={"id": collection_id})
    )

    volume_id = "1"
    volume = make_simple_element("volume", attrib={"id": volume_id})
    tree.getroot().insert(0, volume)

    # Create the metadata for the paper
    meta = None
    for row in csv.DictReader(args.meta_file, delimiter=","):
        current_collection_id = f"{row['Year']}.{row['Conference code']}"
        if current_collection_id == collection_id:
            if row["Completed"] == "FALSE":
                if args.force:
                    print(
                        "Warning: Conference {collection_id} is not marked as completed.",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "Warning: Conference {collection_id} is not marked as completed and no -f, can't ingest.",
                        file=sys.stderr,
                    )
                    sys.exit(1)

            meta = make_simple_element("meta", parent=volume)
            make_simple_element("booktitle", row["Conference title"], parent=meta)
            make_simple_element("publisher", row["Publisher"], parent=meta)
            make_simple_element("address", row["Location"], parent=meta)
            make_simple_element("month", row["Dates held"], parent=meta)
            make_simple_element("year", row["Year"], parent=meta)
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

    if not os.path.exists(collection_id):
        print(f"Creating {collection_id}", file=sys.stderr)
        os.makedirs(collection_id)

    if args.frontmatter:
        start_id = 0
    else:
        start_id = 1

    # Create entries for all the papers
    for paperid, row in enumerate(
        csv.DictReader(args.tsv_file, delimiter='\t'), start_id
    ):
        pages = row.get("Pagenumbers", None)

        if paperid == 0:

            title_text = row["Title"]
            try:
                pdf = row["Pdf"]
            except KeyError:
                pdf = None
            frontmatter = make_simple_element("frontmatter", parent=volume)
            if pages is not None:
                make_simple_element("pages", pages, parent=frontmatter)

            url = f"{collection_id}-{volume_id}.{paperid}"
            pdf_local_path = os.path.join(args.anthology_files_path, venue, f"{url}.pdf")
            make_simple_element("url", url, parent=frontmatter)
            if not pdf is None:
                if not download(pdf, pdf_local_path):
                    pdf = None
            else:
                pdf_pages = row["pages in pdf"]
                extract_pages(args.proceedings, pdf_pages, pdf_local_path)
            continue

        title_text = row["Title"]
        author_list = row["Authors"].split(" and ")

        try:
            pdf = row["Pdf"]
        except KeyError:
            pdf = None

        paper = make_simple_element("paper", attrib={"id": str(paperid)}, parent=volume)

        make_simple_element("title", title_text, parent=paper)
        for author_name in author_list:
            if author_name == "":
                continue
            author = make_simple_element("author", parent=paper)
            if ", " in author_name:
                last, first = author_name.split(", ")
            else:
                first, last = ' '.join(author_name.split()[:-1]), author_name.split()[-1]
            make_simple_element("first", first, parent=author)
            make_simple_element("last", last, parent=author)

        if pages is not None:
            make_simple_element("pages", pages, parent=paper)

        url = f"{collection_id}-{volume_id}.{paperid}"
        pdf_local_path = os.path.join(args.anthology_files_path, venue, f"{url}.pdf")
        if not pdf is None:
            if not download(pdf, pdf_local_path):
                url = None

        elif "pages in pdf" in row:
            pdf_pages = row["pages in pdf"]
            extract_pages(args.proceedings, pdf_pages, pdf_local_path)

        else:
            url = None

        if url is not None:
            make_simple_element("url", url, parent=paper)

        if "Abstract" in row:
            make_simple_element("abstract", row["Abstract"], parent=paper)

        if "Presentation" in row and row["Presentation"] != "":
            extension = row["Presentation"].split(".")[-1]
            filename = f"{collection_id}-{volume_id}.{paperid}.Presentation.{extension}"
            make_simple_element("attachment", filename, attrib={"type": "presentation"})
            download(row["Presentation"], os.path.join(collection_id, filename))

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

    parser.add_argument('--proceedings', help="Path to PDF with conference proceedings")
    parser.add_argument('--frontmatter', action="store_true")
    parser.add_argument("--force", "-f", action="store_true")
    args = parser.parse_args()

    main(args)
