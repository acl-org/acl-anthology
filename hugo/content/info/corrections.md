---
Title: Requesting Corrections
linktitle: Corrections
subtitle: How to submit corrections to the Anthology
date: 2025-08-02
---

### What type of correction do I need?

Our central guiding corrections principle is that **we view the content of PDFs as authoritative**. If you see errors or inconsistencies in the metadata (author list, title, abstract), you need to first check to see if it matches the PDF.

This view drives two main types of __paper-level corrections__:

* [_There are problems with the PDF_](#pdf-corrections). We can process corrections, revisions, errata, and retractions.
* [_The PDF is fine, but there are problems with the metadata_](#metadata-corrections). Errors in the title, abstract, author names, or list of authors.

Below, we describe the process for addressing these types of corrections.

Additionally, there are two main types of __corrections to author pages__. For these, please see [Author pages]({{< ref "/info/author-pages">}}).

* You have more than one author page. This occurs if you published papers under different variations of your name, or if you changed your name.
* Your papers are mixed with someone else's. If multiple people publish under the same name, we need to manually disambiguate them.

### Metadata corrections

Corrections to **metadata** do not require changing the PDF.
These kinds of corrections bring the information presented in the Anthology in line with the authoritative PDF.

A request to change paper metadata can be submitted in two ways.

- _Have us do the work_. You can submit an issue to Anthology staff.
   -  _(Preferred)_ Navigate to the paper’s page in the ACL Anthology (e.g., [K17-1003](https://aclanthology.org/K17-1003)). From there, click the yellow “Fix data” button. This will display a dialog that you can use to correct the title, abstract, and author information. Submitting this form will fill a Github issue template with a JSON data block. We process these semiautomatically on a weekly basis.
   -  If your issue is sensitive, you can alternately contact us via email at anthology@aclweb.org.
      Please be sure to include a link to the paper page in the Anthology in your email. These are typically
      processed on a monthly basis, in batches of corrections.
- _Make the change yourself_. [Follow the instructions here](https://github.com/acl-org/acl-anthology/wiki/Issuing-Pull-Requests-For-Corrections) to make the changes yourself and create a pull request against the Anthology repository. These are typically processed every few days, as we see them.

Metadata changes are generally accepted if they are consistent with the PDF, which we take as authoritative.

**Note on changes to author metadata**

Because it is beyond our ability to keep track of the many differing policies governing conferences and journals whose proceedings we host, it is therefore up to those groups to ensure that PDF authorship is correct when proceedings are delivered to the Anthology for ingestion.

We reserve the right to seek permission or corroboration from the associated conference or workshop program chairs in unusual situations, such as removing or adding an author to a PDF revision.
In such cases, we will ask authors to arrange for this permission to be conveyed to us, either (ideally) on the corresponding Github issue or via email.

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
  Unfortunately, we cannot provide any assistance with this task, but [this template from the ACLPUB2 repo](https://github.com/rycolab/aclpub2/blob/main/aclpub2/templates/watermarked_pdf.tex) may be helpful for this.

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
