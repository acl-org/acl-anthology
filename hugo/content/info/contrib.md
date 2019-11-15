---
Title: Information for Submitters
linktitle: Submitting
subtitle: General information on submitting proceedings to the ACL Anthology (for event chairs)
date: "2019-10-25"
---

This page contains general information about how to submit proceedings to the ACL Anthology.
If you are a workshop or publication chair whose job it is to submit your conference proceedings, this page should be helpful to you.
Please read through it so that you have an understanding of the ingestion process.

### Overview of the Submission Process

Please [contact the Anthology Director](mailto:anthology@aclweb.org) as soon as possible to register your intention to submit your proceedings.
**If you are a workshop chair attached to a main conference (e.g., ACL or EMNLP), the main conference publication chair should handle this for you.**
Conference-level publication chairs should assemble the following information for all volumes and workshops in their conference and send it to the director in a single email.
We need the following information from you:

-  **The full titles of all volumes** that you need identifiers for; and
-  **the date** you would like your volumes to be available to the world.
   (Your proceedings will be due **two weeks** prior to this negotiated date).

The full titles should not contain abbreviations, except parenthetically.
For example, "Proceedings of EMNLP 2019" is not a good title, but "Proceedings of the 2019 Meeting of the Conference on Empirical Methods in Natural Language Processing (EMNLP)" is a great one.
(We have plans in the works to collect short titles in the near future, for more concise display in various settings.}
If you have sub-volumes (e.g., long papers, short papers, demonstrations, tutorial abstracts), we suggest you append them after the full volume name.
For example, "Proceedings of the 2019 Meeting of the Conference on Empirical Methods in Natural Language Processing (EMNLP): Tutorial Abstracts".
You should also seek consistency with the names of your volumes from prior years.

With this information in hand, we will assign you a [list of Anthology identifiers](https://docs.google.com/spreadsheets/d/166W-eIJX2rzCACbjpQYOaruJda7bTZrY7MBw_oa7B2E/edit?usp=sharing) for use with ACLPUB.

Ingestion is a multi-step process:

1. **You** arrange your data (PDFs, BibTeX files, and metadata) using ACLPUB by following the instructions below.
   You will run a script to lay it out into a single directory, and then send a link to your tarball.
   **This tarball must be delivered to the Anthology director two weeks prior to your desired publication date**, which was negotiated when you first contacted us.
2. **We** ingest that data by running additional scripts that convert it into our authoritative format and commit it to [our Github repository](https://github.com/acl-org/acl-anthology/).
3. This becomes a pull request on [our pull requests page](https://github.com/acl-org/acl-anthology/pulls).
4. Once approved and merged into the `master` branch, the site will be automatically rebuilt (which happens twice a day) and made live.

You are responsible only for the Step 1: producting a minimally compliant XML file along with the associated PDFs and optionally other data (such as software).
This is handled by the [ACLPUB](https://github.com/acl-org/ACLPUB/) package, whose output is a minimally compliant XML file that can be ingested into [the Anthology's authoritative XML format](#authoritative-xml-format).
**Instructions for this can be found [in the ACLPUB package](https://github.com/acl-org/ACLPUB/blob/master/anthologize/README.md)**.
(Additionally, if you are using EasyChair, you will also want to use [our easychair scripts](https://github.com/acl-org/easy2acl), but please start with the ACLPUB documentation).

The remaining steps are handled by Anthology staff and use [Anthology tools](https://github.com/acl-org/acl-anthology/tree/master/bin/).

#### Notes about Softconf's START

The ingestion process is manual and requires time to execute and proofcheck, and as such, it's very helpful to ensure that your proceedings are in good order before sending the link.
Redoing the ingestion costs approximately the same time as the original ingestion and thus incurs significant additional expense for the volunteer staff.

If you are using START, the process is easier for you.
You need only supply the proceedings tarball (named `proceedings.tgz`) for each of the volumes and workshops that are part of your conference.
You can download this from START and send it directly to your publication chair.
If you are the publication chair, you can collect these and coordinate with the Anthology Director.

Please be aware of the following:

**Workshop identifiers**

START uses a formatted string to identify the volume ID.
The Anthology Director will assign templates to you for each volume your are submitting.
For main conference proceedings (e.g., NAACL long papers), for each volume, this looks like

> http://www.aclweb.org/anthology/N19-1%03d

since the volume ID has one digit and the paper three.
For workshops, it is

> http://www.aclweb.org/anthology/W19-38%02d

since there are only two digits for the paper ID.
Note again that the (zero-padded) paper ID '0' is used for front matter, '1' for the first paper, and so on.
(Note that this format will change in 2020 to allow for Anthology growth).

**Special Interest Groups**

For workshops, your conference publication chair should have noted special interest group affiliations and endorsements for workshops.
If you are using START, this information can be entered in the "meta" file.

Workshop chairs should contact the ACL Anthology Editor to receive their workshop number offset (the 'xx' portion of the ACL Anthology ID).
If your workshop is attached to a conference as a satellite event, please contact the proceedings chair for the main conference to receive the offset ID, as it is easiest to allocate offsets as a whole block.
Conversely, if you are the proceedings chair for a conference that has satellite workshops, please contact the ACL Anthology Editor with the final list of titles of the workshops (make certain the workshops will actually be run) so that the editor can allocate a suitable block of offsets to the workshops.
The current list of ingestion prefixes is [publicly visible](https://docs.google.com/spreadsheets/d/166W-eIJX2rzCACbjpQYOaruJda7bTZrY7MBw_oa7B2E/edit?usp=sharing) (but read-only).

### Copyright

For copyright transfers, you can use the default form at:

+ https://github.com/acl-org/ACLPUB/blob/master/doc/authors/ACL-copyright-form.pdf

Ask authors to sign the form, scan a B/W copy at 150 to 200 DPI for you as a
`.pdf` (or `.jpg` or `.png` if otherwise not possible). Name the forms using
the ACL Anthology identifiers, and send me a separate `.zip` or `.tgz`
archive as you would for the proceedings of your event (e.g., a file in the
archive might be `copyright-transfers/P11-1001.pdf`).
These copyrights should be delivered in bulk to the Anthology Editor when submitting the proceedings.

Note that if you are using the START system (softconf.com), there is a
digital form of this copyright transfer form, so you may not have to ask the
authors to print, sign and submit to you. You may be able to simply download
the `.zip` or `.tgz` version of the archived forms and submit them to
me. Please note this when submitting.

For both current and legacy events, it is good practice for the organizers
to attempt to obtain copyright transfers for their materials, but we will
ingest materials even if no copyright transfers are on file.

### ISBN Numbers

If you need to assign ISBN numbers, please provide the exact titles of each volume to be assigned an ISBN and forward this information to Priscilla Rasmussen, ACL Business Manager.

### Publication Date

By default, the publication of papers associated with a current event in the Anthology will be on the first day of the event (inclusive of workshops or tutorials).
If you prefer to have it published on a different date, please inform us.

### Errata and Corrections

If you get requests from authors needing to post errata or revised versions of the papers, or supplemental attachments after the publication of the proceedings, please ask them to submit revisions to the current ACL Anthology editor directly (see [Corrections]({{< relref "corrections.md" >}})).
Note that after the publiation date, corrections can only be applied to individual papers; the full proceedings volumes will not be replaced or revised.
