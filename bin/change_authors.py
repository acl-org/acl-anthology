"""Apply changes to author names.

The input file should have the format:

paperid \t role \t oldfirst || oldlast \t newfirst || newlast

For example:

Z99-9999 \t author \t ARAVIND K. || JOSHI \t Aravind K. Joshi

This script will try to modify data/yaml/name_variants.yaml as well. However, sometimes it will ask you to manually merge two entries.

To do:
- Remove entry from name_variants.yaml if it becomes unused
"""

import sys
import os.path
import glob
import anthology
import yaml, yamlfix
import lxml.etree as etree
import argparse
import logging

def merge_people(variants, can1, can2):
    if can1 == can2:
        return
    # This is really inefficient, but it doesn't actually happen that much
    i1 = i2 = None
    for i, d in enumerate(variants):
        can = anthology.people.PersonName.from_dict(d["canonical"])
        if can == can1:
            i1 = i
        if can == can2:
            i2 = i
    if i1 is not None and i2 is not None:
        logger.error(
            "Please manually merge '{}' and '{}' in name_variants.yaml".format(can1, can2)
        )
        return
    elif i1 is not None:
        i = i1
        new = can2
    elif i2 is not None:
        i = i2
        new = can1
    else:
        # choose can2 to be canonical, since it is the new and hopefully more correct name.
        variants.append({"canonical": {"first": can2.first, "last": can2.last}})
        i = len(variants) - 1
        new = can1
    for v in variants[i].get("variants", []):
        var = anthology.people.PersonName.from_dict(v)
        if var == new:
            return
    variants[i].setdefault("variants", []).append(
        {"first": new.first, "last": new.last}
    )  # don't use to_dict because that adds extra fields

if __name__ == "__main__":
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    datadir = os.path.join(scriptdir, "..", "data")

    logger = logging.getLogger("change_authors")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    ap = argparse.ArgumentParser(
        description="Apply changes to author names."
    )
    ap.add_argument("changefile", help="list of changes")
    ap.add_argument(
        "-o", "--outdir", metavar="dir", help="output directory", required=True
    )
    args = ap.parse_args()
    
    changes = {}
    for line in open(args.changefile):
        paperid, role, oldname, newname = line.rstrip().split('\t')
        oldfirst, oldlast = oldname.split(' || ')
        newfirst, newlast = newname.split(' || ')
        changes[paperid, oldfirst, oldlast] = newfirst, newlast
    
    anth = anthology.Anthology(importdir=datadir)
    variants = yaml.safe_load(open(os.path.join(datadir, "yaml", "name_variants.yaml")))
    infiles = sorted(glob.glob(os.path.join(datadir, "xml", "*.xml")))

    os.makedirs(os.path.join(args.outdir, "data", "xml"), exist_ok=True)
    os.makedirs(os.path.join(args.outdir, "data", "yaml"), exist_ok=True)
    
    for infile in infiles:
        tree = etree.parse(infile)
        root = tree.getroot()
        if not root.tail:
            root.tail = "\n"
        for volume in root.findall("volume"):
            for paper in volume.findall("paper"):
                paperid = anthology.utils.build_anthology_id(root.attrib["id"],
                                                             volume.attrib["id"],
                                                             paper.attrib["id"])
                for authornode in paper.xpath("./author|./editor"):
                    firstnode = authornode.find("first")
                    lastnode = authornode.find("last")
                    if firstnode is None or firstnode.text is None:
                        oldfirst = ""
                    else:
                        oldfirst = firstnode.text
                    oldlast = lastnode.text or ""
                    try:
                        newfirst, newlast = changes[paperid, oldfirst, oldlast]
                    except KeyError:
                        continue

                    # Update variants
                    oldperson = anth.people.resolve_name(
                        anthology.people.PersonName(oldfirst, oldlast)
                    )["id"]
                    newperson = anth.people.resolve_name(
                        anthology.people.PersonName(newfirst, newlast)
                    )["id"]
                    merge_people(
                        variants,
                        anth.people.get_canonical_name(oldperson),
                        anth.people.get_canonical_name(newperson),
                    )

                    # Update XML file
                    if newfirst != "":
                        if firstnode is None:
                            firstnode = etree.SubElement(authornode, 'first')
                        firstnode.text = newfirst
                    else:
                        if firstnode is not None:
                            authornode.remove(firstnode)
                    lastnode.text = newlast
                    
        outfile = os.path.join(args.outdir, "data", "xml", os.path.basename(infile))
        tree.write(outfile, xml_declaration=True, encoding="UTF-8")
        
    variants.sort(key=lambda v: (v["canonical"]["last"], v["canonical"]["first"]))

    with open(
        os.path.join(args.outdir, "data", "yaml", "name_variants.yaml"), "w"
    ) as outfile:
        outfile.write(yaml.dump(variants, allow_unicode=True, default_flow_style=None))
