---
Title: Requesting Corrections
linktitle: Corrections
subtitle: How to submit corrections to the Anthology
date: "2020-01-22"
---

### Types of corrections

The staff of the ACL Anthology can process requests for both many types of corrections to data in the ACL Anthology.
These include correcting *metadata* and posting *errata* and *revisions* for scholarly works that are already published.
While this service can help correct post-publication problems, due to certain difficulties and liabilities, the corrections have certain limitations, which we describe here.

+ Corrections to **metadata** do not require the submission of a new PDF.
  Examples include correcting the spelling of a name or the title.
  These kinds of corrections are typically made to bring the metadata in line with what is on the PDF, which is taken to be authoritative.
  If the metadata changes impact the work's physical form (e.g., adding an additional author), a revision must also be supplied.
+ An **erratum** clarifies errors made in the original scholarly work.
  Usually these are just short notes, correcting statements, or changes to equations or other problems in the original, which need to be read alongside the original work.
+ A **revision** is a replacement to the original scholarly work.
  This format allows a corrected paper to be read independently of the original scholarly work, and typically does not highlight the original's errors.

Please take note of the following regarding errata and revisions:

+ The original published PDF is not invalidated.
  The original will still stand as published and cannot be withdrawn, and both will remain available and linked on the website.
+ The landing page for the work will indicate the availability of the erratum or revision.
+ We cannot retrofit any accompanying full volumes with either revisions or errata.
+ If possible, when generating your revision, it would be good to add the proper proceedings header and footer stamps, as well as the correct page numbering.
  Unfortunately, we cannot provide any assistance with this task.
+ Downstream consumers of the Anthology (e.g., search engines) should notice the changes in your work, but there are no guarantees of this.

### Correcting Metadata

For requests to change paper *metadata* (that do not require any PDF changes), please file [a Github issue](https://github.com/acl-org/acl-anthology/issues/new).[^1]
**Be sure to indicate the Anthology ID of the paper** (e.g., `P19-1017`).
Metadata changes are generally accepted if they comport with the PDF, which we take as authoritative.

[^1]: We prefer to work through Github issues since it simplifies our workflow.
   However, if your issue is sensitive, you can alternately contact us via email at anthology@aclweb.org.

The Anthology team will attend to the correction as we find time.
If you would like to expedite the process and are familiar with [git](https://git-scm.com), you can make the correction yourself and file a [pull request (PR)](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests).
To do this, first fork our repository so that you can make edits to your local copy.
Then, locate your file amongst our [authoritative XML files](https://github.com/acl-org/acl-anthology/tree/master/data/xml).
As an example, if the Anthology ID of your paper is `P19-10171`, then the file you will need to edit is [data/xml/P19.xml](https://github.com/acl-org/acl-anthology/blob/master/data/xml/P19.xml).
Find your entry from some identifying information, make the correction, and issue a PR against our `master` branch.
For smaller XML files, you can avoid having to clone the repository by [editing directly in the browser](https://help.github.com/en/github/managing-files-in-a-repository/editing-files-in-another-users-repository).

### Requesting revisions or errata

For requests to change paper *content* (either a revision or an erratum), [please use this form](https://forms.office.com/Pages/ResponsePage.aspx?id=DQSIkWdsW0yxEjajBLZtrQAAAAAAAAAAAAMAABqTSThUN0I2VEdZMTk4Sks3S042MVkxUEZQUVdOUS4u).
**Please note the following**:

- The PDF you submit needs to be retrievable via `wget` (please test this!)
- You need to provide a summary of the changes.
  This summary will be included in the Anthology, and should be written from a neutral,  scientific perspective.

If the metadata also needs to change, please also follow the instructions in the above section.

These conditions help us to process corrections more quickly.
We will do our best to process revisions or errata within six weeks, but do not make guarantees as to the processing time.
Submissions not meeting these standards will be rejected, potentially without notice.
