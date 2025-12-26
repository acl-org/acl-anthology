#!/usr/bin/env python3

"""
Load the TSV dumped by dump_orcid_info.py. Then, once again, go
through every paper in the Anthology, and find every <author> tag
with an orcid attribute. Call a function (stub for now) to
determine whether to retain the orcid or delete it.
Then save the file back to disk using the library.
"""

from collections import Counter


def delete_orcid_id(pct, count):
    """
    Docstring for delete_orcid_id

    :param pct: The levenshtein distance divided by the length of the anthology name
    :param distance: The levenshtein distance between the anthology name and best-matching ORCID name
    :param anthology_name: The name as listed in the paper metadata
    :param orcid_name: The best-matching name from the ORCID record
    :param all_orcid_names: All names returned by ORCID in the format "name (distance), name (distance), ..."
    :param orcid: The ORCID identifier
    :param anthology_id: The Anthology ID of the paper
    :return: True if the ORCID ID should be deleted, False otherwise

    We currently just delete if the pct match is over 58.8%.
    This number was chosen by manual inspection of the sorted results.
    https://github.com/acl-org/acl-anthology/pull/6859#issuecomment-3682339570
    """
    delete = float(pct) > 66.7 and count == 1

    return delete


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from acl_anthology import Anthology

    out_file = "distances.tsv"

    # load completed items from the distances TSV file
    db = {}
    counts = Counter()
    if Path(out_file).exists():
        with open(out_file) as f:
            for line in f:
                # pct match, distance, anthology_name, orcid_name,
                # all_orcid_names, orcid, anthology_id
                parts = line.rstrip().split("\t")
                if len(parts) == 7:
                    name = parts[2]
                    anthology_id = parts[-1]
                    orcid = parts[-2]
                    key = (anthology_id, name, orcid)
                    db[key] = parts
                    counts[key] += 1
            print("Loaded", len(db), "completed items", file=sys.stderr)

    anthology = Anthology(datadir=Path(__file__).parent.parent.parent / "data")
    # anthology = Anthology.from_repo()

    # iterate through all collections, then all papers,
    # deleting ORCIDs as needed
    for collection in anthology.collections.values():
        for paper in collection.papers():
            anthology_id = paper.full_id
            for author in paper.authors:
                name = author.name.as_first_last()

                if author.orcid:
                    key = (anthology_id, name, author.orcid)
                    # this shouldn't happen
                    if key not in db:
                        print(f"Found no key for {key}", file=sys.stderr)
                        continue

                    parts = db.get(key)
                    pct = float(parts[0])
                    count = counts.get(key, 1)

                    if delete_orcid_id(pct, count):
                        print(
                            f"Deleting ORCID {author.orcid} for {name} in {anthology_id} with pct={pct:.1f} count={count}",
                            file=sys.stderr,
                        )
                        author.orcid = None

        collection.save()
