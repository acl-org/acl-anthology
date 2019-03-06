---
Title: Information for Contributors
linktitle: For Contributors
subtitle: General information on ACL Anthology assignments for event (proceedings) chairs
date: "2015-10-13"
menu: footer
---

### File naming

Currently, we assign each paper in the ACL Anthology a unique 8-character
identifier, so that we can easily locate papers and reference them. The
identifier is assigned by the current ACL Anthology Editor and is in the form of
a letter, two digit year and a 4 digit paper ID (e.g., W11-3801). For large or
prominent events related to ACL or its sister organizations that recur on a
yearly basis, we use a separate lettered prefix, where all 4 digits of the paper
ID can be used (usually accommodating separate volumes or issue numbers in the
event or journal, each capable of referencing up to 999 papers).

For all other smaller events, we use the 'W' prefix. These events accommodate up
to 99 papers. If there are multiple volumes for a such smaller events, they are
assigned as two separate volumes (e.g., shared tasks, student papers).

The file names fit within the 8.3 DOS naming constraint for maximum portability,
as recommended by Adobe. PDF filenames are globally unique, to support
subsetting (saving an ad hoc collection of papers to a single directory). The
numeric fields within filenames are zero-padded to ensure filenames have fixed
width.

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
      <td>This is the first paper appearing in the first (or only) volume of the P90 proceedings; most proceedings have just one volume; in rare cases a proceedings volume has a supplement which should be numbered as a separate volume; in rare cases multiple proceedings volumes are bound into one (N00/A00) and these should be treated as separate volumes. Each conference proceedings may have up to 999 papers; conferences with more papers than this upper limit should consult the ACL Anthology Editor on how to split the proceedings into separate volumes. Proceedings chairs of conferences may choose at their discretion how they would like to partition volumes, although segmentations involving main/full papers, short papers, demonstrations and tutorial abstracts are most common.</td>
    </tr>
    <tr>
      <td>J, F, Q</td>
      <td>Journal (jyy-xnnn)</td>
      <td>J90-2001</td>
      <td>This is for the first paper in the second issue of J90; For combined issues, like 3/4, use the first number of the sequence. (E.g. if a journal year consists of combined issues 1/2 and 3/4, use J90-1 and J90-3 only). The 'F' prefix is for the Finite String, a newsletter (now obsolete) that used to be part of the Journal.</td>
    </tr>
    <tr>
      <td>W</td>
      <td>Workshops and Smaller Events (wyy-xxnn)</td>
      <td>W90-0201</td>
      <td>This is for the first paper in the second workshop in 1990; there is space for up to 100 workshops per year, and up to 99 papers per workshop. If a workshop exceeds over 99 papers in a year, please consult the ACL Anthology Editor (currently Matt Post) first. In this case, a separate set letter code may be established for the venue.</td>
    </tr>
  </tbody>
</table>

Workshop chairs should contact the ACL Anthology Editor to receive their
workshop number offset (the 'xx' portion of the ACL Anthology ID). If your
workshop is attached to a conference as a satellite event, please contact the
proceedings chair for the main conference to receive the offset ID, as it is
easiest to allocate offsets as a whole block. Conversely, if you are the
proceedings chair for a conference that has satellite workshops, please contact
the ACL Anthology Editor with the final list of titles of the workshops (make
certain the workshops will actually be run) so that the editor can allocate a
suitable block of offsets to the workshops.

### Paper numbers

A key notion in file naming is the paper number. The general rule is that papers
will be numbered consecutively within the bound volume in which they
appear. When a proceeding is divided into multiple volumes, paper number will
begin from number '1', with each new volume. When multiple proceedings are bound
into a single volume (e.g. N00), they will be treated as multiple volumes.

Any front matter is given the number '0'. Any back matter is given the number
one more than the last paper in the volume. Front and back matter that appears
internally to a volume (e.g. in N00) will be counted just like an ordinary
paper.

### Metadata

Anthology index pages are generated from an XML file containing information
about volumes, paper titles and authors. Each publication has an XML file,
stored alongside the scanned images. Proceedings chairs using the aclpub
publication package have a build target that will build a richer version of the
metadata below. Here is a fragment of `P/P03/P03.xml`, which satisfies these
minimal requirements, generated automatically from the conference CD-ROM:

```xml
<?xml version="1.0" encoding="UTF-8" ?>
 <volume id="P03">
   <paper id="1000">
        <title>Proceedings of the 41st Annual Meeting of the Association for Computational Linguistics</title>
   </paper>

   <paper id="1001">
        <title>Offline Strategies for Online Question Answering: Answering Questions Before They Are Asked</title>
        <author>Michael Fleischman</author>
        <author>Eduard Hovy</author>
        <author>Abdessamad Echihabi</author>
   </paper>

   <paper id="1002">
        <title>Using Predicate-Argument Structures for Information Extraction</title>
        <author>Mihai Surdeanu</author>
        <author>Sanda Harabagiu</author>
        <author>John Williams</author>
        <author>Paul Aarseth</author>
   </paper>

   <paper id="1003">
        <title>A Noisy-Channel Approach to Question Answering</title>
        <author>Abdessamad Echihabi</author>
        <author>Daniel Marcu</author>
   </paper>

   ...

 </volume>
```

A more comprehensive example can be found at
[http://www.aclweb.org/anthology/P/P15/P15.xml](http://www.aclweb.org/anthology/P/P15/P15.xml)
(metadata for ACL 2015).

These metadata files are publicly visible (but not linked) from the current Anthology.

Other details:

1.  When it's due: Prepare volumes for the Anthology with sufficient timeframe
    for us to ingest it and generate a preview site for you to check. Usually
    edits are necessary for LaTeX escapes that don't transform well to XHTML
    (diacritics in names, protected capitalization in paper titles). Provide the
    zip file's downloadable URL around **two weeks** before the deadline you
    need the proceedings online.

    The ingestion process is manual and requires time to execute and proofcheck,
    and as such, it's very helpful to ensure that your proceedings are in good
    order before sending the link; redoing the ingestion costs approximately the
    same time as the original ingestion and thus incurs significant additional
    expense for the volunteer staff.

2.  URLs for the Anthology (for START as well as the Anthology XML) look like:

        http://www.aclweb.org/anthology/W11-38xx

    and not

        http://www.aclweb.org/anthology/W/W11/W11-38xx.pdf

    (note, no `.pdf` and no intermediate path) where `xx` is the paper ID. `00`
    is used for the frontmatter, `01` for the first paper, etc., and any author
    index is listed as the final paper. In START you may see (and need to
    provide) this coded using C-like format strings:

        http://www.aclweb.org/anthology/W11-38%02d

3.  The data in the ACL Anthology is (almost) completely derived from the XML
    form of the paper and volume metadata that is used to generate it. If you
    can create this XML representation for your event, it will be sufficient
    information for us to generate the Anthology representation (Web pages) for
    your event. For events using START version 2 (via softconf.com), which is
    the default publication / event manager software for ACL, this will be easy,
    as we have transformation scripts to ingest directly from the
    `proceedings.tgz` file that can be one-click generated from START. For other
    events, you will need to provide this data on your own (see the Metadata
    section above).

4.  For copyright transfers, you can use the default forms at:

    + `http://wing.comp.nus.edu.sg/~antho/acl-copyright-form-rev2011.pdf`
    + `http://wing.comp.nus.edu.sg/~antho/acl-copyright-form-rev2011.doc`

    Ask authors to sign the form, scan a B/W copy at 150 to 200 DPI for you as a
    `.pdf` (or `.jpg` or `.png` if otherwise not possible). Name the forms using
    the ACL Anthology identifiers, and send me a separate `.zip` or `.tgz`
    archive as you would for the proceedings of your event (e.g., a file in the
    archive might be `copyright-transfers/P11-1001.pdf`).

    Note that if you are using the START system (softconf.com), there is a
    digital form of this copyright transfer form, so you may not have to ask the
    authors to print, sign and submit to you. You may be able to simply download
    the `.zip` or `.tgz` version of the archived forms and submit them to
    me. Please note this when submitting.

    For both current and legacy events, it is good practice for the organizers
    to attempt to obtain copyright transfers for their materials, but we will
    ingest materials even if no copyright transfers are on file.

5.  If you need to assign ISBN numbers, please provide the exact titles of each
    volume to be assigned an ISBN and forward this information to Priscilla
    Rasmussen, ACL Business Manager.

6.  If there are supplemental attachments, software or datasets, also please let
    me know about them when they are finalized so that we can have them
    published in the Anthology in a timely manner. You'll need to provide a
    zipfile or other filetype (of a three letter extension only) of each
    supplement, where the files are named by their paper's Anthology ID (e.g.,
    `W11-1001.Dataset.zip`).

    Current types supported by the Anthology are:

    + Attachment (this is for generic attachments; best to be specific and avoid
      using this when possible)
    + Dataset
    + Note
    + Poster
    + Presentation
    + Software

    Videos are also accepted but only as valid hyperlinks.

    Any attachment is limited to 30 MB or a valid hyperlink (which should be
    maintained in perpetuity, but reasonably maintained for at least 5
    years). Hyperlinks may lead either to the actual attachment or to a valid
    containing "home page" for the resource.

    We prefer actual attachments over hyperlinks as we can serve them from the
    Anthology directly, but understand that some materials cannot fit within
    this size. Attachments do not need to be author-anonymized (although during
    the review process, program chairs may ask for this -- authors should try to
    include provenance information with their attachments).

7.  If you get requests from authors needing to post errata or revised versions
    of the papers, or supplemental attachments after the publication of the
    proceedings, please ask them to submit revisions to the current ACL
    Anthology editor directly (see [Corrections]({{< relref "corrections.md"
    >}})).

    If you wish to incorporate edits from your pipeline, we will also accept
    revisions from proceedings chairs of workshops (to replace the original
    version, or to create a new version) if the ACL footer (i.e. "Proceedings of
    ..." on header page) appears in the PDF with the correct page numbers, only
    before the publication date. After the publication date, the full volume
    cannot be replaced or revised.

8.  By default, the publication of papers associated with a current event in the
    Anthology will be on the first day of the event (inclusive of workshops or
    tutorials). If you prefer to have it published on a different date, please
    inform us.

9.  Please list the ACL SIGs endorsing or sponsoring each event, and for each
    event, where not completely clear, give a short, acronym form of the event
    name, for indexing (e.g., "ACL", "NAACL", "SocialNLP"). Acronym forms should
    be recognizable and consistent through consecutive (multi-)annual
    events. Please check the [beta
    Anthology](http://aclanthology.info/catalog?utf8=%E2%9C%93&search_field=all_fields&q=#)
    (see venue facet) to check whether the venue acronym has been used
    before). Please provide this information.

10. For ingestion from events managed by Easy Chair, Nils Blomqvist has created
    an [easy2acl](https://github.com/nblomqvist/easy2acl) script, which should
    make the transformation to the aclpub format easier.

11. **Q:** What data from START (softconf.com) does the Anthology ingestion process actually use?

    **A:** The Anthology software uses a transformation script to revise the
    distributed `.bib` files into the appropriate XML metadata used by the
    Anthology. We typically run this on the full volume `.bib` file, provided at
    the `cdrom/` directory that is distributed by START. We primarily use three
    sources of information that is just renamed from those sources:

    + the bib files under `cdrom/bib`
    + the pdf files under `cdrom/pdf`
    + the whole volume `bib/pdf`
    + files under `cdrom`

    We also use the cdrom/attachments when they are provided (optional).

12. Other general information on ACL Anthology assignment is included on the
    following page (although outdated). Please read
    it. http://www.aclweb.org/anthology/importing.html

