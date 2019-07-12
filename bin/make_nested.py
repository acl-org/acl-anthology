#!/usr/bin/env python3

"""
Converts flat input format to hierarchical volumes,
removes padding from paper numbers, and adds the <url>
tag to <volume> if the PDF can be found.

OLD:

    <volume id="P18">
      <paper id="1001">
      ...
    </volume>

NEW:

    <collection id="P18">
      <volume id="1">
        <meta>
          <booktitle>...</booktitle>
          <year>...</year>
          <month>...</month>
          <publish>...</publisher>
          <address>...</address>
        </meta>
        <paper id="1">
        ...
      </volume>
    </root>

Also removes many keys from papers, since they are more properly
inherited from their volumes:

- booktitle
- editor
- year
- month
- publisher
- address

Usage: convert_to_hierarchical.py <infilename> <outfilename>
"""

import lxml.etree as etree
import re
import sys

from anthology.utils import make_nested

filename = sys.argv[1]
outfilename = sys.argv[2]
tree = etree.parse(filename)

tree._setroot(make_nested(tree.getroot()))

tree.write(outfilename, encoding='UTF-8', xml_declaration=True, with_tail=True)
