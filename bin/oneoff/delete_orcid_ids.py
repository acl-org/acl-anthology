#!/usr/bin/env python3

"""
Load the TSV dumped by dump_orcid_info.py. Then, once again, go
through every paper in the Anthology, and find every <author> tag
with an orcid attribute. Call a function (stub for now) to
determine whether to retain the orcid or delete it.
Then save the file back to disk using the library.
"""


def delete_orcid_id(
    pct, distance, anthology_name, orcid_name, all_orcid_names, orcid, anthology_id
):
    return float(pct) == 0.0


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from acl_anthology import Anthology

    out_file = "distances.tsv"

    # load completed items from the distances TSV file
    db = {}
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
            print("Loaded", len(db), "completed items", file=sys.stderr)

    anthology = Anthology.from_repo()

    # iterate through all collections, then all papers,
    # deleting ORCIDs as needed
    for collection in anthology.collections.values():
        for paper in collection.papers():
            anthology_id = paper.full_id
            for author in paper.authors:
                if author.first:
                    name = f"{author.first} {author.last}"
                else:
                    name = author.last

                if author.orcid:
                    key = (anthology_id, name, author.orcid)
                    # this shouldn't happen
                    if key not in db:
                        print(f"Found no key for {key}", file=sys.stderr)
                        continue

                    parts = db.get(key)
                    pct = float(parts[0])

                    if delete_orcid_id(*parts):
                        print(
                            f"Deleting ORCID {author.orcid} for {name} in {anthology_id} with pct {pct:.1f}",
                            file=sys.stderr,
                        )
                        author.orcid = None

        collection.save()
