#!/usr/bin/env python3
# Marcel Bollmann <marcel@bollmann.me>, 2019

"""Usage: split_sitemap.py SITEMAP

Split up a sitemap.xml file into multiple files containing at most 50,000 entries each.  (This is Google's upper limit for re-indexing sites via sitemaps.)

Outputs files named SITEMAP.1, SITEMAP.2, etc.

Arguments:
  SITEMAP                  A sitemap file in XML format.
  -h, --help               Display this helpful text.
"""

from copy import deepcopy
from docopt import docopt
from lxml import etree
import os
import sys


if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        sitemap = etree.parse(args["SITEMAP"])
    except Exception as e:
        print("Error parsing sitemap:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        exit(1)

    root = sitemap.getroot()
    chunk_size = 50000
    i = chunk_size
    all_roots, new_root = [], False

    for url in root:
        if i >= chunk_size:
            if new_root:
                all_roots.append(new_root)
            new_root = etree.Element(root.tag, **dict(root.attrib))
            i = 0
        new_root.append( deepcopy(url) )
        i += 1

    if new_root:
        all_roots.append(new_root)

    print("Split {} entries into {} chunks.".format(chunk_size * (len(all_roots) - 1) + i, len(all_roots)), file=sys.stderr)

    basename = os.path.splitext(args["SITEMAP"])[0]
    for n, root in enumerate(all_roots):
        with open("{}_{}.xml".format(basename, n+1), "w") as f:
            print(etree.tostring(root, xml_declaration=True, pretty_print=True), file=f)
