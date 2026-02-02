"""
Computes statistics of the current state of the Anthology database,
including counts of papers, people, etc. broken down by publication year.
Counts of unique authors (people) are given by year as well as overall ('*' row).
Prints these as CSV to stdout and writes summary statistics to stderr.

Run this script periodically to be able to visualize trends over time
for data that may change after the publication is added
(e.g. author verification/ORCID adoption rate).

@author: Nathan Schneider (@nschneid)
@since: 2026-02-01
"""

import sys
from collections import defaultdict, Counter
import pandas

from acl_anthology import Anthology
from acl_anthology.utils.ids import is_verified_person_id

anthology = Anthology('data')

papers_by_year, doi_papers_by_year = Counter(), Counter()
solo_papers_by_year, max_authors_by_year = Counter(), Counter()
volumes_by_year, doi_volumes_by_year, events_by_year = Counter(), Counter(), Counter()
authorships_by_year, explicit_authorships_by_year, verif_authorships_by_year = (
    Counter(),
    Counter(),
    Counter(),
)
orcid_authorships_by_year, orcid_suffix_authorships_by_year = Counter(), Counter()
papers_by_venue_year = defaultdict(Counter)
uniq_authors_by_year, uniq_verif_authors_by_year = defaultdict(set), defaultdict(set)
uniq_orcid_authors_by_year, uniq_orcid_suffix_authors_by_year = defaultdict(
    set
), defaultdict(set)
uniq_degree_authors_by_year = defaultdict(set)
for p in anthology.papers():
    if p.is_deleted:
        continue
    papers_by_year[p.year] += 1
    if p.doi:
        doi_papers_by_year[p.year] += 1
    else:
        doi_papers_by_year[p.year] += 0
    if len(p.authors) == 1:
        solo_papers_by_year[p.year] += 1
    if len(p.authors) > max_authors_by_year[p.year]:
        max_authors_by_year[p.year] = len(p.authors)
    for a in p.authors:
        if a.id:
            explicit_authorships_by_year[p.year] += 1
        person = anthology.resolve(a)
        authorships_by_year[p.year] += 1
        uniq_authors_by_year[p.year].add(person)
        uniq_authors_by_year['*'].add(person)
        if is_verified_person_id(person.id):
            verif_authorships_by_year[p.year] += 1
            uniq_verif_authors_by_year[p.year].add(person)
            uniq_verif_authors_by_year['*'].add(person)
            if person.orcid:
                orcid_authorships_by_year[p.year] += 1
                uniq_orcid_authors_by_year[p.year].add(person)
                uniq_orcid_authors_by_year['*'].add(person)
                if person.id[-2].isdigit():
                    orcid_suffix_authorships_by_year[p.year] += 1
                    uniq_orcid_suffix_authors_by_year[p.year].add(person)
                    uniq_orcid_suffix_authors_by_year['*'].add(person)
            if person.degree:
                uniq_degree_authors_by_year[p.year].add(person)
                uniq_degree_authors_by_year['*'].add(person)
            # if __person.id ends with institution suffix__ --
            # # not clear that there's a good way to identify these! (the canonical name slug is not always the base author ID):
            #     print(person.id, file=sys.stderr)
            #     degree_suffix_authorships_by_year[p.year] += 1
            #     uniq_degree_suffix_authors_by_year[p.year].add(person)
            #     uniq_degree_suffix_authors_by_year['*'].add(person)
for v in anthology.volumes():
    volumes_by_year[v.year] += 1
    if v.doi:
        doi_volumes_by_year[v.year] += 1
    else:
        doi_volumes_by_year[v.year] += 0
for e in anthology.events.keys():
    venue, year = e.rsplit('-', 1)
    events_by_year[year] += 1
    if venue in {
        'coling',
        'cl',
        'acl',
        'aacl',
        'eacl',
        'naacl',
        'starsem',
        'semeval',
        'tacl',
        'wmt',
    }:
        for v in anthology.events[e].volumes():
            papers_by_venue_year[venue][year] += sum(1 for x in v.papers())
num_uniq_authors_by_year = {
    year: len(auths) for year, auths in uniq_authors_by_year.items()
}
num_uniq_verif_authors_by_year = {
    year: len(auths) for year, auths in uniq_verif_authors_by_year.items()
}
num_uniq_orcid_authors_by_year = {
    year: len(auths) for year, auths in uniq_orcid_authors_by_year.items()
}
num_uniq_orcid_suffix_authors_by_year = {
    year: len(auths) for year, auths in uniq_orcid_suffix_authors_by_year.items()
}
num_uniq_degree_authors_by_year = {
    year: len(auths) for year, auths in uniq_degree_authors_by_year.items()
}


data = pandas.DataFrame(
    {
        'papers': papers_by_year,
        'doi_papers': doi_papers_by_year,
        'explicit_authorships': explicit_authorships_by_year,
        'authorships': authorships_by_year,
        'solo_authorships': solo_papers_by_year,
        'max_authors': max_authors_by_year,
        'verif_authorships': verif_authorships_by_year,
        'orcid_authorships': orcid_authorships_by_year,
        'orcid_suffix_authorships': orcid_suffix_authorships_by_year,
        'uauthors': num_uniq_authors_by_year,
        'verif_uauthors': num_uniq_verif_authors_by_year,
        'orcid_uauthors': num_uniq_orcid_authors_by_year,
        'orcid_suffix_uauthors': num_uniq_orcid_suffix_authors_by_year,
        'degree_uauthors': num_uniq_degree_authors_by_year,
        'evts': events_by_year,
        'vols': volumes_by_year,
        'doi_vols': doi_volumes_by_year,
    }
).sort_index()
data['pctdoi_papers'] = data['doi_papers'] / data['papers']
data['pctdoi_vols'] = data['doi_vols'] / data['vols']

YR = "2025"  # latest full year
print(
    f'''
Headline Results

Overall
-------

{sum(events_by_year.values())} events
{sum(volumes_by_year.values())} volumes, {sum(doi_volumes_by_year.values())} ({sum(doi_volumes_by_year.values())/sum(volumes_by_year.values()):.0%}) with DOIs
{sum(papers_by_year.values())} papers, {sum(doi_papers_by_year.values())} ({sum(doi_papers_by_year.values())/sum(papers_by_year.values()):.0%}) with DOIs
{num_uniq_authors_by_year['*']} people: \
    {num_uniq_authors_by_year['*']-num_uniq_verif_authors_by_year['*']} ({(num_uniq_authors_by_year['*']-num_uniq_verif_authors_by_year['*'])/num_uniq_authors_by_year['*']:.0%}) unverified, \
    {num_uniq_orcid_authors_by_year['*']} ({num_uniq_orcid_authors_by_year['*']/num_uniq_authors_by_year['*']:.0%}) verified with ORCID, \
    {num_uniq_verif_authors_by_year['*']-num_uniq_orcid_authors_by_year['*']} ({(num_uniq_verif_authors_by_year['*']-num_uniq_orcid_authors_by_year['*'])/num_uniq_authors_by_year['*']:.0%}) verified without ORCID
... {num_uniq_degree_authors_by_year['*']} people have a registered degree institution
... Of the ORCID-verified people, {num_uniq_orcid_suffix_authors_by_year['*']} ({num_uniq_orcid_suffix_authors_by_year['*']/num_uniq_orcid_authors_by_year['*']:.0%}) have an ORCID-based ID
{sum(authorships_by_year.values())} authorships ({sum(authorships_by_year.values())/sum(papers_by_year.values()):.2} per paper; {sum(solo_papers_by_year.values())} solo-authored papers; max authors per paper = {max(max_authors_by_year.values())})
... {sum(verif_authorships_by_year.values())} ({sum(verif_authorships_by_year.values())/sum(authorships_by_year.values()):.0%}) verified
... {sum(orcid_authorships_by_year.values())} ({sum(orcid_authorships_by_year.values())/sum(authorships_by_year.values()):.0%}) with ORCID
... {sum(explicit_authorships_by_year.values())} ({sum(explicit_authorships_by_year.values())/sum(authorships_by_year.values()):.0%}) explicit author ID at paper level

{YR}
----
{events_by_year[YR]} events
{volumes_by_year[YR]} volumes, {doi_volumes_by_year[YR]} ({doi_volumes_by_year[YR]/volumes_by_year[YR]:.0%}) with DOIs
{papers_by_year[YR]} papers, {doi_papers_by_year[YR]} ({doi_papers_by_year[YR]/papers_by_year[YR]:.0%}) with DOIs
{num_uniq_authors_by_year[YR]} people publishing that year: \
    {num_uniq_authors_by_year[YR]-num_uniq_verif_authors_by_year[YR]} ({(num_uniq_authors_by_year[YR]-num_uniq_verif_authors_by_year[YR])/num_uniq_authors_by_year[YR]:.0%}) unverified, \
    {num_uniq_orcid_authors_by_year[YR]} ({num_uniq_orcid_authors_by_year[YR]/num_uniq_authors_by_year[YR]:.0%}) verified with ORCID, \
    {num_uniq_verif_authors_by_year[YR]-num_uniq_orcid_authors_by_year[YR]} ({(num_uniq_verif_authors_by_year[YR]-num_uniq_orcid_authors_by_year[YR])/num_uniq_authors_by_year[YR]:.0%}) verified without ORCID
... {num_uniq_degree_authors_by_year[YR]} of these people have a registered degree institution
... Of the ORCID-verified people, {num_uniq_orcid_suffix_authors_by_year[YR]} ({num_uniq_orcid_suffix_authors_by_year[YR]/num_uniq_orcid_authors_by_year[YR]:.0%}) have an ORCID-based ID
{authorships_by_year[YR]} authorships ({authorships_by_year[YR]/papers_by_year[YR]:.2} per paper; {solo_papers_by_year[YR]} solo-authored papers; max authors per paper = {max_authors_by_year[YR]})
... {verif_authorships_by_year[YR]} ({verif_authorships_by_year[YR]/authorships_by_year[YR]:.0%}) verified
... {orcid_authorships_by_year[YR]} ({orcid_authorships_by_year[YR]/authorships_by_year[YR]:.0%}) with ORCID
... {explicit_authorships_by_year[YR]} ({explicit_authorships_by_year[YR]/authorships_by_year[YR]:.0%}) explicit author ID at paper level
''',
    file=sys.stderr,
)


print(data.to_csv(), end='')
