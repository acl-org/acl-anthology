---
Title: Verified authors
linktitle: Verification
subtitle: How the ACL Anthology verifies authors
date: "2025-12-29"
---
Every author appearing on a paper in the Anthology is given an author page. The ACL Anthology distinguishes between verified and unverified authors.

**A _verified_ author is one for whom we have an explicit entry in our names database.**
This can happen either automatically or manually. Entries are created automatically when a paper is ingested with ORCID iD information attached to the papers author(s). We also create entries manually when we intervene to disambiguate authors with similar names or who publish under multiple names. The top of the author's page will have an ORCID icon <i class="fab fa-orcid fa-xs align-middle text-verified ml-1"></i> linked to the ORCID profile (except for some legacy entries for which we do not yet have an ORCID iD).

The ORCID icon does not guarantee that all papers on the page belong to that author, however. This is because, once an author is verified, papers lacking an explicit ORCID iD but matching the name string will be included on the page unless the name is known to be ambiguous. The "Fix author" button should be used to alert the Anthology team of any errors.

**An _unverified_ author is one for whom we do not have an explicit entry in our names database.** Unverified pages have `/unverified/` appended to the URL. These pages are created automatically when a paper is ingested without ORCID iD information attached to the authors. Unverified author pages do not include a link to an ORCID profile, but instead include a question mark icon <i class="fas fa-question-circle fa-xs align-middle text-secondary ml-1"></i> next to the author's name.

For author names in our database that are known to be ambiguous, there will be an `/unverified/` page for any papers which have not been explicitly identified with a verified author.

### Verifying an author

1. Create an ORCID iD and populate it.

   We urge every author to create an [ORCID iD](https://orcid.org), and to supply this ID to publication systems such as OpenReview. The reason is that we use this information at ingestion time to match papers to an author. This is increasingly important as the size of the global scientific community increases, and ambiguous names proliferate. Please see our simple [ORCID iD guide]({{< ref "/info/orcid">}}) for information that will help match your papers to your Anthology page.

2. File an issue on GitHub.

   Navigate to the author page in the Anthology. If there is no ORCID icon, click the "Fix author" link at the bottom of the links on the righthand side of the page to create an issue from our template. Provide an ORCID iD along with other relevant information. Leave the issue open to be reviewed by Anthology staff.
