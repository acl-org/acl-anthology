"""
Try to automatically restore accents in author names by downloading and scraping the PDFs.
Reads and writes Anthology XML files.

To do:
- Update for new hierarchical XML structure
- Instead of making changes, output a list of changes that can be read by change_authors.py.
"""

import tika.parser
import requests
import sys
import lxml.etree as etree
import re
import unicodedata
import os.path, glob
import anthology
import copy
import collections
import time
from normalize_anth import clean_unicode, curly_quotes
import yaml, yamlfix


def guess_url(paper):
    volume = paper.getparent()

    if (
        paper.attrib["id"].endswith("000")
        or volume.attrib["id"].startswith("W")
        and paper.attrib["id"].endswith("00")
    ):
        return None

    if args.pdfdir:
        path = os.path.join(
            args.pdfdir,
            volume.attrib["id"][0],
            volume.attrib["id"],
            "{}-{}.pdf".format(volume.attrib["id"], paper.attrib["id"]),
        )
        print(path)
        if os.path.exists(path):
            return "file:" + path

    url = paper.find("url") is not None and paper.find("url").text
    if not url:
        url = paper.find("href") and paper.find("href").text
    if not url:
        url = paper.attrib.get("href", None)
    if not url:
        url = "http://www.aclweb.org/anthology/{}-{}".format(
            volume.attrib["id"], paper.attrib["id"]
        )

    return url


def slugify(s):
    # Bug: Foobar and Foo Bar have different slugs.
    # We could remove spaces,
    # but there are many PDFs that have extra spaces, and we don't want those.

    # Split on camelCase
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)

    # Split on hyphens
    s = s.replace("-", " ")

    # Remove accents and symbols
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if c.isalpha() or c.isspace())

    s = s.lower()
    s = "-".join(s.split())

    return s


def is_namechar(c):
    # hyphen can occur in names, but not at beginning or end,
    # so we don't include it her
    return (
        c in ".“”‘’«»„"
        or unicodedata.category(c)[0] not in "CNPSZ"
        and not (0x370 <= ord(c) < 0x400)  # Greek letters used as symbols
    )


email_re = r"(\{.*\}|\S+)\@\S+\.\S+"

delay = 0.0


def get_url(url, retries=10):
    global delay
    if url.startswith("http:") or url.startswith("https:"):
        if retries == 0:
            logger.error("max retries exceeded; skipping")
            return {}
        logger.info("getting {}".format(url))
        try:
            time.sleep(delay)
            r = requests.get(url, timeout=10)
            if not r:
                logger.error("could not download PDF")
                return None
            content = r.content
        except KeyboardInterrupt:
            raise
        except requests.exceptions.Timeout:
            delay += 1.0
            logger.warning("connection timed out; increasing delay to {} s".format(delay))
            return get_url(url, retries - 1)
        except Exception as e:
            logger.error(str(e))
            return get_url(url, retries - 1)
    elif url.startswith("file:"):
        file = url[5:]
        logger.info("reading file {}".format(file))
        content = open(file, "rb").read()
    else:
        assert False

    return content


def scrape_authors(content, retries=10):
    try:
        raw = tika.parser.from_buffer(content)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.error(str(e))
        return scrape_authors(content, retries - 1)

    text = raw.get("content", None)
    if text is None:
        return {}
    index = collections.defaultdict(list)
    li = 0
    for line in text.splitlines():
        # some papers have spaces between every letter
        nospace = "".join(line.split())
        if nospace == "Abstract":
            break
        if nospace == "":
            continue

        li += 1
        if li > 50:
            break

        line = clean_unicode(line)
        line = curly_quotes(line)
        line = unicodedata.normalize(
            "NFKC", line
        )  # more aggressive normalization than clean_unicode; for example, in an author name, 𝐦 (mathematical bold small m) is presumably a PDF bug
        logger.info("line:  " + line)

        # delete email addresses, so that they are not mistaken for names
        for m in re.finditer(email_re, line):
            logger.info("deleting email address {}".format(m.group(0)))
        line = re.sub(email_re, "", line)

        line = line.replace(",", ", ")

        words = []
        slugs = []
        for word in line.split():
            word = word.strip()

            # strip leading and trailing symbols
            while len(word) > 0 and not is_namechar(word[0]):
                word = word[1:]
            while len(word) > 0 and not is_namechar(word[-1]):
                word = word[:-1]

            if word == "":
                continue

            words.append(word)
            slugs.append(slugify(word))

        # Index up to 4-grams
        for g in range(1, 5):
            for i in range(len(words) - g + 1):
                index["-".join(slugs[i : i + g])].append(" ".join(words[i : i + g]))

    return index


def change(index, name):
    if name == "":
        return name
    slug = slugify(name)
    if slug in index:
        if len(set(index[slug])) > 1:
            logger.warning("name collision: {}".format(", ".join(index[slug])))
        newname = index[slug][0]
        if not name.isupper() and newname.isupper():
            # this could backfire for initials, like Abc -> ABC
            logger.info("not uppercasing: {} -> {}".format(name, newname))
            return name
        if not name.islower() and newname.islower():
            # an all-lowercase name is likely to be an email address
            logger.info("not lowercasing: {} -> {}".format(name, newname))
            return name
        if newname != name:
            logger.info("changing: {} -> {}".format(name, newname))
        return newname
    else:
        logger.warning("name {} in XML but not in PDF".format(name))
        return name


def merge_people(variants, can1, can2):
    if can1 == can2:
        return
    # This is really inefficient, but it doesn't actually happen that much
    i1 = i2 = None
    for i, d in enumerate(variants):
        can = anthology.people.PersonName.from_dict(d["canonical"])
        if can == can1:
            i1 = i
        if can == can2:
            i2 = i
    if i1 is not None and i2 is not None:
        logger.error(
            "Please manually merge '{}' and '{}' in name_variants.yaml".format(can1, can2)
        )
        return
    elif i1 is not None:
        i = i1
        new = can2
    elif i2 is not None:
        i = i2
        new = can1
    else:
        # choose can2 to be canonical, since it is the new and hopefully more correct name.
        variants.append({"canonical": {"first": can2.first, "last": can2.last}})
        i = len(variants) - 1
        new = can1
    for v in variants[i].get("variants", []):
        var = anthology.people.PersonName.from_dict(v)
        if var == new:
            return
    variants[i].setdefault("variants", []).append(
        {"first": new.first, "last": new.last}
    )  # don't use to_dict because that adds extra fields


if __name__ == "__main__":
    import argparse
    import logging

    # Set up logging
    logger = logging.getLogger("auto_authors")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:%(location)s %(message)s"))
    location = ""

    def filter(r):
        r.location = location
        return True

    handler.addFilter(filter)
    logger.setLevel(logging.INFO)
    # logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False

    scriptdir = os.path.dirname(os.path.abspath(__file__))
    datadir = os.path.join(scriptdir, "..", "data")

    ap = argparse.ArgumentParser(
        description="Try to automatically restore accents in author names."
    )
    ap.add_argument("infiles", metavar="xml", nargs="*", help="input XML files")
    ap.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="process all XML files in input directory",
    )
    ap.add_argument("-p", "--pdfdir", metavar="dir", help="directory with PDFs")
    ap.add_argument(
        "-i", "--indir", metavar="dir", help="input directory", default=datadir
    )
    ap.add_argument(
        "-o", "--outdir", metavar="dir", help="output directory", required=True
    )
    args = ap.parse_args()

    if args.all and args.infiles:
        ap.print_usage(sys.stderr)
        sys.exit("error: the -a and infiles options cannot be used together")
    elif args.all:
        infiles = sorted(glob.glob(os.path.join(datadir, "xml", "*.xml")))
    elif args.infiles:
        infiles = args.infiles
    else:
        ap.print_usage(sys.stderr)
        sys.exit("error: either the -a or infiles option is required")

    anth = anthology.Anthology(importdir=datadir)
    os.makedirs(os.path.join(args.outdir, "data", "xml"), exist_ok=True)
    os.makedirs(os.path.join(args.outdir, "data", "yaml"), exist_ok=True)

    # Although Anthology already read in name_variants.yaml,
    # we read it here so we can modify it
    variants = yaml.safe_load(open(os.path.join(datadir, "yaml", "name_variants.yaml")))

    for infile in infiles:
        tree = etree.parse(infile)
        volume = tree.getroot()
        if not volume.tail:
            volume.tail = "\n"
        for paper in volume.findall("paper"):
            paperid = "{}-{}".format(volume.attrib["id"], paper.attrib["id"])
            location = paperid + ":"

            url = guess_url(paper)
            if url is None:
                continue
            content = get_url(url)
            index = scrape_authors(content)
            if index is None:
                continue

            for authornode in paper.xpath("./author|./editor"):
                firstnode = authornode.find("first")
                lastnode = authornode.find("last")
                if firstnode is None or firstnode.text is None:
                    first = ""
                else:
                    first = firstnode.text
                last = lastnode.text or ""

                location = "{} {} {} {}:".format(paperid, authornode.tag, first, last)

                newfirst = change(index, first)
                newlast = change(index, last)

                person = anth.people.resolve_name(
                    anthology.people.PersonName(first, last)
                )["id"]
                newperson = anth.people.resolve_name(
                    anthology.people.PersonName(newfirst, newlast)
                )["id"]

                merge_people(
                    variants,
                    anth.people.get_canonical_name(person),
                    anth.people.get_canonical_name(newperson),
                )

                if firstnode is not None:
                    firstnode.text = newfirst
                lastnode.text = newlast

        outfile = os.path.join(args.outdir, "data", "xml", os.path.basename(infile))
        tree.write(outfile, xml_declaration=True, encoding="UTF-8")

    variants.sort(key=lambda v: (v["canonical"]["last"], v["canonical"]["first"]))

    with open(
        os.path.join(args.outdir, "data", "yaml", "name_variants.yaml"), "w"
    ) as outfile:
        outfile.write(yaml.dump(variants, allow_unicode=True, default_flow_style=None))
