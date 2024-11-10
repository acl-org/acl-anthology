---
Title: Requesting Corrections
linktitle: Corrections
subtitle: How to submit corrections to the Anthology
date: 2021-11-11
---

### Types of corrections

The staff of the ACL Anthology can process requests for many types of corrections.
We generally distinguish five types, loosely following the [ACM Publications Policy](https://www.acm.org/publications/policies/):

* Corrections to **metadata** do not require changing the PDF.
  Examples include correcting the spelling of a name or the title.
  These kinds of corrections are typically made to bring the metadata in line with what is on the PDF, which is taken to be authoritative.
  If changes to the metadata also require a change to the PDF (e.g., changing an author's name), a revision must also be supplied.
* An **erratum** clarifies errors made in the original scholarly work.
  Usually these are just short notes, corrective statements, or changes to equations or other problems in the original, which need to be read alongside the original work.
* A **revision** is a versioned replacement of the original scholarly work.
  This format allows a corrected paper to be read in place of the original scholarly work, and typically does not highlight the original's errors.
* A **retraction** occurs when serious, unrecoverable errors are discovered, which drastically affect the findings of the original work.
* A **removal** occurs in rare circumstances where serious ethical or legal issues arise, such as plagiarism.

Please take note of the following points regarding revisions and retractions.

* The original published PDF is not invalidated.
  The original will still stand as published and cannot be withdrawn, and both will remain available and linked on the website.
* The landing page for the work will indicate the availability of the erratum or revision.
* We cannot currently regenerate the full volumes, which will continue to contain only the original papers.
* We have no control over how downstream consumers of the Anthology, such as search engine, process the changes.

### Correcting Metadata

A request to change paper metadata (that does not require any PDF changes) can be submitted in several ways.

-  _(Preferred)_ Please file [a Github issue](https://github.com/acl-org/acl-anthology/issues/new?assignees=anthology-assist&labels=correction%2Cmetadata&template=01-metadata-correction.yml&title=Paper+Metadata%3A+%7Breplace+with+Anthology+ID%7D).
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

For requests to change paper *content* (either a revision or an erratum), again, please [file a Github issue](https://github.com/acl-org/acl-anthology/issues/new?assignees=anthology-assist&labels=correction%2Crevision&template=03-revision-or-errata.yml&title=Paper+Revision%7Breplace+with+Anthology+ID%7D).
**Please note the following**:

- Be sure to attach the revised PDF to the issue.
- For revisions, provide a brief summary of the changes.
  This summary will be included in the Anthology.
	Its intended audience is users of the Anthology, and should therefore be written from a neutral, scientific perspective.
- If the metadata also needs to change, please also follow the instructions in the previous section.
- If possible, when generating your revision, it would be good to add the proper proceedings header and footer stamps, as well as the correct page numbering.
  Unfortunately, we cannot provide any assistance with this task.

For revisions, the brief summary should allow readers to find the changed parts, but need not be too detailed.
Here are some good examples:

- *A sponsor was added to the Acknowledgments section.*
- *Added a footnote to page 8 describing data processing.*
- *Corrected a few citations; added Footnote 2 clarifying the baseline calculation; expanded the caption of Table 3; added a paragraph to the Related Works section.*

Following these instructions will help us to process corrections more quickly.
We will do our best to process revisions or errata within four weeks, but make no guarantees as to the processing time.
Submissions not meeting these standards will be rejected, potentially without notice.

A revision that changes the author list needs permission (see below).

### Retractions

To initiate a retraction, please communicate directly with the Anthology director.
Retractions often involve the organizing editors or chairs of the respective journal or conference.

Retractions result in the following changes in the Anthology:

* The paper is processed as a revision.
  Each page of the revised PDF is marked with a prominent watermark reading "RETRACTED".
* The paper's title and author list are displayed with ~~strikeout text~~ in the volume and event listings.
* The paper's canonical page contains a prominent notice of the retraction,
  Its title, author list, and abstract are presented in ~~strikeout text~~.
  No bibliographic files are generated, and the paper is not listed in the consolidated Anthology BibTeX file.
* The paper is removed entirely from the listing on the author page.

### Removal

Removals are rare events that are undertaken only in the most serious of situations, such as plagiarism or fraud.
A paper can be removed at the request of the scientific organization with jurisdiction over the paper.
For most papers within the Anthology, this is the [ACL](https://www.aclweb.org/), but any organization with publications in the Anthology (e.g., [AMTA](https://www.amtaweb.org/), [LREC](https://lrec-conf.org)) can also request the removal of a paper.
The Anthology staff does not adjudicate removal decisions.

A removal will result in the following changes to the Anthology:

* The paper PDF, along with all revisions and attachments, are removed from the Anthology.
  (They will, however, be preserved in the Anthology's private storage.)
* The associated book will either be regenerated or will be edited to remove the offending paper.
* The paper will be removed from all listings, including the volume page, any events pages it is associated with, and the author page.
* The paper's canonical page will be modified to contain a prominent notice of the removal.
  Its title and author list will be presented in ~~strikeout text~~.
  The abstract, if present, will be removed.
  No bibliographic files will be generated.

### Note on changes to author metadata

The Anthology generally accepts corrections to the author metadata that bring it into line with the PDF, which we treat as authoritative.
Example corrections include name spellings and details (such as initialization or the inclusion of a middle name), changes to author ordering, and even the addition of authors mistakenly left out of the metadata.
Because it is beyond our ability to keep track of the many differing policies governing conferences and journals whose proceedings we host, it is therefore up to those groups to ensure that PDF authorship is correct when proceedings are delivered to the Anthology for ingestion.

We reserve the right to seek permission or corroboration from the associated conference or workshop program chairs in unusual situations, such as removing or adding an author to a PDF revision.
In such cases, we will ask authors to arrange for this permission to be conveyed to us, either via email or on a Github issue.
