#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Matt Post <post@cs.jhu.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Author: Matt Post <post@cs.jhu.edu>

Produces two-space indenting for all items except
<author>, <editor>, <title>, and <booktitle> which
remain on one line.

Usage: indent.py <in.xml> <out.xml>
"""

import lxml.etree as etree
import argparse
import re
import sys

from anthology.utils import indent

if __name__ == "__main__":

    infilename = sys.argv[1]
    outfilename = sys.argv[2]

    tree = etree.parse(infilename)
    root = tree.getroot()
    indent(root)

    tree.write(outfilename, encoding="UTF-8", xml_declaration=True, with_tail=True)
