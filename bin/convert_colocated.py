#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#
# Copyright 2022 Matt Post <post@cs.jhu.edu>
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
Converts

    <event>
      <colocated>VOLUME_ID</colocated>
      ...
    </event>

to

    <event>
      <colocated>
        <volume-id>VOLUME_ID</volume-id>
      </colocated>
    </
"""

from pathlib import Path
import sys

import lxml.etree as ET


sys.path.append("/Users/mattpost/src/acl-anthology/bin")
from anthology.utils import make_simple_element, indent  # noqa: E402

for xml_file in sys.argv[1:]:
    xml_file = Path(xml_file)

    collection_id = xml_file.name[0:3]

    # the volume we'll iterate over
    tree = ET.parse(xml_file)

    event_xml = tree.getroot().find("./event")
    if event_xml is not None:
        event_id = event_xml.attrib["id"]

        colocated_xml = make_simple_element("colocated")
        for volume_xml in event_xml.findall("./colocated"):
            make_simple_element("volume-id", volume_xml.text, parent=colocated_xml)
            event_xml.remove(volume_xml)
        event_xml.append(colocated_xml)

    indent(tree.getroot())
    tree.write(xml_file, encoding="UTF-8", xml_declaration=True)

    print("Writing", xml_file)
