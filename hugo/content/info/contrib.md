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

| Deadline                   | Step                                            |
|----------------------------|-------------------------------------------------|
| ASAP                       | [Register your meeting](#register-your-meeting) |
| 2 weeks before publication | [Submit your data](#submit-your-data)           |
| 2 weeks before publication | [Submit copyright transfer forms](#copyright)   |
|                            | [Request ISBNs](#isbn-numbers)                  |
| After publication          | [Making corrections](#errata-and-corrections)   |

#### Publication Date

By default, the publication of papers associated with a current event in the Anthology will be on the first day of the event (inclusive of workshops or tutorials).
If you prefer to have it published on a different date, please inform us.

### Register your meeting

All publications chairs need to obtain a volume ID, of the form `X99-9` for conferences and `W99-99` for workshops. See [Volume and Paper IDs](#volume-and-paper-ids) for more information.

If you are chairing a meeting attached as a satellite of a main conference (e.g., ACL or EMNLP), please contact the publications chair for the main conference to receive 

If you are a conference publications chair, you must register your intention to submit your proceedings. Assemble the following information for all volumes and workshops in their conference and send it to [the Anthology Director](mailto:anthology@aclweb.org) in a single email.
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

If your conference has satellite workshops, please make certain the workshops will actually be run.

With this information in hand, we will assign you a [list of Anthology identifiers](https://docs.google.com/spreadsheets/d/166W-eIJX2rzCACbjpQYOaruJda7bTZrY7MBw_oa7B2E/edit?usp=sharing) for use with ACLPUB.

### Prepare your data

Prepare your data (PDFs, BibTeX files, and metadata) using ACLPUB by following the instructions below.
   You will run a script to lay it out into a single directory, and then send a link to your tarball.
   **This tarball must be delivered to the Anthology director two weeks prior to your desired publication date**, which was negotiated when you first contacted us.

This is handled by the [ACLPUB](https://github.com/acl-org/ACLPUB/) package, whose output is a minimally compliant XML file that can be ingested into [the Anthology's authoritative XML format](#authoritative-xml-format).
**Instructions for this can be found [in the ACLPUB package](https://github.com/acl-org/ACLPUB/blob/master/anthologize/README.md)**.
(Additionally, if you are using EasyChair, you will also want to use [our easychair scripts](https://github.com/acl-org/easy2acl), but please start with the ACLPUB documentation).

The remaining steps are handled by Anthology staff and use [Anthology tools](https://github.com/acl-org/acl-anthology/tree/master/bin/):

- We ingest that data by running additional scripts that convert it into our authoritative format and commit it to [our Github repository](https://github.com/acl-org/acl-anthology/).
- This becomes a pull request on [our pull requests page](https://github.com/acl-org/acl-anthology/pulls).
- Once approved and merged into the `master` branch, the site will be automatically rebuilt (which happens twice a day) and made live.

#### Notes about Softconf's START

The ingestion process is manual and requires time to execute and proofcheck, and as such, it's very helpful to ensure that your proceedings are in good order before sending the link.
Redoing the ingestion costs approximately the same time as the original ingestion and thus incurs significant additional expense for the volunteer staff.

If you are using START, the process is easier for you.
You need only supply the proceedings tarball (named `proceedings.tgz`) for each of the volumes and workshops that are part of your conference.
You can download this from START and send it directly to your publication chair.
If you are the publication chair, you can collect these and coordinate with the Anthology Director.

### Volume and Paper IDs

START uses a formatted string to identify each volume.
The Anthology Director will assign templates to you for each volume you are submitting.
For main conference proceedings (e.g., NAACL long papers), for each volume, this looks like

> http://www.aclweb.org/anthology/N19-1%03d

since the volume ID has one digit and the paper three.
For workshops, it is

> http://www.aclweb.org/anthology/W19-38%02d

since there are only two digits for the paper ID.
The (zero-padded) paper ID '0' is used for front matter, '1' for the first paper, and so on.
(This format will change in 2020 to allow for Anthology growth).

**Special Interest Groups**

For workshops, your conference publication chair should have noted special interest group affiliations and endorsements for workshops.
If you are using START, this information can be entered in the "meta" file.

#### Canonical IDs and URLs

Currently, we assign each paper in the ACL Anthology a unique 8-character identifier, so that we can easily locate papers and reference them.
The identifier is assigned by the current is in the form of a letter, a two digit year, and a 4 digit paper ID (e.g., P18-1024).
The paper ID decomposes into a volume ID and a paper ID.
For large or prominent events related to ACL or its sister organizations that recur on a yearly basis, we use a separate lettered prefix (e.g., ACL, which is 'P'), the volume ID is 1 digit and the paper ID is 3 digits.
For all other smaller events, we use the 'W' prefix.
Here, the volume ID is 2 digits, and the paper ID 2 digits.
These events therefore accommodate up to 99 papers.
If there are more than 99 papers, they need to be broken out into two separate volume IDs.
Both paper and volume IDs are zero-padded to ensure that filenames have a fixed width.

<table class="table table-bordered">
  <thead>
    <tr>
      <th scope="col">Codes</th>
      <th scope="col">Sets</th>
      <th scope="col">Filename Example</th>
      <th scope="col">Comments</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>A, C, D, E, H, I, L, M, N, P, S, T, X</td>
      <td>Proceedings (syy-xnnn)</td>
      <td>P90-1001</td>
      <td>
        This is the first paper appearing in the first (or only) volume of the P90 proceedings; most proceedings have just one volume; in rare cases a proceedings volume has a supplement which should be numbered as a separate volume; in rare cases multiple proceedings volumes are bound into one (N00/A00) and these should be treated as separate volumes.
        Each conference proceedings may have up to 999 papers; conferences with more papers than this upper limit should consult the ACL Anthology Editor on how to split the proceedings into separate volumes.
        Proceedings chairs of conferences may choose at their discretion how they would like to partition volumes, although segmentations involving main/full papers, short papers, demonstrations and tutorial abstracts are most common.
      </td>
    </tr>
    <tr>
      <td>J, F, Q</td>
      <td>Journal (jyy-xnnn)</td>
      <td>J90-2001</td>
      <td>This is for the first paper in the second issue of J90; For combined issues, like 3/4, use the first number of the sequence.
        (E.g., if a journal year consists of combined issues 1/2 and 3/4, use J90-1 and J90-3 only).
        The 'F' prefix is for the Finite String, a newsletter (now obsolete) that used to be part of the Journal.
      </td>
    </tr>
    <tr>
      <td>W</td>
      <td>Workshops and Smaller Events (wyy-xxnn)</td>
      <td>W90-0201</td>
      <td>
        This is for the first paper in the second workshop in 1990; there is space for up to 100 workshops per year, and up to 99 papers per workshop.
        If a workshop exceeds 99 papers in a year, please consult with the ACL Anthology Editor.
        In this case, a separate set letter code may be established for the venue.
      </td>
    </tr>
  </tbody>
</table>

Historically, the file names fit within the 8.3 DOS naming constraint for maximum portability, as recommended by Adobe. PDF filenames are globally unique, to support subsetting (saving an ad hoc collection of papers to a single directory).
This format will likely be generalized in 2019 or 2020.

The canonical URLs for the Anthology are formed by appending the ACL ID to the Anthology URL.
For example,

> http://www.aclweb.org/anthology/P18-1023

will return the PDF of this paper.
Note that the canonical URL does *not* include the `.pdf` extension (though that URL will also resolve).

#### Paper numbering

A key notion in file naming is the paper number.
The general rule is that papers will be numbered consecutively within the bound volume in which they appear.
When a proceedings is divided into multiple volumes, paper number will begin from number '1', with each new volume.
When multiple proceedings are bound into a single volume (e.g., N18), they will be treated as multiple volumes (e.g., N18-1, N18-2, and so on).

Any front matter is given the paper number '0', padded to the ACL ID length (e.g., N18-1000).
Any back matter is given the number one more than the last paper in the volume.
Front and back matter that appears internally to a volume (e.g., in N18) will be counted just like an ordinary paper.

### Authoritative XML format

The Anthology site is generated from an authoritative XML file format containing information about volumes, paper titles, and authors.
This data is stored in [the official repository on Github](https://github.com/acl-org/acl-anthology/tree/master/data/xml).
Here is a fragment of a complete XML file ([P18.xml](https://github.com/acl-org/acl-anthology/blob/master/data/xml/P18.xml)), to give you the idea.
The full file contains much more information.

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<volume id="P18">
  <paper id="3000">
    <title>Proceedings of <fixed-case>ACL</fixed-case> 2018, Student Research Workshop</title>
    <editor><first>Vered</first><last>Shwartz</last></editor>
    <!-- ... -->
  </paper>
  <paper id="3001">
    <title>Towards Opinion Summarization of Customer Reviews</title>
    <author><first>Samuel</first><last>Pecar</last></author>
    <!-- ... -->
  </paper>
  <paper id="3002">
    <title>Sampling Informative Training Data for <fixed-case>RNN</fixed-case> Language Models</title>
    <author><first>Jared</first><last>Fernandez</last></author>
    <author><first>Doug</first><last>Downey</last></author>
    <!-- ... -->
  </paper>
  <paper id="3003">
    <title>Learning-based Composite Metrics for Improved Caption Evaluation</title>
    <author><first>Naeha</first><last>Sharif</last></author>
    <author><first>Lyndon</first><last>White</last></author>
    <author><first>Mohammed</first><last>Bennamoun</last></author>
    <author><first>Syed Afaq</first><last>Ali Shah</last></author>
    <!-- ... -->
  </paper>
  <!-- ...  -->
 </volume>
```

You need not necessarily concern yourself with this format, but it may be useful to know.

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
