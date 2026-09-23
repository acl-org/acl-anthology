#!/usr/bin/env python3

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from acl_anthology import Anthology
from acl_anthology.collections import VolumeType
from acl_anthology.files import PDFReference


ARCHIVE_INDEX_URL = (
    "https://web.archive.org/web/20211201201347/"
    "https://www.aclweb.org/old_anthology/docs/fs.html"
)
ARCHIVE_PDF_URLS = (
    "https://aclanthology.org/{source_id}.pdf",
    (
        "https://web.archive.org/web/20211201201347id_/"
        "https://www.aclweb.org/old_anthology/J/J79/{source_id}.pdf"
    ),
)


@dataclass(frozen=True)
class Issue:
    id: str
    month: str
    journal_volume: str | None = None
    journal_issue: str | None = None
    source_id: str | None = None
    source_papers: tuple[str, ...] = ()
    sic: bool = False

    def title(self, year: int) -> str:
        if self.journal_volume is None:
            return f"The Finite String Newsletter, {self.month} {year}"
        volume = self.journal_volume + (" [sic]" if self.sic else "")
        label = "Numbers" if "-" in str(self.journal_issue) else "Number"
        return (
            f"The Finite String, Volume {volume}, {label} {self.journal_issue} "
            f"({self.month} {year})"
        )


def issue(
    id_: str,
    month: str,
    journal_volume: int,
    journal_issue: str | int,
    source_id: str | None = None,
    *,
    sic: bool = False,
) -> Issue:
    return Issue(
        id=id_,
        month=month,
        journal_volume=str(journal_volume),
        journal_issue=str(journal_issue),
        source_id=source_id,
        sic=sic,
    )


def embedded(id_: str, month: str, *source_papers: str) -> Issue:
    return Issue(id=id_, month=month, source_papers=tuple(source_papers))


ISSUES: dict[int, tuple[Issue, ...]] = {
    1964: (
        issue("1", "January", 1, 1),
        issue("2", "February", 1, 2),
        issue("3", "March", 1, 3),
        issue("4", "April", 1, 4),
        issue("5", "May", 1, 5),
        issue("6a", "June", 1, "6, Part 1"),
        issue("6b", "July", 1, "6, Part 2"),
        issue("7", "September", 1, 7),
        issue("8", "October", 1, 8),
        issue("9", "November", 1, 9),
        issue("10", "December", 1, 10),
    ),
    1965: tuple(
        issue(str(number), month, 2, number)
        for number, month in enumerate(
            (
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "September",
                "October",
                "November",
                "December",
            ),
            1,
        )
    ),
    1966: (
        issue("1", "January", 3, 1),
        issue("2", "February", 3, 2),
        issue("3", "March", 3, 3),
        issue("4", "April", 3, 4),
        issue("5", "May", 3, 5),
        issue("6", "June", 3, 6),
        issue("7", "September", 3, 7),
        issue("8to9", "October-November", 3, "8-9"),
        issue("10", "December", 3, 10),
    ),
    1967: tuple(
        issue(str(number), month, 4, number)
        for number, month in enumerate(
            (
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "September",
                "October",
                "November",
                "December",
            ),
            1,
        )
    ),
    1968: (
        issue("1", "January", 5, 1),
        issue("2", "February", 5, 2),
        issue("3", "March", 5, 3),
        issue("4", "April", 5, 4),
        issue("5", "May", 5, 5),
        issue("6", "June", 5, 6),
        issue("7", "September", 5, 7),
        issue("8", "October", 5, 8),
        issue("9to10", "November-December", 5, "9-10"),
    ),
    1969: (
        issue("1", "January", 6, 1),
        issue("2", "February", 6, 2),
        issue("3", "March", 6, 3),
        issue("4", "April", 6, 4),
        issue("5", "May", 6, 5),
        issue("6", "June", 6, 6),
        issue("7", "September", 6, 7),
        issue("8to9", "October-November", 6, "8-9"),
        issue("10", "December", 6, 10),
    ),
    1970: tuple(
        issue(str(number), month, 7, number)
        for number, month in enumerate(
            (
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "September",
                "October",
                "November",
                "December",
            ),
            1,
        )
    ),
    1971: (
        issue("1", "January", 8, 1),
        issue("2", "February", 8, 2),
        issue("3", "March", 8, 3),
        issue("4", "April", 8, 4),
        issue("5", "May", 8, 5),
        issue("6", "June", 8, 6),
        issue("7", "September", 8, 7),
        issue("8to9", "October-November", 8, "8-9"),
        issue("10", "December", 8, 10),
    ),
    1972: (
        issue("1to2", "January-February", 9, "1-2"),
        issue("3to4", "March-April", 9, "3-4"),
        issue("5to6", "May-June", 9, "5-6"),
        issue("7to8", "September-October", 9, "7-8"),
        issue("9to10", "November-December", 9, "9-10"),
    ),
    1973: (issue("7to8", "September-October", 10, "7-8"),),
    1974: (
        issue("1", "September", 11, 1, "J79-1001"),
        issue("2", "December", 11, 2, "J79-1006"),
        issue("3", "December", 11, 3, "J79-1009"),
        issue("4", "December", 11, 4, "J79-1014"),
    ),
    1975: (
        issue("1", "April", 12, 1, "J79-1015"),
        issue("2", "July", 12, 2, "J79-1017"),
        issue("3", "July", 12, 3, "J79-1021"),
        issue("4", "September", 12, 4, "J79-1022"),
        issue("5", "November", 12, 5, "J79-1029"),
        issue("6", "November", 12, 6, "J79-1030"),
    ),
    1976: (
        issue("1", "February", 13, 1, "J79-1037"),
        issue("2", "February", 13, 2, "J79-1042"),
        issue("3", "May", 13, 3, "J79-1043"),
        issue("4", "May", 13, 4, "J79-1049"),
        issue("5", "May", 13, 5, "J79-1050"),
        issue("6", "September", 13, 6, "J79-1051"),
        issue("7", "December", 13, 7, "J79-1055"),
        issue("8", "December", 13, 8, "J79-1058"),
    ),
    1977: (
        issue("1", "February", 14, 1, "J79-1059"),
        issue("2", "May", 14, 2, "J79-1064"),
        issue("3", "May", 14, 3, "J79-1065"),
        issue("4", "September", 14, 4, "J79-1066"),
        issue("5", "September", 14, 5, "J79-1068"),
        issue("6", "December", 14, 6, "J79-1069"),
        issue("7", "December", 14, 7, "J79-1072"),
    ),
    1978: (
        issue("1", "February", 15, 1, "J79-1073"),
        issue("2", "June", 15, 2, "J79-1075"),
        issue("3", "June", 15, 3, "J79-1076"),
        issue("4", "December", 15, 4, "J79-1077"),
    ),
    1979: (issue("5", "March", 15, 5, "J79-1081"),),
    1980: (
        embedded("1", "January-March", *[f"J80-{n}" for n in range(1007, 1011)]),
        embedded("2", "April-June", *[f"J80-{n}" for n in range(2007, 2012)]),
        embedded("3", "July-December", *[f"J80-{n}" for n in range(3007, 3012)]),
    ),
    1981: (
        embedded("1", "January-March", *[f"J81-{n}" for n in range(1006, 1009)]),
        embedded("2", "April-June", "J81-2006"),
        embedded("3", "July-September", *[f"J81-{n}" for n in range(3006, 3011)]),
        embedded("4", "October-December", *[f"J81-{n}" for n in range(4007, 4013)]),
    ),
    1982: (
        embedded("1", "January-March", *[f"J82-{n}" for n in range(1005, 1008)]),
        embedded("2", "April-June", *[f"J82-{n}" for n in range(2007, 2013)]),
        embedded("3", "July-December", *[f"J82-{n}" for n in range(3005, 3010)]),
    ),
    1983: (
        embedded("1", "January-March", *[f"J83-{n}" for n in range(1006, 1011)]),
        embedded("2", "April-June", *[f"J83-{n}" for n in range(2006, 2009)]),
        embedded("3", "July-December", *[f"J83-{n}" for n in range(3007, 3010)]),
    ),
    1984: (
        embedded("1", "January-March", *[f"J84-{n}" for n in range(1004, 1012)]),
        embedded("2", "April-June", *[f"J84-{n}" for n in range(2006, 2011)]),
        embedded("3", "July-December", *[f"J84-{n}" for n in range(3007, 3012)]),
    ),
    1985: (
        embedded("1", "January-March", *[f"J85-{n}" for n in range(1005, 1008)]),
        embedded("2", "April-September", *[f"J85-{n}" for n in range(2010, 2014)]),
        embedded("4", "October-December", *[f"J85-{n}" for n in range(4007, 4010)]),
    ),
    1986: (
        embedded("1", "January-March", *[f"J86-{n}" for n in range(1007, 1012)]),
        embedded("2", "April-June", *[f"J86-{n}" for n in range(2008, 2013)]),
        embedded("3", "July-September", *[f"J86-{n}" for n in range(3006, 3010)]),
        embedded("4", "October-December", *[f"J86-{n}" for n in range(4009, 4013)]),
    ),
    1987: (
        embedded("1", "January-June", *[f"J87-{n}" for n in range(1016, 1024)]),
        embedded("3", "July-December", *[f"J87-{n}" for n in range(3011, 3015)]),
    ),
    1988: (issue("4", "December", 14, 4, sic=True),),
    1991: (
        issue("1", "May", 17, 1),
        issue("2", "June", 17, 2),
        issue("3", "September", 17, 3),
    ),
    1992: (
        issue("1", "March", 18, 1),
        issue("2", "June", 18, 2),
    ),
}


def validate_pdf(path: Path) -> int:
    if not path.read_bytes().startswith(b"%PDF-"):
        raise ValueError(f"Not a PDF: {path}")
    page_count = len(PdfReader(path).pages)
    if page_count == 0:
        raise ValueError(f"PDF has no pages: {path}")
    return page_count


def download_archive_pdf(source_id: str, cache_dir: Path) -> Path:
    destination = cache_dir / f"{source_id}.pdf"
    if destination.is_file():
        validate_pdf(destination)
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={"GET"},
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    errors = []
    for url_template in ARCHIVE_PDF_URLS:
        try:
            response = session.get(url_template.format(source_id=source_id), timeout=120)
            response.raise_for_status()
            destination.write_bytes(response.content)
            break
        except requests.RequestException as exc:
            errors.append(exc)
    else:
        raise ExceptionGroup(f"Could not download {source_id}", errors)
    validate_pdf(destination)
    return destination


def download_paper_pdf(anthology: Anthology, paper_id: str, cache_dir: Path) -> Path:
    destination = cache_dir / f"{paper_id}.pdf"
    paper = anthology.get_paper(paper_id)
    if paper is None or paper.pdf is None:
        raise ValueError(f"No PDF metadata for source paper {paper_id}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    paper.pdf.download(destination, timeout=120)
    validate_pdf(destination)
    return destination


def stage_pdf(
    anthology: Anthology,
    year: int,
    issue_: Issue,
    files_root: Path,
    cache_dir: Path,
    force: bool,
) -> PDFReference | None:
    if issue_.source_id is None and not issue_.source_papers:
        return None

    full_id = f"{year}.finitestring-{issue_.id}"
    destination = files_root / "pdf" / "finitestring" / f"{full_id}.pdf"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {destination}")

    if issue_.source_id is not None:
        source = download_archive_pdf(issue_.source_id, cache_dir / "archive")
        shutil.copyfile(source, destination)
    else:
        writer = PdfWriter()
        for paper_id in issue_.source_papers:
            source = download_paper_pdf(anthology, paper_id, cache_dir / "papers")
            writer.append(source)
        with destination.open("wb") as pdf_file:
            writer.write(pdf_file)
        writer.close()

    pages = validate_pdf(destination)
    print(f"Staged {destination} ({pages} pages)")
    return PDFReference.from_file(destination)


def create_collection(
    year: int,
    xml_dir: Path,
    files_root: Path,
    cache_dir: Path,
    force: bool,
) -> Path:
    collection_id = f"{year}.finitestring"
    destination = xml_dir / f"{collection_id}.xml"
    if destination.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {destination}")

    anthology = Anthology.from_within_repo()
    if anthology.get_collection(collection_id) is not None:
        if not force:
            raise ValueError(f"Collection already exists: {collection_id}")
        del anthology.collections[collection_id]
    collection = anthology.create_collection(collection_id)

    for issue_ in ISSUES[year]:
        pdf = stage_pdf(anthology, year, issue_, files_root, cache_dir, force=force)
        collection.create_volume(
            id=issue_.id,
            title=issue_.title(year),
            type=VolumeType.JOURNAL,
            publisher="Association for Computational Linguistics",
            month=issue_.month,
            venue_ids=["finitestring"],
            journal_title="The Finite String",
            journal_volume=issue_.journal_volume,
            journal_issue=issue_.journal_issue,
            pdf=pdf,
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    collection.save(path=destination, minimal_diff=False)
    collection.path = destination
    collection.validate_schema()
    print(f"Created {destination} ({len(collection)} volumes)")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one yearly Finite String collection and stage its PDFs."
    )
    parser.add_argument("year", type=int, choices=sorted(ISSUES))
    parser.add_argument(
        "--xml-dir",
        type=Path,
        default=Path("data/xml"),
        help="XML destination directory (default: %(default)s)",
    )
    parser.add_argument(
        "--files-root",
        type=Path,
        default=Path.home() / "anthology-files",
        help="Anthology files root (default: %(default)s)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "acl-anthology" / "finite-string",
        help="Source PDF cache (default: %(default)s)",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    create_collection(
        args.year,
        xml_dir=args.xml_dir,
        files_root=args.files_root,
        cache_dir=args.cache_dir,
        force=args.force,
    )


if __name__ == "__main__":
    main()
