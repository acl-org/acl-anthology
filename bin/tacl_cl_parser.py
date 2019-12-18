#! /usr/bin/env python3
"""
Convert MIT Press XML files for TACL to Anthology XML.

Author: Arya D. McCarthy
"""
import logging
import shutil
import xml.etree.ElementTree as etree

from pathlib import Path
from typing import List, Optional, Tuple

__version__ = "0.1"

log = logging.getLogger(__name__ if __name__ != "__main__ " else Path(__file__).stem)


TACL = "Q"
CL = "J"

STANDARD_URL = "https://www.aclweb.org/anthology/{volume}-{paper}"


def parse_args():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("year_root", metavar="FOLDER", type=Path)
    parser.add_argument(
        "--outfile",
        "-o",
        default=sys.stdout.buffer,
        help="Output XML file (default stdout)",
    )
    parser.add_argument("--pdf_save_destination", default=None, type=Path)
    parser.add_argument("--old_version", default=None, type=Path, metavar="XML")

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
    log.info("Getting volume info from {}".format(xml))
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
    assert issue_count < 10
    assert 0 < count < 1000
    # for i in range(1, 4+1):
    #     assert basename[-i] in [str(x) for x in range(10)], basename
    return f"{issue_count}{count:03}"  # TACL is always QXX-1YYY.


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
    abstract_text = collapse_spaces("".join(abstract.itertext()))
    return abstract_text


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
    journal_title_text = journal_title_text.replace(  # Somebody in 2018 didn't know our name?
        "Association of Computational Linguistics",
        "Association for Computational Linguistics",
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
    log.debug(format_string.format(**data))
    return format_string.format(**data)


def process_xml(xml: Path, is_tacl: bool) -> Optional[etree.Element]:
    logging.info("Reading {}".format(xml))

    tree = etree.parse(xml)
    root = tree.getroot()
    front = root.find("front")

    info = get_article_journal_info(front, is_tacl)

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

    year_text = get_year(front)
    year = etree.Element("year")
    year.text = year_text
    paper.append(year)

    month_text = get_month(front)
    if month_text is not None:
        month = etree.Element("month")
        month.text = month_text
        paper.append(month)

    doi_text = get_doi(front)
    doi = etree.Element("doi")
    doi.text = doi_text
    paper.append(doi)

    abstract_text = get_abstract(front)
    abstract = etree.Element("abstract")
    abstract.text = abstract_text
    paper.append(abstract)

    pages_tuple = get_pages(front)
    pages = etree.Element("pages")
    pages.text = "–".join(pages_tuple)  # en-dash, not hyphen!
    paper.append(pages)

    return paper, info


def issue_info_to_node(
    issue_info: str, year_: str, volume_id: str, issue_counter: int, is_tacl: bool
) -> etree.Element:
    node = etree.Element("paper")
    node.attrib["id"] = f"{issue_counter}000"

    assert int(year_)

    title_text = issue_info
    title = etree.Element("title")
    title.text = title_text
    node.append(title)

    if not is_tacl:
        month_text = issue_info.split()[-2]  # blah blah blah month year
        assert month_text in {
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
        }
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

    prefix = TACL if is_tacl else CL  # J for CL, Q for TACL.
    year = args.year_root.stem.split(".")[1]
    year_suffix = year[-2:]  # Feels hacky, too.
    volume_id = prefix + year_suffix

    volume = etree.Element("volume")
    volume.attrib["id"] = volume_id

    tacl_glob = "tacl.20*.*/tacl.20*.*.xml"
    # volume_info = get_volume_info(list(args.year_root.glob("*.*.*/*.*.*.xml"))[0])
    # volume.append(volume_info)

    if args.pdf_save_destination:
        save_destination = args.pdf_save_destination
        write_to_here = save_destination / "pdf" / prefix / volume_id
        write_to_here.mkdir(parents=True, exist_ok=True)  # destination / Q / Q18

    if args.old_version:
        old_version = etree.parse(args.old_version)
        old_root = old_version.getroot()

    previous_issue_info, issue_count = None, 0

    i = 1  # Stupid non-enumerate counter because of "Erratum: " papers interleaved with real ones.
    for xml in sorted(args.year_root.glob("*_a_*/*.xml")):
        # print(xml)

        papernode, issue_info = process_xml(xml, is_tacl)
        if papernode is None or papernode.find("title").text.startswith("Erratum: “"):
            continue

        if issue_info != previous_issue_info:
            # Emit the new volume info before the paper.
            log.info(f"New issue; will number it {issue_count + 1}")
            log.info(f"{issue_info} vs. {previous_issue_info}")
            previous_issue_info, issue_count = issue_info, issue_count + 1
            volume.append(
                issue_info_to_node(issue_info, year, volume_id, issue_count, is_tacl)
            )
        paper_id = papernode.attrib["id"] = get_paperid(xml, i, issue_count)

        pdf = xml.with_suffix(".pdf")
        if not pdf.is_file():
            log.error("Missing pdf for " + xml.name)
        elif args.pdf_save_destination:
            destination = write_to_here / "{}-{}.pdf".format(volume_id, paper_id)
            shutil.copyfile(pdf, destination)

        url_text = STANDARD_URL.format(volume=volume_id, paper=paper_id)
        url = etree.Element("url")
        url.text = url_text
        papernode.append(url)

        if args.old_version:
            old_paper = old_root.find(f"*[@id='{paper_id}']")
            if old_paper is None:
                log.error(
                    f"No old version for {paper_id} with title {papernode.find('title').text}"
                )
            else:
                old_video = old_paper.find("video")
                log.info(old_video)
                if old_video is not None:
                    log.info("Had old video!")
                    old_video_href = old_video.attrib["href"]
                    old_video_href_https = old_video_href.replace(
                        "http://", "https://"
                    )  # Fix for techtalkx.tv links
                    old_video.attrib["href"] = old_video_href_https
                    log.info(old_video_href)
                    papernode.append(old_video)

                old_attachment = old_paper.find("attachment")
                log.info(old_attachment)
                if old_attachment is not None:
                    log.info("Had an old attachment!")
                    old_attachment_type = old_attachment.attrib["type"]
                    log.info(old_attachment_type)
                    papernode.append(old_attachment)

        volume.append(papernode)
        i += 1

    for paper in volume:
        for field in paper:
            field.tail = "\n    "
        if len(paper):
            paper.text = "\n    "
            paper[-1].tail = "\n  "
        paper.tail = "\n\n  "
    if len(volume):
        volume.text = "\n  "
        volume[-1].tail = "\n"
    volume.tail = "\n"

    et = etree.ElementTree(volume)
    et.write(args.outfile, encoding="UTF-8", xml_declaration=True)
