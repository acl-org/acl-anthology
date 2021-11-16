---
Title: Information for Submitters
linktitle: Submitting
subtitle: General information on submitting proceedings to the ACL Anthology (for event chairs)
date: "2020-10-30"
---

This page contains general information about submitting the proceedings of a conference to the ACL Anthology.
(For information about the complete conference management process, particularly for ACL conference publications chairs, please refer to [the official documentation](https://acl-org.github.io/ACLPUB/).)
It is intended for publication chairs of main conferences and standalone events, who have the responsibility of delivering the proceedings for all main conference and workshop volumes to the Anthology director.
Chairs of workshops attached to a larger conference should also read this page, but should work through their main conference publication chair instead of directly with the Anthology.

### Overview of the Submission Process

Please note the following important dates.

<table class="table table-bordered">
  <thead class="thead-dark">
    <tr>
      <th scope="col">Deadline</th>
      <th scope="col">Step</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Before paper submission deadline</td>
      <td><a href="#register-your-meeting"">Register your meeting</a></td>
    </tr>
    <tr>
      <td>Before paper submission deadline</td>
      <td><a href="#isbn-numbers">Request ISBNs</a></td>
    </tr>
    <tr>
      <td>2 weeks before publication</td>
      <td><a href="#submit-your-data">Submit your data</a></td>
    </tr>
    <tr>
      <td>2 weeks before publication</td>
      <td><a href="#copyright">Submit copyright transfer forms</a></td>
    </tr>
    <tr>
      <td>After publication</td>
      <td><a href="#errata-and-corrections">Making corrections</a></td>
    </tr>
  </tbody>
</table>




### Register your meeting

If you are a conference publications chair, you must register your intention to submit your proceedings.
This step requires you to send (a) the complete list of volumes that will be published in the Anthology (main conference volumes and workshops) and (b) the desired publication date.
This information should be assembled in a spreadsheet and then commmunicated to [the Anthology Director](mailto:anthology@aclweb.org) in a single email.
Please do this as early as possible, ideally well before the submission deadline.
An template for this spreadsheet [can be found here](https://docs.google.com/spreadsheets/d/13F1XhnT4PsiN-ZXcpv6QUp5A2qlr6-W9MoDgCkBOw9w/edit#gid=0).
As noted above, if you are the chair of a workshop that is colocated with a larger event, please work with your main conference publication chair instead of directly with the Anthology.

The following information in the spreadsheet is especially important:

-  **Venue identifiers**. Each venue (conference or workshop) has a venue identifier.
   Its basic form is the conference acronym, such as ACL, NAACL, JEP/TALN/RECITAL, and so on.
   A [slugified](https://en.wikipedia.org/wiki/Clean_URL#Slug) version of this acronym, containing only numerals and lowercase ASCII letters, is used in the URL for the venue's page on the Anthology (e.g., [ACL → acl](https://aclanthology.org/venues/acl), [JEP/TALN/RECITAL → jeptalnrecital](https://aclanthology.org/venues/jeptalnrecital)), and also forms a component of the [Anthology ID]({{< relref "ids.md" >}}).
   For existing venues, be sure to look up [the venue's existing identifier](https://aclanthology.org/venues/).
   New venues must have their venue identifier confirmed by the Anthology director.
   Note: a common mistake is to include the year in the venue identifier, e.g., ACL2020 (perhaps in part because Softconf often uses this).
   This confuses a *meeting* of a venue with the venue itself.
   The identifier should not have the year or meeting number in it.
-  **Venue name**. Each venue has a name.
   These names are attached to the venue identifier and stored in [our database](https://github.com/acl-org/acl-anthology/blob/master/data/yaml/venues.yaml).
   If your venue is new, please enter the venue name.
   Note: similar to the caveat about about the venue identifier, this is the name of the venue, not a particular meeting of the venue.
   When submitting a new venue to the Anthology, please make sure *not* to put the year or meeting number in the venue name.
-  **Volume titles**. These are the titles of the volumes that will be published, e.g., *Proceedings of the...*.
   We recommend you choose a name consistent with your prior years' volumes.
   The full titles should not contain abbreviations, except parenthetically.
   For example, "Proceedings of EMNLP 2019" is not a good title, but "Proceedings of the 2019 Meeting of the Conference on Empirical Methods in Natural Language Processing (EMNLP)" is a great one.
   If you have sub-volumes (e.g., long papers, short papers, demonstrations, tutorial abstracts), we suggest you append them after the full volume name.
   For example, "Proceedings of the 2019 Meeting of the Conference on Empirical Methods in Natural Language Processing (EMNLP): Tutorial Abstracts".
   You should also seek consistency with the names of your volumes from prior years.
   You may find [this naming guide](https://docs.google.com/document/d/1-4I8w-ckyy3oF2XMbkjAaq14EOyWSoSUW0dpCTtprm8/edit?usp=sharing) helpful.

By default, the publication of papers associated with an event in the Anthology will be on the first day of the event (inclusive of workshops or tutorials).
If you prefer to have it published on a different date, please inform us when you register.

### Submit your data

After your conference management software has collected all the camera-ready papers and associated attachments, you will arrange all the volumes of your proceedings into ACLPUB format, as described in the [ACLPUB → Anthology documentation](https://acl-org.github.io/ACLPUB/anthology.html).
The end result is a `data` directory containing ACLPUB proceedings, one for each conference (again, see [the ACLPUB -> Anthology instructions](https://acl-org.github.io/ACLPUB/anthology.html)).
A link to this directory (preferably via a file sharing service, such as Dropbox or Google Drive) should be sent to the Anthology Director **two weeks prior to your desired publication date** (which was negotiated when you first contacted us).

The remaining steps are handled by Anthology staff and use [Anthology tools](https://github.com/acl-org/acl-anthology/tree/master/bin/):

- We ingest that data by running additional scripts that convert it into our authoritative format, apply title-case protection, and disambiguate author names.
- This becomes a pull request on [our Github repository](https://github.com/acl-org/acl-anthology/).
- Once approved and merged into the `master` branch, the site will be automatically rebuilt (which happens twice a day) and made live.

### Copyright

If you are using the START system, this process is handled as part of the camera-ready submission process.

Otherwise, for copyright transfers, please use the form at:

+ https://github.com/acl-org/ACLPUB/blob/master/doc/authors/ACL-copyright-form.pdf

Forms should be signed by authors and saved using the ACL Anthology identifiers as names.
Please place these into a folder (e.g., `copyright-transfers/P11-1001.pdf`) and then deliver them in bulk to the Anthology Editor when submitting the proceedings.

For both current and legacy events, it is good practice for the organizers to attempt to obtain copyright transfers for their materials, but we will ingest materials even if no copyright transfers are on file.

### ISBN Numbers

If you need to assign ISBN numbers, please provide the exact titles of each volume to be assigned an ISBN and forward this information to Priscilla Rasmussen, ACL Business Manager.

### Errata and Corrections

If you get requests from authors needing to post errata or revised versions of the papers, or supplemental attachments after the publication of the proceedings, please refer them to [our documentation on the matter]({{< relref "corrections.md" >}}).
Note that after the publication date, corrections can only be applied to individual papers; the full proceedings volumes will not be replaced or revised.
