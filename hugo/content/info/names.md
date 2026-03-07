---
Title: Names in the ACL Anthology
linktitle: Names
subtitle: How the Anthology deals with names
date: "2026-01-15"
---

This page explains how the Anthology creates author pages and groups papers by authors. Its main topics include:

* Author pages and name slugs
* Disambiguating names
* Matching papers to authors

## Names in paper metadata

When a volume is ingested, we receive a list of authors for each paper as text metadata: given name(s) and family name, plus optional additional information. These “name strings” are what you see on PDFs and in BibTeX exports. (The Anthology policy is that these name strings should match what is on the PDF, which we treat as authoritative.)

We distinguish between a **name** or **name string** (the textual representation of a person’s name on a paper) and a **person** (the real-world individual behind the name).

Our goal is to create author pages which correspond to a real person.
The difficulty is that a single person may publish under multiple name variants (diacritics, middle initials, different transliterations, name changes), and multiple people may publish under the same name. Both scenarios can be resolved either manually or automatically, as described below.

## Person IDs

By default, person IDs are derived from the person's full name, creating a **slug** from it. A slug is a normalized, URL-safe representation of a name: lowercased and hyphenated, without any punctuation or diacritics, other than a hyphen separator.

When we manually resolve an ambiguous name, we create a person ID for each author. At least one of the authors requires an explicit disambiguator appended to the slug. In an attempt to keep identifiers human-focused (i.e., not numeric), by convention we use the name or acronym of the institution where the author earned (or is expected to earn) their highest degree at the time they became known to the Anthology.

For example, if there are two authors named "Alex Smith", one with a Ph.D. from Stanford and the other first publishing while an undergrad at Tsinghua, one of them might be assigned `alex-smith`, while the other would be given `alex-smith-stanford` or `alex-smith-tsinghua`, respectively. These extended slugs function as unique person IDs.

## Creating author pages

[Author pages]({{< ref "/info/author-pages" >}}) are created automatically when the Anthology site is built (following any change to the database).
This is done by (a) reading names off paper metadata and (b) grouping them according to our internal database of verified authors.

A verified author is one for whom we have an explicit entry in our names database. This can happen either automatically (when a paper is ingested with ORCID iD information attached to the author) or manually (when we intervene to disambiguate authors with similar names or who publish under multiple names).
We then create author pages of two types:

- **Verified author pages**: `https://aclanthology.org/people/{person-id}/`
- **Unverified author pages**: `https://aclanthology.org/people/{name-slug}/unverified/`

The presence of `/unverified/` in the URL is a signal that the page was created automatically from name-only metadata.

For more on what “verified” means (and what the icons on author pages indicate), see [Verification]({{< ref "/info/verification" >}}).

## Disambiguating names

When authors report problems with the set of papers assigned to their author page, there are a number of actions we take.

The first is to **ensure that the metadata matches the PDF**. Anthology policy is to treat the PDF as authoritative, so that each name in the metadata should match what is on the PDF. Many issues can be resolved by simply correcting this metadata using the "Fix data" button on each paper page.

Problems with actual ambiguity can be addressed in two ways:

- **Merge name variants** that refer to the same person, so their publications appear under one verified page.
- **Separate ambiguous names** so that publications by different people do not appear on the same page.

Both of these are initiated using the "Fix Author" button displayed on the righthand side of each author page. This will fill out a GitHub issue template that we can use to process the request.

## ORCID iDs: the best way to disambiguate

ORCID iDs are persistent identifiers for people. Providing an ORCID iD dramatically improves our ability to match papers to the correct author, especially as the community grows and name collisions become more common.

If you are an author, we strongly encourage you to create an ORCID iD and add it to your submission systems (especially OpenReview, and also Softconf where applicable). See [ORCID iDs]({{< ref "/info/orcid" >}}) for best practices.

## Related documentation

- [Author pages]({{< ref "/info/author-pages" >}})
- [Verification]({{< ref "/info/verification" >}})
- [ORCID iDs]({{< ref "/info/orcid" >}})
- [IDs]({{< ref "/info/ids" >}}) (paper/volume identifiers, not person identifiers)
