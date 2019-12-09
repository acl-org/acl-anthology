"""Repairs URLs in Anthology XML files.

Usage: repair_url.py <infilename> <outfilename>

To do:
- check URLs of attachments
- incorporate into a more general XML-fixing script

"""

import lxml.etree as etree
import requests
import sys

from anthology.utils import test_url


def get_anth_url(volume_id, paper_id=None, width=4):
    return "https://www.aclweb.org/anthology/{volume_id}-{paper_id:0{width}d}".format(
        volume_id=volume_id, paper_id=paper_id, width=width
    )


if __name__ == "__main__":
    filename = sys.argv[1]
    outfilename = sys.argv[2]
    tree = etree.parse(filename)
    volume = tree.getroot()
    for paper in volume.findall("paper"):
        if "href" in paper.attrib:
            if not test_url(paper.attrib["href"]):
                sys.stderr.write(
                    "{}:{} removing href attribute: {}\n".format(
                        filename, paper.sourceline, paper.attrib["href"]
                    )
                )
                del paper.attrib["href"]

        href = paper.find("href")
        if href is not None:
            assert len(href) == 0
            if not test_url(href.text):
                sys.stderr.write(
                    "{}:{} removing href element: {}\n".format(
                        filename, href.sourceline, href.text
                    )
                )
                paper.remove(href)

        anth_url = get_anth_url(volume.attrib["id"], int(paper.attrib["id"]))
        anth_url_good = test_url(anth_url)

        url = paper.find("url")
        assert url is None or len(url) == 0

        if url is None:
            if anth_url_good:
                url = etree.Element("url")
                url.text = anth_url
                sys.stderr.write(
                    "{}:{} inserting url element: {}\n".format(
                        filename, paper.sourceline, anth_url
                    )
                )
                paper.append(url)

        else:
            if anth_url_good and url.text != anth_url:
                sys.stderr.write(
                    "{}:{} rewriting url: {} -> {}\n".format(
                        filename, url.sourceline, url.text, anth_url
                    )
                )
                url.text = anth_url

            else:
                sys.stderr.write(
                    "{}:{} removing url element because {} is bad\n".format(
                        filename, url.sourceline, anth_url
                    )
                )
                paper.remove(url)

    tree.write(outfilename, encoding="UTF-8", xml_declaration=True, with_tail=True)
