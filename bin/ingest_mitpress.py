#! /usr/bin/env python3
"""
Convert MIT Press XML files for CL and TACL to Anthology XML.

version 0.4 - now updates XML directly, skips existing papers, sorts by page number
version 0.3 - produces anthology ID in new format 2020.cl-1.1

Example usage: unpack all the ZIP files from MIT Press. You'll have
a directory like this:

    ./tacl_a_00296
    |-- tacl_a_00296.pdf
    |-- tacl_a_00296.xml
    ./tacl_a_00297
    |-- tacl_a_00297.pdf
    |-- tacl_a_00297.xml
    ./tacl_a_00298
    |-- tacl_a_00298.pdf
    |-- tacl_a_00298.xml
    ...

Then, in that directory, run:

    /path/to/anthology/tacl_cl_parser.py .

This will

* infer the path of, then update or create the XML file, skipping existing papers
* copy new PDFs where they can be bundled up or rsynced over.

It assumes that you are working within a single collection (e.g., a single XML
file), but there can be multiple volumes (like for CL).

Warning (August 2020): not yet tested with CL, but should work!

Authors: Arya D. McCarthy, Matt Post
"""
import logging
import os
import shutil
import lxml.etree as etree

from pathlib import Path
from typing import List, Optional, Tuple

from normalize_anth import normalize
from anthology.utils import make_simple_element, indent, compute_hash_from_file

__version__ = "0.4"

TACL = "tacl"
CL = "cl"


def parse_args():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("year_root", metavar="FOLDER", type=Path)
    anthology_path = os.path.join(os.path.dirname(sys.argv[0]), "..")
    parser.add_argument(
        "--anthology-dir",
        "-r",
        default=anthology_path,
        help="Root path of ACL Anthology Github repo. Default: %(default)s.",
    )
    pdfs_path = os.path.join(os.environ["HOME"], "anthology-files")
    parser.add_argument(
        "--pdfs-dir",
        "-p",
        default=pdfs_path,
        help="Root path for placement of PDF files",
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose", action="store_const", const=logging.DEBUG, default=logging.INFO
    )
    verbosity.add_argument(
        "-q", "--quiet", dest="verbose", action="store_const", const=logging.WARNING
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s v{__version__}")

    args = parser.parse_args()
    args.year_root = args.year_root.resolve()  # Get absolute path.
    # args.outfile = argparse.FileType(mode='w')(args.outfile)
    return args


def collapse_spaces(text: str) -> str:
    return " ".join(text.split())


def get_volume_info(xml: Path) -> str:
    logging.info("Getting volume info from {}".format(xml))
    # So far, their XML for the volume doesn't play nicely with xml.etree. Thus, we hack.
    paper = etree.Element("paper")
    paper.attrib["id"] = "1000"  # hard-code because there's only one collection.

    volume_text = xml.stem.split(".")[-1]
    title_text = "Transactions of the Association for Computational Linguistics"

    title = etree.Element("title")
    title.text = "{}, Volume {}".format(title_text, volume_text)
    paper.append(title)

    year_text = xml.stem.split(".")[1]
    year = etree.Element("year")
    year.text = year_text
    paper.append(year)

    return paper


def get_paperid(xml: Path, count: int, issue_count: int) -> str:
    basename = xml.stem
    assert int(issue_count) < 10
    assert 0 < count < 1000
    # for i in range(1, 4+1):
    #     assert basename[-i] in [str(x) for x in range(10)], basename
    return f"{issue_count}.{count}"  # after dash in new anth id


def get_title(xml_front_node: etree.Element) -> str:
    article_meta = xml_front_node.find("article-meta")
    title_group = article_meta.find("title-group")
    title = title_group.find("article-title")
    title_text = collapse_spaces("".join(title.itertext()))
    return title_text


def get_year(xml_front_node: etree.Element) -> str:
    article_meta = xml_front_node.find("article-meta")
    pub_date = article_meta.find("pub-date")
    year_text = pub_date.find("year").text
    return year_text


def get_month(xml_front_node: etree.Element) -> str:
    article_meta = xml_front_node.find("article-meta")
    pub_date = article_meta.find("pub-date")
    try:
        month_id = pub_date.find("month").text
    except AttributeError:
        return None
    months = [
        None,
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    month_text = months[int(month_id)]
    return month_text


def get_abstract(xml_front_node: etree.Element) -> str:
    article_meta = xml_front_node.find("article-meta")
    abstract = article_meta.find("abstract")
    if abstract is not None:
        abstract_text = collapse_spaces("".join(abstract.itertext()))
        return abstract_text
    else:
        return None


def get_authors(xml_front_node: etree.Element) -> List[Tuple[str, str]]:
    article_meta = xml_front_node.find("article-meta")
    contrib_group = article_meta.find("contrib-group")
    authors = []
    for author in contrib_group.findall("contrib"):
        string_name = author.find("string-name")
        try:
            given_names = string_name.find("given-names").text
        except AttributeError:
            given_names = ""  # Special case for Mausam, and potentially Madonna.
        surname = string_name.find("surname").text
        try:
            suffix = string_name.find("suffix").text
            surname = surname + " " + suffix
        except AttributeError:
            pass
        authors.append((given_names, surname))
    return authors


def get_pages(xml_front_node: etree.Element) -> Tuple[str, str]:
    article_meta = xml_front_node.find("article-meta")
    fpage = article_meta.find("fpage")
    lpage = article_meta.find("lpage")
    return fpage.text, lpage.text


def get_doi(xml_front_node: etree.Element) -> str:
    article_meta = xml_front_node.find("article-meta")
    doi_ = article_meta.find("*[@pub-id-type='doi']")
    return doi_.text


def get_article_journal_info(xml_front_node: etree.Element, is_tacl: bool) -> str:
    journal_meta = xml_front_node.find("journal-meta")
    journal_title_group = journal_meta.find("journal-title-group")
    journal_title = journal_title_group.find("journal-title")
    journal_title_text = journal_title.text

    article_meta = xml_front_node.find("article-meta")
    volume = article_meta.find("volume")

    # Fixes
    journal_title_text = " ".join(
        journal_title_text.split()
    )  # Sometimes it's split onto two lines...
    journal_title_text = (
        journal_title_text.replace(  # Somebody in 2018 didn't know our name?
            "Association of Computational Linguistics",
            "Association for Computational Linguistics",
        )
    )
    volume_text = volume.text.lstrip(
        "0"
    )  # Somebody brilliant decided that 2018 would be "06" instead of "6"

    if is_tacl:
        issue_text = None
        string_date_text = None
        format_string = "{journal}, Volume {volume}"
    else:
        issue = article_meta.find("issue")
        issue_text = issue.text

        pub_date = article_meta.find("pub-date")
        string_date = pub_date.find("string-date")
        string_date_text = string_date.text

        format_string = "{journal}, Volume {volume}, Issue {issue} - {date}"

    data = dict(
        journal=journal_title_text,
        volume=volume_text,
        issue=issue_text,
        date=string_date_text,
    )
    logging.debug(format_string.format(**data))
    return format_string.format(**data), issue_text


def process_xml(xml: Path, is_tacl: bool) -> Optional[etree.Element]:
    logging.info("Reading {}".format(xml))

    tree = etree.parse(str(xml))
    root = tree.getroot()
    front = root.find("front")

    info, issue = get_article_journal_info(front, is_tacl)

    paper = etree.Element("paper")

    title_text = get_title(front)
    title = etree.Element("title")
    title.text = title_text
    paper.append(title)

    authors = get_authors(front)
    for given_names, surname in authors:
        first = etree.Element("first")
        first.text = given_names

        last = etree.Element("last")
        last.text = surname

        author = etree.Element("author")
        author.append(first)
        author.append(last)

        paper.append(author)

    doi_text = get_doi(front)
    doi = etree.Element("doi")
    doi.text = doi_text
    paper.append(doi)

    abstract_text = get_abstract(front)
    if abstract_text:
        make_simple_element("abstract", abstract_text, parent=paper)

    pages_tuple = get_pages(front)
    pages = etree.Element("pages")
    pages.text = "–".join(pages_tuple)  # en-dash, not hyphen!
    paper.append(pages)

    return paper, info, issue


def issue_info_to_node(
    issue_info: str, year_: str, volume_id: str, is_tacl: bool
) -> etree.Element:
    """Creates the meta block for a new issue / volume"""
    node = etree.Element("meta")

    assert int(year_)

    title_text = issue_info
    title = etree.Element("booktitle")
    title.text = title_text
    node.append(title)

    if not is_tacl:
        month_text = issue_info.split()[-2]  # blah blah blah month year
        if not month_text in {
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        }:
            logging.error("Unknown month: " + month_text)
        month = etree.Element("month")
        month.text = month_text
        node.append(month)

    year = etree.Element("year")
    year.text = year_
    node.append(year)

    return node


if __name__ == "__main__":
    import sys

    if sys.version_info < (3, 6):
        sys.stderr.write("Python >=3.6 required.\n")
        sys.exit(1)

    args = parse_args()
    logging.basicConfig(level=args.verbose)

    is_tacl = "tacl" in args.year_root.stem

    venue = TACL if is_tacl else CL  # J for CL, Q for TACL.
    year = args.year_root.stem.split(".")[1]
    year_suffix = year[-2:]  # Feels hacky, too.

    collection_id = year + "." + venue

    collection_file = os.path.join(
        args.anthology_dir, "data", "xml", f"{collection_id}.xml"
    )
    if os.path.exists(collection_file):
        collection = etree.parse(collection_file).getroot()
    else:
        collection = make_simple_element("collection", attrib={"id": collection_id})

    tacl_glob = "tacl.20*.*/tacl.20*.*.xml"
    # volume_info = get_volume_info(list(args.year_root.glob("*.*.*/*.*.*.xml"))[0])
    # volume.append(volume_info)

    pdf_destination = Path(args.pdfs_dir)
    pdf_destination = pdf_destination / "pdf" / venue
    pdf_destination.mkdir(parents=True, exist_ok=True)

    previous_issue_info = None

    papers = []
    for xml in sorted(args.year_root.glob("*_a_*/*.xml")):
        # print(xml)

        papernode, issue_info, issue = process_xml(xml, is_tacl)
        if papernode is None or papernode.find("title").text.startswith("Erratum: “"):
            continue

        pdf_path = xml.with_suffix(".pdf")
        if not pdf_path.is_file():
            logging.error("Missing pdf for " + pdf_path)
            sys.exit(1)

        papers.append((papernode, pdf_path, issue_info, issue))

    # MIT Press does assign its IDs in page order, so we have to sort by page
    def sort_papers_by_page(paper_tuple):
        papernode = paper_tuple[0]
        startpage = int(papernode.find("./pages").text.split("–")[0])
        return startpage

    paper_id = 1  # Stupid non-enumerate counter because of "Erratum: " papers interleaved with real ones.
    for papernode, pdf_path, issue_info, issue in sorted(papers, key=sort_papers_by_page):
        issue = issue or "1"
        if issue_info != previous_issue_info:
            # Emit the new volume info before the paper.
            logging.info(f"New issue")
            logging.info(f"{issue_info} vs. {previous_issue_info}")
            previous_issue_info = issue_info

            # Look for node in tree, else create it
            volume = collection.find(f'./volume[@id="{issue}"]')
            if volume is None:
                # xml volume = journal issue
                volume = make_simple_element(
                    "volume", attrib={"id": issue}, parent=collection
                )
                volume.append(
                    issue_info_to_node(issue_info, year, collection_id, is_tacl)
                )
            else:
                for paper in volume.findall(".//paper"):
                    paper_id = max(paper_id, int(paper.attrib["id"]))
                    print(f"Setting paper_id to {paper_id}")
                paper_id += 1

        anth_id = f"{collection_id}-{issue}.{paper_id}"

        # Check if the paper is already present in the volume
        doi_text = papernode.find("./doi").text
        doi_node = collection.xpath(f'.//doi[text()="{doi_text}"]')
        if len(doi_node):
            logging.info(
                f"Skipping existing paper {anth_id}/{doi_text} with title {papernode.find('title').text}"
            )
            continue

        papernode.attrib["id"] = f"{paper_id}"

        destination = pdf_destination / f"{anth_id}.pdf"
        print(f"Copying {pdf_path} to {destination}")
        shutil.copyfile(pdf_path, destination)
        checksum = compute_hash_from_file(pdf_path)

        url_text = anth_id
        url = etree.Element("url")
        url.attrib["hash"] = checksum
        url.text = url_text
        papernode.append(url)

        # Normalize
        for oldnode in papernode:
            normalize(oldnode, informat="latex")
        volume.append(papernode)

        paper_id += 1

    indent(collection)  # from anthology.utils
    et = etree.ElementTree(collection)
    et.write(collection_file, encoding="UTF-8", xml_declaration=True, with_tail=True)
