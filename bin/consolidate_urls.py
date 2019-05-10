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

from repair_url import test_url, get_anth_url

filename = sys.argv[1]
outfilename = sys.argv[2]
tree = etree.parse(filename)
volume = tree.getroot()
volume_id = volume.attrib['id']

# Build list of volumes observed
volumes = set()

for paper in volume.findall("paper"):
    href = None

    if volume_id.startswith('W'):
        volumes.add(paper.attrib['id'][0:2])
    else:
        volumes.add(paper.attrib['id'][0:1])

    paper_id = int(paper.attrib['id'])
    acl_id = '{}-{}'.format(volume_id, paper_id)
    if 'href' in paper.attrib:
        href = paper.attrib['href']
        print('{}: removing href attribute {}'.format(acl_id, href), file=sys.stderr)
        del paper.attrib['href']

    if href and paper.find('href'):
        print('{}: WARNING: found "href" attribute AND <href> tag'.format(paper_id), file=sys.stderr)
        sys.exit(1)

    if paper.find('href'):
        assert len(href) == 0
        if not test_url(href.text):
            href = paper.find('href').text
            print('{}: removing href element: {}'.format(acl_id, text), file=sys.stderr)
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
            print("{}: rewriting url: {} -> {}".format(acl_id, url.text, anth_url), file=sys.stderr)
            url.text = anth_url
    else:
        # For this initial conversion, we add the canonical URL
        url = etree.Element('url')
        url.text = anth_url
        print("{}: inserting url element: {}".format(acl_id, anth_url), file=sys.stderr)
        paper.append(url)

# Now look for volumes -- (postponed until after hierarchical change)
# for id_ in sorted(volumes):
#     url = etree.Element('url')
#     url.text = get_anth_url(volume_id, int(id_), width=len(id_))
#     if test_url(url.text):
#         print("{}: inserting volume URL: {}".format(volume_id, url.text), file=sys.stderr)
#         url.tail = '\n  '
#         volume.insert(0, url)

# https://stackoverflow.com/a/33956544
# def indent(elem, level=0):
#     i = "\n" + level*"  "
#     if len(elem):
#         if not elem.text or not elem.text.strip():
#             elem.text = i + "  "
#         if not elem.tail or not elem.tail.strip():
#             elem.tail = i
#         for elem in elem:
#             indent(elem, level+1)
#         if not elem.tail or not elem.tail.strip():
#             elem.tail = i
#     else:
#         if level and (not elem.tail or not elem.tail.strip()):
#             elem.tail = i

# indent(volume)

tree.write(outfilename, encoding='UTF-8', xml_declaration=True, with_tail=True)
