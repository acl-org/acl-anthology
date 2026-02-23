---
Title: Verified authors
linktitle: Verification
subtitle: How the ACL Anthology verifies authors
date: "2026-01-15"
---
Every author appearing on a paper in the Anthology is given an [author page]({{< ref "/info/author-pages" >}}). The ACL Anthology distinguishes between verified and unverified authors.

**A _verified_ author is one for whom we have an explicit entry in our names database.**
This can happen either automatically or manually. Entries are created automatically when a paper is ingested with ORCID iD information attached to the papers author(s). We also create entries manually when we intervene to disambiguate authors with similar names or who publish under multiple names. The top of the author's page will have an ORCID icon <i class="fab fa-orcid text-verified"></i> linked to the ORCID profile (except for some legacy entries for which we do not yet have an ORCID iD).

The ORCID icon does not guarantee that all papers on the page belong to that author, however. This is because, once an author is verified, papers lacking an explicit ORCID iD but matching the name string will be included on the page unless the name is known to be ambiguous. The "Fix author" button should be used to alert the Anthology team of any errors.

**An _unverified_ author is one for whom we do not have an explicit entry in our names database.** Unverified pages have `/unverified/` appended to the URL. These pages are created automatically when a paper is ingested without ORCID iD information attached to the authors. Unverified author pages do not include a link to an ORCID profile, but instead include a question mark icon <i class="fas fa-question-circle text-secondary"></i> next to the author's name.

Where an author name in our database is known to be ambiguous, there will be an `/unverified/` page listing any papers with that name which have not been explicitly identified with a specific verified author. These can be moved to a verified author page via a "Fix author" request.

## Verifying an author

You can submit an ORCID iD in order to verify an author of papers appearing in the Anthology. For full instructions see [Author pages]({{< ref "/info/author-pages" >}}).

## Related documentation

- [Author pages]({{< ref "/info/author-pages" >}})
- [ORCID iDs]({{< ref "/info/orcid" >}})
- [Names]({{< ref "/info/names" >}})
