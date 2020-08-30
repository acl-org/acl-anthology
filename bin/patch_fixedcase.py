#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 David Wei Chiang <dchiang@nd.edu>
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

import lxml.etree as etree, html
import sys
import os
import logging
import bibtex
import tex_unicode


def replace_node(old, new):
    save_tail = old.tail
    old.clear()
    old.tag = new.tag
    old.attrib.update(new.attrib)
    old.text = new.text
    old.extend(new)
    old.tail = save_tail


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        format="%(levelname)s:%(location)s %(message)s", level=logging.INFO
    )
    location = ""

    def filter(r):
        r.location = location
        return True

    logging.getLogger().addFilter(filter)

    xfilename, bdirname, outfilename = sys.argv[1:]
    xtree = etree.parse(xfilename)
    xroot = xtree.getroot()

    for xpaper in xroot.findall("paper"):
        fullid = "{}-{}".format(xroot.attrib["id"], xpaper.attrib["id"])
        location = fullid
        bfilename = os.path.join(bdirname, fullid + ".bib")
        try:
            bdata = bibtex.read_bibtex(bfilename)
        except FileNotFoundError:
            logging.warning("{} not found".format(bfilename))
            continue
        for entry in bdata.entries.values():
            for field in ["title", "booktitle"]:
                if field not in entry.fields:
                    continue

                boldvalue = entry.fields[field]
                bnewvalue = tex_unicode.parse_latex(boldvalue)
                bibtex.find_fixed_case(bnewvalue, conservative=True)
                bnewvalue = tex_unicode.unparse_latex(bnewvalue, delete_root=True)
                if bnewvalue != boldvalue:
                    xnode = xpaper.find(field)
                    if xnode is None:
                        logging.warning("{} missing from XML".format(field))
                        continue

                    xoldvalue = tex_unicode.contents(xnode)
                    boldvalue = tex_unicode.convert_string(boldvalue)
                    xoldvalue = " ".join(xoldvalue.split())
                    boldvalue = " ".join(boldvalue.split())
                    if xoldvalue != boldvalue:
                        logging.warning(
                            "{} has been changed; please edit manually".format(field)
                        )
                        logging.warning("old value in xml: {}".format(xoldvalue))
                        logging.warning("old value in bib: {}".format(boldvalue))
                        logging.warning("new value in bib: {}".format(bnewvalue))
                    else:  # success
                        bnewvalue = html.escape(bnewvalue)
                        bnewvalue = bnewvalue.replace(
                            r"\begin{fixedcase}", "<fixed-case>"
                        )
                        bnewvalue = bnewvalue.replace(r"\end{fixedcase}", "</fixed-case>")
                        xnewnode = tex_unicode.convert_node(
                            etree.fromstring(
                                "<{}>{}</{}>".format(xnode.tag, bnewvalue, xnode.tag)
                            )
                        )
                        replace_node(xnode, xnewnode)

    xtree.write(outfilename, encoding="UTF-8", xml_declaration=True)
