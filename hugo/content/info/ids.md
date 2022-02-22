---
Title: Anthology Identifiers
linktitle: IDs
subtitle: Information on how the Anthology assigns identifiers
date: "2022-02-12"
---

Every item in the Anthology is assigned an identifier, called the "Anthology ID".
These identifiers are used together with the Anthology domain name to form a canonical URL for each of these items, for easy location and reference.

## Modern identifier format

Everything /ingested/ into the Anthology after 2020 (including volumes from prior years) has been assigned an identifier of the form `YEAR.VENUE-VOLUME.NUMBER`, where:

- YEAR is the 4-digit year (e.g., "2020")
- VENUE is a lowercased, alphanumeric ([a-z0-9]+) identifier (e.g., "acl" or "repl4nlp")
- VOLUME is a volume name (e.g., "1" or "long")
- NUMBER is a paper number

An example is `2020.acl-1.12` for the twelth paper in the first volume.
Its canonical page can be accessed at <https://aclanthology.org/2020.acl-main.12>.

Venue identifiers are assigned by the Anthology Directory in consultation with submitters.
Typically, an acronym will be selected ("lrec" for [LREC](http://lrec.org), "acl" for [ACL](http://www.aclweb.org/), etc.).

In addition to paper identifiers, there are a number of other useful concepts.

Volumes themselves also have identifiers.
A volume identifier is formed by removing the paper number and the delimiter, e.g., `2020.acl-main`.
Volumes can be accessed via the same scheme for canonical pages used for papers, e.g., <https://aclanthology.org/2020.acl-main>.

We also infer the presence of events.
Each yearly entry for a venue creates an "events" page.
This can be accessed using the year and venue code.
For example, the ACL 2020 event is available at <https://aclanthology.org/events/acl-2020>.
This page will include all volumes published under ACL, as well as any colocated events, such as workshops.

## Paper numbering

A key notion in file naming is the paper number.
The general rule is that papers will be numbered consecutively within the bound volume in which they appear.
When a proceedings is divided into multiple volumes, paper numbers will begin from number '1', with each new volume.

By convention, any front matter is given the paper number '0' (e.g., 2020.acl-srw.0, 2020.emnlp-1.0).
Any back matter is assigned the last paper number in the volume.
Front and back matter that appears internally to a volume will be treated just like an ordinary paper.

## Canonical URLs

The canonical URLs for the Anthology are formed by appending the ACL ID to the Anthology URL.
For example,

> https://aclanthology.org/P18-1023

will return the landing page for this paper.
The PDF can be accessed directly by accessing

> https://aclanthology.org/P18-1023.pdf

This works for other provided files such as BibTeX (.bib) and MODS XML (.xml).


## Old format (for materials ingested prior to 2020)

Anthology IDs from volumes ingested prior to 2020 had a unique 8-character identifier, comprising a letter, a two digit year, and a 4 digit volume and paper ID (e.g., P18-1024).
The paper ID decomposes into a volume ID and a paper ID.
For large or prominent events related to ACL or its sister organizations that recur on a yearly basis, we used a separate lettered prefix (e.g., ACL, which is "P").
With only two exceptions (see the table below), in such cases, the volume ID is 1 digit and the paper ID is 3 digits.
For all other events, we used the 'W' prefix.
Here, the volume ID is 2 digits, and the paper ID 2 digits.
These events therefore accommodated up to 99 papers.
If there are more than 99 papers, they need to be broken out into two separate volume IDs.
Both paper and volume IDs are zero-padded to ensure that filenames have a fixed width.

<table class="table table-bordered">
  <thead class="thead-dark">
    <tr>
      <th scope="col">Codes</th>
      <th scope="col">Sets</th>
      <th scope="col">Filename Example</th>
      <th scope="col">Comments</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>A, C*, D*, E, H, I, L, M, N, P, S, T, X</td>
      <td>Proceedings (syy-xnnn)</td>
      <td>P90-1001</td>
      <td>
        <p>This is the first paper appearing in the first (or only) volume of the P90 proceedings; most proceedings have just one volume; in rare cases a proceedings volume has a supplement which should be numbered as a separate volume; in rare cases multiple proceedings volumes are bound into one (N00/A00) and these should be treated as separate volumes.
        Each conference proceedings may have up to 999 papers; conferences with more papers than this upper limit should consult the ACL Anthology Editor on how to split the proceedings into separate volumes.
        Proceedings chairs of conferences may choose at their discretion how they would like to partition volumes, although segmentations involving main/full papers, short papers, demonstrations and tutorial abstracts are most common.</p>

        <p>(*) There are two exceptions: C69, and D19-50 through D19-66.
        All of these are treated as workshop identifiers, with two characters reserved for the volume identifier.</p>
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
      <td>W, C69, D19-50--D19-66</td>
      <td>Workshops and Smaller Events (wyy-xxnn)</td>
      <td>W90-0201</td>
      <td>
        <p>This is for the first paper in the second workshop in 1990; there is space for up to 100 workshops per year, and up to 99 papers per workshop.
        If a workshop exceeds 99 papers in a year, please consult with the ACL Anthology Editor.
        In this case, a separate set letter code may be established for the venue.</p>

        <p>D19-50--D19-66 were used as workshop identifiers because 2019 would otherwise have had more than 100 workshops, which was impossible in that numbering scheme.</p>
      </td>
    </tr>
  </tbody>
</table>

Historically, the file names fit within the 8.3 DOS naming constraint for maximum portability, as recommended by Adobe.
PDF filenames are globally unique, to support subsetting (saving an ad hoc collection of papers to a single directory).

The old format presented a number of problems.

* It had only four digits to encode the volume and paper number.
  Some workshops had more than 100 papers and had to be unnaturally split into multiple volumes, in a cumbersome fashion (for example, [WMT 2019](https://aclanthology.org/events/wmt-2019/)).
  The modern format has no real restriction on the number of papers.

* It had a fixed number of identifiers for venues (for example, "P" was for "ACL").
  All other venues shared the "W" identifier.
  The modern format permits a unique venue code for every venue.
