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
+ A **revision** is a replacement to the original scholarly work.
  This format allows a corrected paper to be read independently of the original scholarly work, and typically does not highlight the original's errors.
+ An **erratum** clarifies errors made in the original scholarly work.
  Usually these are just short notes, correcting statements, or changes to equations or other problems in the original, which need to be read alongside the original work.

Please take note of the following regarding revisions and errata:

+ The original published PDF is not invalidated.
  The original will still stand as published and cannot be withdrawn, and both will remain available and linked on the website.
+ The landing page for the work will indicate the availability of the erratum or revision.
+ We cannot retrofit any accompanying full volumes with either revisions or errata.
+ If possible, when generating your revision, it would be good to add the proper proceedings header and footer stamps, as well as the correct page numbering.
  Unfortunately, we cannot provide any assistance with this task.
+ Downstream consumers of the Anthology (e.g., search engines) should notice the changes in your work, but there are no guarantees of this.

### Correcting Metadata

A request to change paper metadata (that does not require any PDF changes) can be submitted in several ways.

-  (Preferred) Please file [a Github issue](https://github.com/acl-org/acl-anthology/issues/new?labels=correction&template=file-a-correction.md&title=Correction+to+Anthology+ID+XXX).
   **Be sure to indicate the Anthology ID of the paper** (e.g., `P19-1017` or `2020.acl-1.17`).
-  If your issue is sensitive, you can alternately contact us via email at anthology@aclweb.org.
   Again, please be sure to include the Anthology ID of the paper in your email.
-  If you would like to expedite the process and are familiar with [git](https://git-scm.com), you can make the correction yourself and file a [pull request (PR)](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests).
   To do this, first fork our repository so that you can make edits to your local copy.
   Then, locate your file amongst our [authoritative XML files](https://github.com/acl-org/acl-anthology/tree/master/data/xml).
   As an example, if the Anthology ID of your paper is `P19-10171`, then the file you will need to edit is [data/xml/P19.xml](https://github.com/acl-org/acl-anthology/blob/master/data/xml/P19.xml).
   Find your entry from some identifying information, make the correction, and issue a PR against our `master` branch.
   For smaller XML files, you can avoid having to clone the repository by [editing directly in the browser](https://help.github.com/en/github/managing-files-in-a-repository/editing-files-in-another-users-repository).

The Anthology team will attend to the correction as we find time.
Metadata changes are generally accepted if they are consistent with the PDF, which we take as authoritative.
However, please see the [note below about author changes](#note-on-author-changes).

### Revisions and errata

For requests to change paper *content* (either a revision or an erratum), again, please [file a Github issue](https://github.com/acl-org/acl-anthology/issues/new?labels=correction&template=file-a-correction.md&title=Correction+to+Anthology+ID+XXX).
**Please note the following**:

- Be sure to attach the revised PDF to the issue.
- For revisions, provide a brief summary of the changes.
  This summary will be included in the Anthology.
	Its intended audience is users of the Anthology, and should therefore be written from a neutral, scientific perspective.
- If the metadata also needs to change, please also follow the instructions in the previous section.

For revisions, the brief summary should allow readers to find the changed parts, but need not be too detailed.
Here are some good examples:

- *A sponsor was added to the Acknowledgments section.*
- *Added a footnote to page 8 describing data processing.*
- *Corrected a few citations; added Footnote 2 clarifying the baseline calculation; expanded the caption of Table 3; added a paragraph to the Related Works section.*

Following these instructions will help us to process corrections more quickly.
We will do our best to process revisions or errata within four weeks, but make no guarantees as to the processing time.
Submissions not meeting these standards will be rejected, potentially without notice.

A revision that changes the author list needs permission (see below).

### Note on author changes

Some conferences and workshops have a policy of disallowing authorship changes after the initial submission.
Because it is beyond our ability to track this, changes to the list of authors, whether in the PDF or in the metadata, require permission from the associated conference program chair or workshop/tutorial chair.
You are responsible for arranging for this permission to be conveyed to us, either via email or on your Github issue.
Permission is not required for the correction of obvious spelling errors or other typos or for changes to an author's name.
