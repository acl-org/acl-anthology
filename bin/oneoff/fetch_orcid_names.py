#!/usr/bin/env python3

import sys
import requests
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
    # print(json.dumps(data, indent=2))

    names = []

    name_block = data.get("name", {})

    def get_part(part):
        try:
            return name_block.get(part, {}).get("value", "")
        except AttributeError:
            return ""

    given = get_part("given-names")
    family = get_part("family-name")

    if given and family:
        name = f"{given} {family}"
    elif given:
        name = given
    elif family:
        name = family
    else:
        name = ""

    names.append(name)

    # get the "credit name"
    credit_name = get_part("credit-name")
    if credit_name and credit_name != name:
        names.append(credit_name)

    other_names = data.get("other-names", {}).get("other-name", [])

    for on in other_names:
        content = on.get("content")
        if content:
            names.append(content)

    CACHE[orcid] = names
    return CACHE[orcid]


if __name__ == "__main__":
    import sys

    for orcid in sys.argv[1:]:
        names = fetch_names(orcid)
        print(f"ORCID {orcid} has names: {names}")
