#!/usr/bin/env python3

"""
Go through every paper in the Anthology, and find every <author>
with an orcid attribute. For each such author, query the ORCID
API and check that the name matches using string edit distance.
Print out tuples of (Anthology ID, author name, ORCID, distance).
Make sure to use the acl-anthology package from PyPI.
"""

#!/usr/bin/env python3

import sys
import requests
import unicodedata

from time import sleep

CACHE = {}


def fetch_names(orcid):
    if orcid in CACHE:
        return CACHE[orcid]

    sleep(0.1)

    url = f"https://pub.orcid.org/v3.0/{orcid}/person"
    headers = {"Accept": "application/json"}

    # check for 404 error
    try:
        r = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.HTTPError as e:
        r.raise_for_status()
        # chck if 404
        if e.response.status_code == 404:
            print(f"HTTP error for ORCID {orcid}: {e}", file=sys.stderr)
            CACHE[orcid] = ["404"]
            return CACHE[orcid]

    data = r.json()

    names = []

    name_block = data.get("name", {})
    try:
        given = name_block.get("given-names", {}).get("value")
    except AttributeError:
        given = ""
    try:
        family = name_block.get("family-name", {}).get("value")
    except AttributeError:
        family = ""

    if given and family:
        name = f"{given} {family}"
    elif given:
        name = given
    elif family:
        name = family
    else:
        name = ""

    names.append(name)

    other_names = data.get("other-names", {}).get("other-name", [])

    for on in other_names:
        content = on.get("content")
        if content:
            names.append(content)

    CACHE[orcid] = names
    return CACHE[orcid]


def edit_distance(a: str, b: str) -> int:
    a, b = a.lower(), b.lower()

    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a  # ensure a is longer
    # now len(a) >= len(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            ins = curr[j - 1] + 1
            delete = prev[j] + 1
            subst = prev[j - 1] + (ca != cb)
            curr.append(min(ins, delete, subst))
        prev = curr
    return prev[-1]


def remove_diacritics(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode('ASCII')


def munge_names(name):
    """
    Generate name variants:
    - original
    - remove middle names/initials
    - last first
    - remove diacritics
    """
    # if input is a list, return chained recursive call
    if isinstance(name, list):
        variants = []
        for n in name:
            variants.extend(munge_names(n))
        return variants

    variants = []
    variants.append(name)

    parts = name.split()
    if len(parts) > 2:
        # remove middle names/initials
        variants.append(f"{parts[0]} {parts[-1]}")

    if len(parts) == 2:
        # last first
        variants.append(f"{parts[1]} {parts[0]}")
    # remove diacritics
    if any(ord(c) > 127 for c in name):
        variants.append(remove_diacritics(name))

    return variants


if __name__ == "__main__":
    import sys
    import requests
    from pathlib import Path
    from acl_anthology import Anthology

    out_file = "distances.tsv"

    # load completed items
    completed = {}
    if Path(out_file).exists():
        with open(out_file) as f:
            for line in f:
                line = line.rstrip()
                parts = line.split("\t")
                if len(parts) == 7:
                    (
                        pct,
                        distance,
                        anthology_name,
                        orcid_name,
                        all_orcid_names,
                        orcid,
                        anthology_id,
                    ) = line.split("\t")
                    key = (anthology_id, orcid)
                    completed[key] = line
            print("Loaded", len(completed), "completed items", file=sys.stderr)

    # get script directory
    data_dir = Path(__file__).parent.resolve().parent.parent
    anthology = Anthology(datadir=data_dir / "data")

    out_fh = open(out_file, "a")

    for paper in anthology.papers():
        anthology_id = paper.full_id

        for author in paper.authors:

            if author.first:
                anthology_name = f"{author.first} {author.last}"
            else:
                anthology_name = author.last

            if author.orcid:
                if (anthology_id, author.orcid) in completed:
                    continue

                # Query the ORCID API
                names = fetch_names(author.orcid)

                # compute distance for each name, sort by distnace, print best match
                results = []
                exact_match_found = False
                for name in munge_names(anthology_name):
                    for orcid_name in munge_names(names):
                        distance = edit_distance(name, orcid_name)
                        results.append((orcid_name, distance))

                        if distance == 0:
                            exact_match_found = True
                            break
                    if exact_match_found:
                        break
                results = sorted(results, key=lambda x: x[1])

                orcid_name, distance = results[0]
                all_orcid_names = ", ".join([f"{n} ({d})" for n, d in results])

                pct = 100 * distance / len(anthology_name)

                # write to file "distances.tsv"
                output_line = [
                    f"{pct:.1f}",
                    str(distance),
                    anthology_name,
                    orcid_name,
                    all_orcid_names,
                    author.orcid,
                    paper.full_id,
                ]
                print(*output_line, sep="\t")
                print(*output_line, file=out_fh, sep="\t")
                out_fh.flush()

    out_fh.close()
