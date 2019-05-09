#!/usr/bin/env python3

"""
Used to clean up the URL situation:

- 'href' tags on papers are moved to <url> tags
- <href> tags are turned intot <url> tags
- 'https?:(www).aclweb.org/anthology/' is stripped from <url> tags, leaving just the relative ACL ID

Usage: consolidate_urls.py <infilename> <outfilename>

"""

import lxml.etree as etree
import re
import sys

filename = sys.argv[1]
outfilename = sys.argv[2]
tree = etree.parse(filename)
volume = tree.getroot()

volume_id = volume.attrib['id']
for paper in volume.findall("paper"):
    href = None
    paper_id = int(paper.attrib['id'])
    if 'href' in paper.attrib:
        href = paper.attrib['href']
        print('{}: removing href attribute {}'.format(paper_id, href), file=sys.stderr)
        del paper.attrib['href']

    if href and paper.find('href'):
        print('{}: WARNING: found "href" attribute AND <href> tag'.format(paper_id), file=sys.stderr)
        sys.exit(1)

    if paper.find('href'):
        assert len(href) == 0
        if not test_url(href.text):
            href = paper.find('href').text
            print('{}: removing href element: {}'.format(paper_id, text), file=sys.stderr)
            paper.remove(paper.find('href'))

    if href and paper.find('url'):
        print('{}: WARNING: found "href" attribute AND <url> tag'.format(paper_id), file=sys.stderr)
        sys.exit(1)

    if href and href.startswith('http'):
        anth_url = href
    else:
        anth_url = '{}-{:04d}'.format(volume_id, paper_id)

    anth_url = re.sub(r'^https?://(www\.)?aclweb.org./anthology/', '', anth_url)

    url = paper.find("url")
    if url is not None:
        if url.text != anth_url:
            print("{}: rewriting url: {} -> {}".format(paper_id, url.text, anth_url), file=sys.stderr)
            url.text = anth_url
    else:
        url = etree.Element('url')
        url.text = anth_url
        print("{}: inserting url element: {}".format(paper_id, anth_url), file=sys.stderr)
        paper.append(url)


tree.write(outfilename, encoding='UTF-8', xml_declaration=True, with_tail=True)
