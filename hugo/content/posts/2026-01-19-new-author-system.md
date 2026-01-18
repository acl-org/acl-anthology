---
title: New Author System in the ACL Anthology
date: "2026-01-19"
description: >
    Introducing ORCID-centered author pages with explicit verification status
---

One of the most important jobs in the ACL Anthology is correctly matching papers to authors. When a new volume is ingested, the Anthology receives author information as textual metadata along with each PDF. When the site is built, author pages are created by assembling all papers that share an author.

This may sound straightforward, but in practice it’s difficult for two reasons: the same person may publish under multiple name variants (diacritics, middle initials, name changes), and many names are shared by multiple people. In practice, we resolve both of these issues using a manual process: one mechanism to group papers for a single author with multiple names, and another to explicitly assign a paper to a specific author using [a name ID]({{< ref "/info/names" >}}). This process is time-consuming and labor-intensive.

As of today, we are introducing a new author system that improves this process by centering on [ORCID iDs](https://orcid.org), a widely used persistent identifier for researchers.
Under this system, author pages use two URL patterns:

- **Verified authors** live at `https://aclanthology.org/people/{person-id}/`.
- **Unverified authors** live at `https://aclanthology.org/people/{person-id}/unverified`.

Verified authors are those for whom we have an explicit entry in our names database, usually created automatically when we ingest a paper with ORCID iD information attached to the author. Unverified authors are those for whom we do not have such an entry; these pages are created automatically from papers without ORCID iDs based on the simplified string form of the name in the paper's metadata. Verified pages show an ORCID icon that links to the author’s ORCID profile (except for some legacy verified entries, where we do not yet have an ORCID iD). Unverified pages are created automatically from papers without ORCID iDs; they include `/unverified/` in the URL and display a question mark next to the name. If you notice papers that don’t belong together, please use the “Fix author” link on the author page to report it.

The best way to help us (and to ensure your papers are correctly attributed) is to create an ORCID iD and add it everywhere you submit: in particular, to your OpenReview profile and to conference submission systems such as Softconf. This makes it much more likely that your ORCID travels with your paper into the Anthology and that your author page is created and maintained as a verified record.

For details and best practices, see our documentation on [verification]({{< ref "/info/verification" >}}) and [ORCID iDs]({{< ref "/info/orcid" >}}). Preview builds of these pages are available at https://preview.aclanthology.org/master-new-author-system/info/verification/ and https://preview.aclanthology.org/master-new-author-system/info/orcid. For deeper background on the motivation and design, you are welcome to read our [Author Page Plan](https://github.com/acl-org/acl-anthology/wiki/Author-Page-Plan) and [the extensive discussions](https://github.com/acl-org/acl-anthology/issues/623) that preceded it.
