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
ACL USD 1.  

- Only assign DOIs to ACL venues (i.e., those run by ACL or
  (co-)sponsored by an ACL chapter or SIG) 
- Do not assign DOIs to journals that assign their own DOIs (as of
  current, both CL and TACL should be assigning their own DOIs)

See also https://github.com/acl-org/acl-anthology/wiki/DOI

Usage: python3 generate_crossref_doi_metadata.py <Anthology XML file> <volume ID>

Bugs: 
- Should change DEPOSITOR_NAME / EMAIL_ADDRESS soon
- Can't handle current (30 Jun 2019) ACL Anthology XML with
  <fixed-case> tags.  Need to strip those out first.

Limitations:
- This script does not inject the DOI data into the Anthology XML.
  There (will be) another script for this.
- Doesn't properly handle existing ISBN information.

Tested:
- against 2018 workshop and conference data (working)
"""
import xml.etree.ElementTree as ET  
from xml.dom import minidom
import sys
import time
import re

# CONSTANTS
PUBLISHER_PLACE = "Stroudsburg, PA, USA"
DOI_PREFIX = "10.18653/v1/"
DEPOSITOR_NAME = "Min-Yen Kan"
EMAIL_ADDRESS = "kanmy@comp.nus.edu.sg"
REGISTRANT = "Association for Computational Linguistics"
PUBLISHER  = "Association for Computational Linguistics"
RESOURCE_PREFIX = 'http://aclweb.org/anthology/'
MONTH_HASH = {"January":"1","February":"2","March":"3","April":"4","May":"5","June":"6",
              "July":"7","August":"8","September":"9","October":"10","November":"11","December":"12"}

# FUNCTION DEFINITIONS
def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

tree = ET.parse(sys.argv[1])
vol = sys.argv[2]

##################################################
# MAIN FUNCTION

## Assemble container
new_volume = ET.Element('doi_batch',
                        {'xmlns':'http://www.crossref.org/schema/4.4.1',
                         'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance',
                         'xsi:schemaLocation':'http://www.crossref.org/schema/4.4.1 http://www.crossref.org/schema/deposit/crossref4.4.1.xsd',
                         'version':'4.4.1'})

## Assemble head
head = ET.SubElement(new_volume,'head')
dbi = ET.SubElement(head,'doi_batch_id')
dbi.text = str(int(time.time()))

timestamp = ET.SubElement(head,'timestamp')
timestamp.text = str(int(time.time()))

depositor = ET.SubElement(head,'depositor')
depositor_name = ET.SubElement(depositor,'depositor_name')
depositor_name.text = DEPOSITOR_NAME
email_address = ET.SubElement(depositor,'email_address')
email_address.text = EMAIL_ADDRESS

registrant = ET.SubElement(head,'registrant')
registrant.text = REGISTRANT

## Assemble body
body = ET.SubElement(new_volume,'body')

year = ""
start_month = ""
end_month = ""

for v in tree.iterfind("volume[@id='"+vol+"']"):
    # Volume constant data

    ## Assemble frontmatter
    c = ET.SubElement(body,'conference')
    contribs = ET.SubElement(c,'contributors')
    editor_index = 0;

    for meta in v.iter(tag='meta'):
        for y in meta.iter(tag='year'):
            year = y.text
        for m in meta.iter(tag='month'):
            try:
                start_month = MONTH_HASH[re.split('[-–]',m.text)[0]]
                end_month = MONTH_HASH[re.split('[-–]',m.text)[1]]
            except IndexError as e: # only one month
                start_month = MONTH_HASH[m.text]
                end_month = MONTH_HASH[m.text]
        # Capture the URL to construct the deposit ID
        for u in meta.iter(tag='url'): 
            url = u.text
        for bt in meta.iter(tag='booktitle'): 
            booktitle = bt.text
        for addr in meta.iter(tag='address'): 
            address = addr.text
        for pub in meta.iter(tag='publisher'): 
            publisher = pub.text

        for editor in meta.iter(tag='editor'):
            pn = ET.SubElement(contribs,'person_name',
                               {'contributor_role':'chair'})
            if (editor_index == 0):
                pn.attrib['sequence'] = 'first'
                editor_index += 1
            else:
                pn.attrib['sequence'] = 'additional'
                editor_index += 1

            for first in editor.iter(tag='first'):
                if (not (first.text is None)):
                    gn = ET.SubElement(pn,'given_name')
                    gn.text = first.text
            for last in editor.iter(tag='last'):
                sn = ET.SubElement(pn,'surname')
                sn.text = last.text

        # Assemble Event Metadata
        em = ET.SubElement(c,'event_metadata')
        cn = ET.SubElement(em,'conference_name')
        cn.text = booktitle
        cl = ET.SubElement(em,'conference_location')
        cl.text = address
        cd = ET.SubElement(em,'conference_date',
                           {'start_year':year,
                            'end_year':year,
                            'start_month':start_month,
                            'end_month':end_month})
        
        # Assemble Proceedings Metadata
        pm = ET.SubElement(c,'proceedings_metadata',
                           {'language':'en'})
        pt = ET.SubElement(pm,'proceedings_title')
        pt.text = booktitle
        p = ET.SubElement(pm,'publisher')
        pn = ET.SubElement(p,'publisher_name')
        pn.text = publisher
        pp = ET.SubElement(p,'publisher_place')
        pp.text = PUBLISHER_PLACE
        pd = ET.SubElement(pm,'publication_date')
        y = ET.SubElement(pd,'year')
        y.text = year
        noisbn  = ET.SubElement(pm,'noisbn',
                                {'reason':'simple_series'})

        # DOI assignation data
        dd = ET.SubElement(pm,'doi_data')
        doi = ET.SubElement(dd,'doi')
        doi.text = DOI_PREFIX + url 
        resource = ET.SubElement(dd,'resource')
        resource.text = RESOURCE_PREFIX + url

    for paper in v.iter(tag='paper'):
        ## Individual Paper Data

        aa_id = ""
        if (len(url) == 6):
            aa_id = '{:02d}'.format(int(paper.attrib['id']))
        else:
            if (len(url) == 5):
                aa_id = '{:03d}'.format(int(paper.attrib['id']))

        cp = ET.SubElement(c,'conference_paper')

        # contributors
        contribs = ET.SubElement(cp,'contributors')
        author_index = 0;
        for author in paper.iter(tag='author'):
            pn = ET.SubElement(contribs,'person_name',
                               {'contributor_role':'author'})
            if (author_index == 0):
                pn.attrib['sequence'] = 'first'
                author_index += 1
            else:
                pn.attrib['sequence'] = 'additional'
                author_index += 1

            for first in author.iter(tag='first'):
                if (not (first.text is None)):
                    gn = ET.SubElement(pn,'given_name')
                    gn.text = first.text
            for last in author.iter(tag='last'):
                sn = ET.SubElement(pn,'surname')
                sn.text = last.text
                        
        for title in paper.iter(tag='title'):
            o_titles = ET.SubElement(cp,'titles')
            o_title = ET.SubElement(o_titles,'title')
            o_title.text = title.text

        pd = ET.SubElement(cp,'publication_date')
        o_year = ET.SubElement(pd,'year')
        o_year.text = year

        for pages in paper.iter(tag='pages'):
            o_pages = ET.SubElement(cp,'pages')
            fp = ET.SubElement(o_pages,'first_page')
            lp = ET.SubElement(o_pages,'last_page')
            try:
                fp.text = re.split('[-–]',pages.text)[0]
                lp.text = re.split('[-–]',pages.text)[1]
            except IndexError as e: # only one page
                fp.text = pages.text
                lp.text = pages.text

        # DOI assignation data
        dd = ET.SubElement(cp,'doi_data')
        doi = ET.SubElement(dd,'doi')
        doi.text = DOI_PREFIX + url + aa_id
        resource = ET.SubElement(dd,'resource')
        resource.text = RESOURCE_PREFIX + url + aa_id
        
print (prettify(new_volume))
