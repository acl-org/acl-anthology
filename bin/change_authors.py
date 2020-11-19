#!/usr/bin/env python3

"""Apply changes to author names.

usage: change_authors.py -o <out-dir> <change-file>

Reads a list of changes (produced, e.g., by author_case.py)
in the following format:

paperid \t role \t oldfirst || oldlast \t newfirst || newlast

For example:

Z99-9999 \t author \t ARAVIND K. || JOSHI \t Aravind K. || Joshi

means, for paper Z99-999, change author name "ARAVIND K. JOSHI" to
"Aravind K. Joshi".

The script will apply these changes to all of the .xml files given on
the command line and write modified copies in <out-dir>/data/xml.

It will also try to modify data/yaml/name_variants.yaml and write it
to <out-dir>/data/yaml/name_variants.yaml. However, sometimes this is
not possible, so it will ask you to manually merge two entries.
"""

import sys
import os.path
import glob
import anthology
import yaml, yamlfix
import lxml.etree as etree
import collections
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
        logging.error(
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

    logging.basicConfig(level=logging.INFO)

    ap = argparse.ArgumentParser(description="Apply changes to author names.")
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

    oldnames = collections.defaultdict(list)

    for infile in infiles:
        tree = etree.parse(infile)
        root = tree.getroot()
        if not root.tail:
            root.tail = "\n"
        for volume in root.findall("volume"):
            for paper in volume.findall("paper"):
                paperid = anthology.utils.build_anthology_id(
                    root.attrib["id"], volume.attrib["id"], paper.attrib["id"]
                )
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

                    oldnames[anthology.people.PersonName(oldfirst, oldlast)].append(
                        paperid
                    )

        outfile = os.path.join(args.outdir, "data", "xml", os.path.basename(infile))
        tree.write(outfile, xml_declaration=True, encoding="UTF-8")

    # If a name variant is no longer used, delete it
    deleted_names = set()
    for name, papers in oldnames.items():
        if set(papers) == set(anth.pindex.name_to_papers[name][False]):
            deleted_names.add(name)

    newvariants = []
    for d in variants:
        name = anthology.people.PersonName.from_dict(d["canonical"])
        if name in deleted_names:
            logging.error(
                "canonical name '{}' is no longer used; please delete manually".format(
                    name
                )
            )
        for var in list(d.get("variants", [])):
            name = anthology.people.PersonName.from_dict(var)
            if name in deleted_names:
                logging.info("variant name '{}' is no longer used; deleting".format(name))
                d["variants"].remove(var)
        if "variants" in d and len(d["variants"]) == 0:
            del d["variants"]
        if list(d.keys()) == ["canonical"]:
            continue
        newvariants.append(d)
    variants = newvariants

    variants.sort(key=lambda v: (v["canonical"]["last"], v["canonical"]["first"]))

    with open(
        os.path.join(args.outdir, "data", "yaml", "name_variants.yaml"), "w"
    ) as outfile:
        outfile.write(yaml.dump(variants, allow_unicode=True, default_flow_style=None))
