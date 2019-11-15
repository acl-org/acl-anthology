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

| Deadline                    | Step                                            |
|-----------------------------|-------------------------------------------------|
| Before submission deadline  | [Register your meeting](#register-your-meeting) |
| Before submission deadline  | [Request ISBNs](#isbn-numbers)                  |
| 2 weeks before publication  | [Submit your data](#submit-your-data)           |
| 2 weeks before publication  | [Submit copyright transfer forms](#copyright)   |
| After publication           | [Making corrections](#errata-and-corrections)   |

### Register your meeting

All publications chairs need to obtain a volume ID, of the form `X99-9` for conferences and `W99-99` for workshops. See [Anthology Identifiers]({{< relref "ids.md" >>}}) for more information.
This should be done before the paper submission deadline for your conference.

If you are chairing a meeting attached as a satellite of a main conference (e.g., ACL or EMNLP), please work with the main conference publication chair to receive your volume ID.

If you are a conference publications chair, you must register your intention to submit your proceedings. Assemble the following information for all volumes and workshops in their conference and send it to [the Anthology Director](mailto:anthology@aclweb.org) in a single email.
We need the following information from you:

-  **The full titles of all volumes** (main conference and workshop) that you need identifiers for ([excellent example](https://docs.google.com/spreadsheets/d/13F1XhnT4PsiN-ZXcpv6QUp5A2qlr6-W9MoDgCkBOw9w/edit#gid=0)); and
-  **The date** you would like your volumes to be available to the world.
   (Your proceedings will be due **two weeks** prior to this negotiated date).

The full titles should not contain abbreviations, except parenthetically.
For example, "Proceedings of EMNLP 2019" is not a good title, but "Proceedings of the 2019 Meeting of the Conference on Empirical Methods in Natural Language Processing (EMNLP)" is a great one.
If you have sub-volumes (e.g., long papers, short papers, demonstrations, tutorial abstracts), we suggest you append them after the full volume name.
For example, "Proceedings of the 2019 Meeting of the Conference on Empirical Methods in Natural Language Processing (EMNLP): Tutorial Abstracts".
You should also seek consistency with the names of your volumes from prior years.

If your conference has satellite workshops, please make certain the workshops will actually be run.

By default, the publication of papers associated with an event in the Anthology will be on the first day of the event (inclusive of workshops or tutorials).
If you prefer to have it published on a different date, please inform us when you register.

With this information in hand, we will assign you a [list of Anthology identifiers](https://docs.google.com/spreadsheets/d/166W-eIJX2rzCACbjpQYOaruJda7bTZrY7MBw_oa7B2E/edit?usp=sharing) for use with ACLPUB.

### Prepare your data

Prepare your data (PDFs, BibTeX files, attachments, and metadata) by following the instructions below. You will end up with a tarball; this tarball (or a link to it) must be delivered to the Anthology director **two weeks prior to your desired publication date**, which was negotiated when you first contacted us.

For meetings using [Softconf](https://www.softconf.com)'s [STARTv2 conference management system](https://www.softconf.com/about/start-v2-mainmenu-26), data preparation is handled by the [ACLPUB](https://github.com/acl-org/ACLPUB/) package, whose output can be ingested into the Anthology.

- [How to generate proceedings from START](https://github.com/acl-org/acl-pub) (for all publications chairs)
- [How to compile the proceedings into Anthology format](https://github.com/acl-org/ACLPUB/blob/master/anthologize/README.md) (for conference-level publications chairs only)

For meetings using EasyChair, you will first want to use [our easy2acl scripts](https://github.com/acl-org/easy2acl), which convert EasyChair proceedings into the same format that START generates.

The remaining steps are handled by Anthology staff and use [Anthology tools](https://github.com/acl-org/acl-anthology/tree/master/bin/):

- We ingest that data by running additional scripts that convert it into our authoritative format and commit it to [our Github repository](https://github.com/acl-org/acl-anthology/).
- This becomes a pull request on [our pull requests page](https://github.com/acl-org/acl-anthology/pulls).
- Once approved and merged into the `master` branch, the site will be automatically rebuilt (which happens twice a day) and made live.

**Special Interest Groups**

For workshops, your conference publication chair should have noted special interest group affiliations and endorsements for workshops.
If you are using START, this information can be entered in the "meta" file.

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

### Errata and Corrections

If you get requests from authors needing to post errata or revised versions of the papers, or supplemental attachments after the publication of the proceedings, please ask them to submit revisions to the current ACL Anthology editor directly (see [Corrections]({{< relref "corrections.md" >}})).
Note that after the publiation date, corrections can only be applied to individual papers; the full proceedings volumes will not be replaced or revised.
