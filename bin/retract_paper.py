#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 Matt Post <post@cs.jhu.edu>
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
Takes an Anthology ID, downloads the PDF, and produces a revision PDF
with a "RETRACTED" watermark, as well as a note at the top pointing
to the paper page. Also revises the XML.
"""

import argparse
import os
import subprocess
import sys
import tempfile

from string import Template

from anthology.utils import (
    retrieve_url,
    deconstruct_anthology_id,
    make_simple_element,
    get_xml_file,
    indent,
)
from anthology.data import CANONICAL_URL_TEMPLATE, PDF_LOCATION_TEMPLATE
from add_revision import add_revision

from datetime import datetime

import lxml.etree as ET

template = Template(
    r"""\documentclass{article}
\usepackage[text=RETRACTED,scale=3,color=red]{draftwatermark}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{pdfpages}
\usepackage{hyperref}
\hypersetup{plainpages=false,
            pdfpagemode=UseNone,
            colorlinks=true,
            unicode=true
}

% set A4
\setlength{\paperwidth}{21cm}
\setlength{\paperheight}{29.7cm}

\special{papersize=21cm,29.7cm}
\pdfpageheight\paperheight
\pdfpagewidth\paperwidth
\pagestyle{plain}

\begin{document}

\AddToShipoutPicture{%
  \setlength{\unitlength}{1mm}
  % center box at (x, y) millimeters from bottom-left corner
  \put(105,290){\makebox(0,0){This paper was retracted. For more information, see \url{$url}.}}
}

\includepdf[pages=-]{$file}

\end{document}"""
)


def add_watermark(anth_id, workdir="."):
    """
    Downloads an Anthology paper and adds a RETRACTED watermark.
    """
    page = CANONICAL_URL_TEMPLATE.format(anth_id)
    url = PDF_LOCATION_TEMPLATE.format(anth_id)
    orig_pdf = os.path.join(workdir, "tmp.pdf")

    retrieve_url(url, orig_pdf)

    tex_file = os.path.join(workdir, f"{anth_id}.tex")
    print("TEX_FILE", tex_file)
    with open(tex_file, "w") as f:
        print(template.substitute(file=orig_pdf, url=page), file=f)

    command = f"pdflatex {tex_file}"
    try:
        subprocess.call(
            command, shell=True, cwd=workdir, stdout=subprocess.DEVNULL, timeout=30
        )
    except subprocess.TimeoutExpired:
        print(
            "pdflatex didn't finish within 30 seconds. Do you have the CTAN watermark package installed?",
            file=sys.stderr,
        )
        sys.exit(1)

    new_pdf = f"{tex_file}".replace(".tex", ".pdf")

    return new_pdf


def main(args):
    """
    Downloads an Anthology paper and adds a RETRACTED watermark, then updates the XML
    with an appropriate <revision> and <retracted> tag.
    """

    with tempfile.TemporaryDirectory() as tempdir:
        new_pdf = add_watermark(args.anthology_id, workdir=tempdir)

        add_revision(
            args.anthology_id,
            new_pdf,
            explanation="Retracted.",
            change_type="revision",
            dry_run=False,
        )

        xml_file = get_xml_file(args.anthology_id)
        collection_id, volume_id, paper_id = deconstruct_anthology_id(args.anthology_id)
        tree = ET.parse(xml_file)
        if paper_id == "0":
            paper = tree.getroot().find(f"./volume[@id='{volume_id}']/frontmatter")
        else:
            paper = tree.getroot().find(
                f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']"
            )

        if paper is None:
            print(f"Couldn't find paper {args.anthology_id}!", file=sys.stderr)
            sys.exit(2)

        print("Modifying the XML", file=sys.stderr)
        now = datetime.now()
        date = f"{now.year}-{now.month:02d}-{now.day:02d}"
        make_simple_element(
            "retracted", args.explanation, attrib={"date": date}, parent=paper
        )
        indent(tree.getroot())
        tree.write(xml_file, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("anthology_id")
    parser.add_argument("explanation", help="Brief description of the changes.")
    args = parser.parse_args()

    main(args)
