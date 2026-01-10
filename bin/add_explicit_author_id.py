#!/usr/bin/env python3

"""
Use the Anthology module to read in the Anthology and then add an explicit id=SLUG attribute to every
<author> tag that doesn't already have an ID. We do this in two steps: first, we iterate through all
authors, and write an author file for them under data/yaml/people/{letter}/{slug}.yaml.
Then we iterate through the Anthology, and for each <author> tag that doesn't have an id, we set it to
the slug of the author file we just created.
"""

import os
import sys
import yaml
from acl_anthology import Anthology


def main():
    # one directory up from the current file
    basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    anthology = Anthology(datadir=f"{basedir}/data")

    # Create author files
    for slug in anthology.people:
        person = anthology.get_person(slug)

        filename = f"{basedir}/data/yaml/people/{slug[0]}.yaml"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'a', encoding='utf-8') as f:
            data = {
                slug: {
                    "canonical_name": {
                        "first": person.canonical_name.first,
                        "last": person.canonical_name.last,
                    }
                }
            }
            if person.orcid:
                data[slug]["orcid"] = person.orcid
            if len(person.names) > 1:
                data[slug]["variants"] = []
                for variant in person.names[1:]:
                    data[slug]["variants"].append({
                        "first": variant.first,
                        "last": variant.last,
                    })
            print(yaml.dump(data, f, allow_unicode=True))

    # # Update the Anthology XML with explicit IDs
    # for paper in anthology.papers:
    #     for author in xml_findall(paper, 'author'):
    #         if not xml_get_id(author):
    #             slug = xml_get_slug(author)
    #             xml_set_id(author, slug)

    # # Write the updated Anthology XML back to file
    # write_xml(anthology.xml, 'data/xml/anthology.xml')

if __name__ == "__main__":
    main()