#!/usr/bin/env python3

"""
Takes an XML file and returns all volumes within it. It will also
return all colocated volumes. This is a convenient way to generate
a list of all volumes associated with an event.
"""

import lxml.etree as ET


def get_volumes(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    collection_id = root.attrib["id"]

    volumes = []
    for volume in root.findall(".//volume"):
        volume_id_full = collection_id + "-" + volume.attrib["id"]
        volumes.append(volume_id_full)

    # get the <colocated> node under <event>
    event_node = root.find(".//event")
    if event_node is not None:
        colocated = event_node.find("colocated")
        if colocated is not None:
            for volume in colocated.findall("volume-id"):
                volumes.append(volume.text)

    return volumes


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("xml_file", help="XML file to process")
    args = parser.parse_args()

    print(" ".join(get_volumes(args.xml_file)))
