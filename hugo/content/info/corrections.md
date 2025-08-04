---
Title: Requesting Corrections
linktitle: Corrections
subtitle: How to submit corrections to the Anthology
date: 2025-08-02
---

### What type of correction do I need?

Our central guiding corrections principle is that **we view the content of PDFs as authoritative**. If you see errors or inconsistencies in the metadata (author list, title, abstract), you need to first check to see if it matches the PDF.

This view drives four main types of corrections:

* [_You have more than one author page_](#merging-author-pages). This occurs if you published papers under different variations of your name, or if you changed your name.
* [_Your papers are mixed with someone else's_](#splitting-author-pages). If multiple people publish under the same name, we need to manually disambiguate them.
* [_There are problems with the PDF_](#pdf-corrections). We can process corrections, revisions, errata, and retractions.
* [_The PDF is fine, but there are problems with the metadata_](#metadata-corrections). Errors in the title, abstract, author names, or list of authors.

Below we describe the process for addressing these types of corrections, in order of the frequency we encounter them.

### Metadata corrections

Corrections to **metadata** do not require changing the PDF.
These kinds of corrections bring the information presented in the Anthology in line with the authoritative PDF.

A request to change paper metadata can be submitted in two ways.

- Have us do the work. Please note that in order to reduce our workload, we process corrections in batches, merging them at the beginning of each month.
   -  _(Preferred)_ Please file a Github issue. This is best done by navigating to the paper's page and clicking the "Fix data" button, which will take you to a filled-out template for a Github issue.
   -  If your issue is sensitive, you can alternately contact us via email at anthology@aclweb.org.
      Please be sure to include a link to the paper page in the Anthology in your email.
- Make the change yourself. The advantage here is that your request can be approved and made live as soon as we see it. You can do this by [following the instructions here](https://github.com/acl-org/acl-anthology/wiki/Issuing-Pull-Requests-For-Corrections).

The Anthology team will attend to the correction. Metadata changes are generally accepted if they are consistent with the PDF, which we take as authoritative. Corrections are typically processed in monthly batches that are merged at the beginning of each month.
However, please see the following note.

**Note on changes to author metadata**

Because it is beyond our ability to keep track of the many differing policies governing conferences and journals whose proceedings we host, it is therefore up to those groups to ensure that PDF authorship is correct when proceedings are delivered to the Anthology for ingestion.

We reserve the right to seek permission or corroboration from the associated conference or workshop program chairs in unusual situations, such as removing or adding an author to a PDF revision.
In such cases, we will ask authors to arrange for this permission to be conveyed to us, either (ideally) on the corresponding Github issue or via email.

### Merging author pages

If you have published papers under different names, you will end up with multiple author profiles in the Anthology. We can merge these into a single page under your preferred name.

Please pay careful attention to the following steps.

1. **Ensure that each name is correct**. We treat the information on the PDF as authoritative; this means that the metadata should reflect exactly what is printed on the PDF. A common situation is that the name recorded in Anthology metadata (e.g., John P. Hancock) will not match what is displayed on the PDF (John Hancock). This needs to be corrected first. Please review your papers and [follow the steps here](#metadata-corrections) to correct any discrepancies. Sometimes, this will resolve the split pages.
2. Obtain [an ORCID](https://orcid.org). This is required to help with matching of future papers.
3. Fill out [an author page correction](https://github.com/acl-org/acl-anthology/issues/new?template=02-name-correction.yml). A Github issue is our preferred mechanism, but you can also email [the Anthology director](mailto:anthology@aclweb.org).
4. Finally, to avoid issues in the future, ensure that the name you use on papers is properly recorded in your profile in publication management systems such as [Open Review](https://openreview.net), [Softconf](https://softconf.com), [EasyChair](https://easychair.org), and so on.

Anthology staff will address your issue as quickly as possible.
An example merged author profile is [Aravand Joshi](https://aclanthology.org/people/aravind-joshi).

### Splitting author pages

When multiple authors publish under the same name, we disambiguate them by manually assigning an ID to one or more of the authors, and then associating that ID with each of their papers.

We need the following information from you:
1. Your [ORCID](https://orcid.org/), which will help us assign future papers to you correctly.
2. The name of the institution from which you received your highest degree (e.g., where you got your Ph.D.), or where you expect to receive it (for students).

Anthology staff will assign an ID to you comprising your canonical name (e.g., [yang-liu]() for "Yang Liu") and this institution. This page will be associated with your ORCID and will become your permanent Anthology author page.

To file a author split request, we prefer you to use [this Github issue](https://github.com/acl-org/acl-anthology/issues/new?template=02-name-correction.yml). A link to this template can also be found on any author page under the "Fix author" button. An example different authors published under the same name is [Yang Liu (of Edinburgh)](https://aclanthology.org/people/yang-liu-edinburgh/) and [Yang Liu (of Peking University)](https://aclanthology.org/people/yang-liu-pk).

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
