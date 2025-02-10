---
Title: Requesting Corrections
linktitle: Corrections
subtitle: How to submit corrections to the Anthology
date: 2025-02-10
---

### What type of correction do you need?

Our central guiding corrections principle is that **we view the content of PDFs as authoritative**. If you see errors or inconsistencies in the metadata (author list, title, abstract), you need to first check to see if it matches the PDF.

This view drives three main types of corrections:

* _PDF corrections_. The PDF itself can be in error.
* _Metadata only_. Information presented in the Anthology may be different from the PDF. Examples include errors in the title, abstract, or author list.
* _Author disambiguation_. An author's papers might be spread across multiple author pages (one person, multiple pages), or a single author page might contain papers from different people (multiple people, one page).

Below we describe the process for addressing these types of corrections, in order of the frequency we encounter them.

### Metadata corrections

Corrections to **metadata** do not require changing the PDF.
These kinds of corrections bring the information presented in the Anthology in line with the authoritative PDF.

A request to change paper metadata can be submitted in two ways.

- Navigate to the paper's page in the ACL Anthology (e.g., [K17-1003](https://aclanthology.org/K17-1003/)). From there, click the yellow "Fix data" button. This will display a dialog that you can use to correct the title and abstract and fix issues with the author list.

  Submitting this form will create a Github issue with a JSON data block. This will then be validated by Anthology staff, and processed by a semi-automatic bulk corrections script on a weekly basis.

-  If you would like to expedite the process and are familiar with [git](https://git-scm.com), you can make the correction yourself and file a [pull request (PR)](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests).
    1. First, locate your file amongst our [authoritative XML files](https://github.com/acl-org/acl-anthology/tree/master/data/xml). The name of your file is the portion of the Anthology ID that comes before the hyphen.

    As an example, if the Anthology ID of your paper is `P19-10171`, then the file you will need to edit is [data/xml/P19.xml](https://github.com/acl-org/acl-anthology/blob/master/data/xml/P19.xml); if the Anthology ID of your paper is `2021.iwslt-1.28`, then the file you will need to edit is [data/xml/2021.iwslt.xml](https://github.com/acl-org/acl-anthology/blob/master/data/xml/2021.iwslt.xml).
    2. Find your entry in the XML file, and use Github's edit button to fix it and then to issue a PR against our `master` branch.
    3. For larger XML files, you may have to fork the repository first. [More information can be found here](https://help.github.com/en/github/managing-files-in-a-repository/editing-files-in-another-users-repository).

The Anthology team will attend to the correction as we find time.
Metadata changes are generally accepted if they are consistent with the PDF, which we take as authoritative.
However, please see the following note.

#### Note on changes to author metadata

Because it is beyond our ability to keep track of the many differing policies governing conferences and journals whose proceedings we host, it is therefore up to those groups to ensure that PDF authorship is correct when proceedings are delivered to the Anthology for ingestion.

We reserve the right to seek permission or corroboration from the associated conference or workshop program chairs in unusual situations, such as removing or adding an author to a PDF revision.
In such cases, we will ask authors to arrange for this permission to be conveyed to us, either (ideally) on the corresponding Github issue or via email.

### Author disambiguation

The Anthology builds author pages based on the string form of names found in paper metadata.
These pages are housed under https://aclanthology.org/people/, e.g., [Aravand Joshi](https://aclanthology.org/people/aravind-joshi).

There are two types of author disambiguation that we handle:

**One person, multiple author pages**.
This situation occurs when a person has multiple papers written under different names.
Often, these names are minor variations of each other (e.g., including or excluding a middle initial).

Sometimes, this is a simple mistake in the metadata that can be handled using the procedure described above.
However, if the metadata for the papers is correct, then we need to manually link the author pages.

**Multiple people, single author page**.

In this situation, many different people have published under the same name.
An example is [Yang Liu](https://aclanthology.org/people/yang-liu).
In this case, we have to manually assign IDs to the papers to create a separate author page, typically using their Ph.D. granting institution (e.g., [Yang Liu of Edinburgh](https://aclanthology.org/people/y/yang-liu-edinburgh/).

Both situations can be addressed by [filing an Author Page request](https://github.com/acl-org/acl-anthology/issues/new?template=02-name-correction.yml).

### PDF corrections

Our PDF corrections process loosely follows the [ACM Publications Policy](https://www.acm.org/publications/policies/):

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


#### Revisions and errata

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

#### Retractions

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

#### Removal

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
