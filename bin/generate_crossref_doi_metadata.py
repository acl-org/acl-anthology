#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Min-Yen Kan <kanmy@comp.nus.edu.sg>
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

"""Creates the Crossref metadata submission XML for the current (30
Jun 2019) Anthology XML data.  Needs to be uploaded to Crossref via
the ACL organization credentials.  Note that each DOI assigned costs
the ACL $1 USD.

- Only assign DOIs to ACL venues (i.e., those run by ACL or
  (co-)sponsored by an ACL chapter or SIG)
- Do not assign DOIs to journals that assign their own DOIs (as of
  current, both CL and TACL should be assigning their own DOIs)

See also https://github.com/acl-org/acl-anthology/wiki/DOI

Usage: python3 generate_crossref_doi_metadata.py <list of volume IDs>
e.g.,

    python3 generate_crossref_doi_metadata.py P19-1 P19-2 P19-3 P19-4 > acl2019_dois.xml

Limitations:
- This script does not inject the DOI data into the Anthology XML.
  For this, use `bin/add_dois.py <list of volume IDs>`.
- Doesn't properly handle existing ISBN information.
- Doesn't currently submit the frontmatter.

Tested:
- against 2018 workshop and conference data (working)
"""
import os
import re
import sys
import time

from lxml import etree

from anthology.utils import deconstruct_anthology_id, make_simple_element, is_newstyle_id
from anthology.data import ANTHOLOGY_URL, DOI_PREFIX
from anthology.formatter import MarkupFormatter

# CONSTANTS
PUBLISHER_PLACE = "Stroudsburg, PA, USA"
DEPOSITOR_NAME = "Matt Post"
EMAIL_ADDRESS = "anthology@aclweb.org"
REGISTRANT = "Association for Computational Linguistics"
PUBLISHER = "Association for Computational Linguistics"
MONTH_HASH = {
    "January": "1",
    "February": "2",
    "March": "3",
    "April": "4",
    "May": "5",
    "June": "6",
    "July": "7",
    "August": "8",
    "September": "9",
    "October": "10",
    "November": "11",
    "December": "12",
}

# FUNCTION DEFINITIONS
def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = etree.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def main(volumes):

    formatter = MarkupFormatter()

    ## Assemble container
    doi_batch = make_simple_element(
        "doi_batch",
        attrib={
            "xmlns": "http://www.crossref.org/schema/4.4.1",
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": "http://www.crossref.org/schema/4.4.1 http://www.crossref.org/schema/deposit/crossref4.4.1.xsd",
            "version": "4.4.1",
        },
        namespaces={"xsi": "http://www.w3.org/2001/XMLSchema-instance"},
    )
    new_volume = etree.ElementTree(doi_batch)

    ## Assemble head
    head = make_simple_element("head", parent=new_volume.getroot())
    dbi = make_simple_element("doi_batch_id", text=str(int(time.time())), parent=head)

    timestamp = make_simple_element("timestamp", text=str(int(time.time())), parent=head)

    depositor = make_simple_element("depositor", parent=head)
    depositor_name = make_simple_element(
        "depositor_name", text=DEPOSITOR_NAME, parent=depositor
    )
    email_address = make_simple_element(
        "email_address", text=EMAIL_ADDRESS, parent=depositor
    )

    registrant = make_simple_element("registrant", text=REGISTRANT, parent=head)

    ## Assemble body
    body = make_simple_element("body", parent=new_volume.getroot())

    year = ""
    start_month = ""
    end_month = ""

    for full_volume_id in sorted(volumes):
        collection_id, volume_id, _ = deconstruct_anthology_id(full_volume_id)

        collection_file = os.path.join(
            os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{collection_id}.xml"
        )
        tree = etree.parse(collection_file)

        v = tree.getroot().find(f"./volume[@id='{volume_id}']")
        if v is None:
            print(f"* Can't find volume {full_volume_id}", file=sys.stderr)
            continue

        ## Assemble frontmatter
        c = make_simple_element("conference", parent=body)
        contribs = make_simple_element("contributors", parent=c)
        editor_index = 0

        meta = v.find("./meta")
        for tag in meta:
            if tag.tag == "year":
                year = tag.text
            elif tag.tag == "month":
                month = tag.text
                try:
                    start_month = MONTH_HASH[re.split("[-–]", month)[0]]
                    end_month = MONTH_HASH[re.split("[-–]", month)[1]]
                except IndexError as e:  # only one month
                    start_month = MONTH_HASH[month]
                    end_month = MONTH_HASH[month]
                except Exception as e:
                    print(
                        f"FATAL: can't parse month {month} in {full_volume_id}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            elif tag.tag == "booktitle":
                booktitle = formatter.as_text(tag)
            elif tag.tag == "address":
                address = tag.text
            elif tag.tag == "publisher":
                publisher = tag.text
            elif tag.tag == "editor":
                pn = make_simple_element(
                    "person_name",
                    parent=contribs,
                    attrib={
                        "contributor_role": "chair",
                        "sequence": "first" if editor_index == 0 else "additional",
                    },
                )
                editor_index += 1

                for name_part in tag:
                    # Check if empty (e.g., "Mausam")
                    if (
                        name_part.tag == "first"
                        and name_part.text is not None
                        and name_part.text != ""
                    ):
                        gn = make_simple_element(
                            "given_name", parent=pn, text=name_part.text
                        )
                    elif name_part.tag == "last":
                        sn = make_simple_element(
                            "surname", text=name_part.text, parent=pn
                        )

        # Assemble Event Metadata
        em = make_simple_element("event_metadata", parent=c)
        cn = make_simple_element("conference_name", parent=em, text=booktitle)
        cl = make_simple_element("conference_location", parent=em, text=address)
        cd = make_simple_element(
            "conference_date",
            parent=em,
            attrib={
                "start_year": year,
                "end_year": year,
                "start_month": start_month,
                "end_month": end_month,
            },
        )

        # Assemble Proceedings Metadata
        pm = make_simple_element(
            "proceedings_metadata", parent=c, attrib={"language": "en"}
        )
        pt = make_simple_element("proceedings_title", parent=pm, text=booktitle)
        p = make_simple_element("publisher", parent=pm)
        pn = make_simple_element("publisher_name", parent=p, text=publisher)
        pp = make_simple_element("publisher_place", parent=p, text=PUBLISHER_PLACE)
        pd = make_simple_element("publication_date", parent=pm)
        y = make_simple_element("year", parent=pd, text=year)
        noisbn = make_simple_element(
            "noisbn", parent=pm, attrib={"reason": "simple_series"}
        )

        # DOI assignation data
        dd = make_simple_element("doi_data", parent=pm)
        doi = make_simple_element("doi", parent=dd, text=DOI_PREFIX + full_volume_id)
        resource = make_simple_element(
            "resource", parent=dd, text=ANTHOLOGY_URL.format(full_volume_id)
        )

        for paper in v.findall("./paper"):
            ## Individual Paper Data
            paper_id = paper.attrib["id"]
            if paper.find("./url") is not None:
                url = paper.find("./url").text
            else:
                if is_newstyle_id(full_volume_id):
                    url = f"{full_volume_id}.{paper_id}"
                elif len(full_volume_id) == 6:
                    url = f"{full_volume_id}{paper_id:02d}"
                elif len(full_volume_id) == 5:
                    url = f"{full_volume_id}{paper_id:03d}"

            cp = make_simple_element("conference_paper", parent=c)

            # contributors
            contribs = make_simple_element("contributors", parent=cp)
            author_index = 0
            for author in paper.findall("./author"):
                pn = make_simple_element(
                    "person_name",
                    parent=contribs,
                    attrib={
                        "contributor_role": "author",
                        "sequence": "first" if author_index == 0 else "additional",
                    },
                )
                author_index += 1

                for name_part in author:
                    if (
                        name_part.tag == "first"
                        and name_part.text is not None
                        and name_part.text != ""
                    ):
                        gn = make_simple_element(
                            "given_name", parent=pn, text=name_part.text
                        )
                    elif name_part.tag == "last":
                        sn = make_simple_element(
                            "surname", text=name_part.text, parent=pn
                        )

            for title in paper.iter(tag="title"):
                o_titles = make_simple_element("titles", parent=cp)
                o_title = make_simple_element(
                    "title", parent=o_titles, text=formatter.as_text(title)
                )

            pd = make_simple_element("publication_date", parent=cp)
            o_year = make_simple_element("year", parent=pd)
            o_year.text = year

            for pages in paper.iter(tag="pages"):
                o_pages = make_simple_element("pages", parent=cp)
                fp = make_simple_element("first_page", parent=o_pages)
                lp = make_simple_element("last_page", parent=o_pages)
                try:
                    fp.text = re.split("[-–]", pages.text)[0]
                    lp.text = re.split("[-–]", pages.text)[1]
                except IndexError as e:  # only one page
                    fp.text = pages.text
                    lp.text = pages.text

            # DOI assignation data
            dd = make_simple_element("doi_data", parent=cp)
            doi = make_simple_element("doi", parent=dd, text=DOI_PREFIX + url)
            resource = make_simple_element(
                "resource", parent=dd, text=ANTHOLOGY_URL.format(url)
            )

    print(
        etree.tostring(
            new_volume,
            pretty_print=True,
            encoding="UTF-8",
            xml_declaration=True,
            with_tail=True,
        ).decode("utf-8")
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("volumes", nargs="+", help="Volumes to add DOIs to")
    args = parser.parse_args()

    main(args.volumes)
