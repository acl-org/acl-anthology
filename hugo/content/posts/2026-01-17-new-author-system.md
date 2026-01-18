---
title: New Author System in the ACL Anthology
date: "2026-01-17"
description: >
    Introducing ORCID-centered author pages with explicit verification status
---

One of the most important jobs in the ACL Anthology is correctly matching papers to authors. When a new volume is ingested, the Anthology receives author information as textual metadata along with each PDF. When the site is built, author pages are created by assembling all papers that share an author.

This may sound straightforward, but in practice it’s difficult for two reasons: the same person may publish under multiple name variants (diacritics, middle initials, name changes), and many names are shared by multiple people. In practice, we resolve both of these issues using a manual process: one mechanism to group papers for a single author with multiple names, and another to explicitly assign a paper to a specific author using [a name ID]({{< ref "/info/names" >}}). This process is time-consuming and labor-intensive.

As of today, we are introducing a new author system that improves this process by centering on [ORCID iDs](https://orcid.org), a widely used persistent identifier for researchers.
Under this system, author pages use two URL patterns:

- **Verified authors** are those for whom we have an explicit entry in our names database. These pages have the format `https://aclanthology.org/people/{person-id}/`.
- **Unverified authors** are those for whom we do not have such an entry. These pages have the format `https://aclanthology.org/people/{person-id}/unverified`.

If you notice papers that don’t belong together, you can use the “Fix author” link on the author page to report it.

The best way to ensure your papers are correctly attributed is to create an ORCID iD and add it everywhere you submit papers: in particular, to your OpenReview profile and to conference submission systems such as Softconf.

For more information, you can read about how we [verify authors]({{< ref "/info/verification" >}}) and how we use [ORCID iDs]({{< ref "/info/orcid" >}}).
