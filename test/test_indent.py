#!/usr/bin/env python3

import sys
import lxml.etree as etree

from anthology.utils import indent

filename = "data/test.xml"
tree = etree.parse(filename)
root = tree.getroot()
indent(root)
print(etree.tostring(root).decode("utf-8"))
