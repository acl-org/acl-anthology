---
title: New workflow for processing metadata
date: "2024-12-27"
description: >
    A simplified workflow for processing metadata corrections should make it easier for authors to submit corrections and for Anthology staff and volunteers to process them expeditiously.
---
After proceedings are published, authors often discover errors in the paper metadata, including misspelled author names, missing or misordered authors, and mistakes in titles or abstracts. Until today, corrections to this data involved a lot of manual effort on both the part of authors (who had to locate the form and fill it out) and Anthology staff (who had to manually process and interpret these forms and make the corrections). The result was hundreds of issues accumulating on the [Anthology Github repository](https://github.com/acl-org/acl-anthology/issues?q=is%3Aissue+is%3Aopen+label%3Acorrection+label%3Ametadata), and a delay of weeks or sometimes even months to process them.

<img src="/images/2024-12-27/many-requests.png" alt="Accumulating issues" style="width:50%;" />

We are therefore happy to announce a new simplified workflow that we hope will reduce effort and processing time. This workflow introduces a yellow "Fix metadata" button on each paper page in the Anthology. Clicking on this button will display a dialog allowing for easy manipulation of the title, author list, and abstract. Upon submission, this dialog will lead the submitter to the creation of a structured Github issue for the correction. The user needs only to submit the issue, and leave the rest to Anthology staff.

<img src="/images/2024-12-27/dialog.png" alt="Metadata correction dialog" style="width:50%;" />

For the curious, from that point, we make use of further Github automations to make the process as easy as possible. A Github workflow annotates the issue with an image of the paper and a link to its paper page, allowing for easy visual verification of the corrections. We then run a script that can automatically create a consolidated pull request from all approved correction requests.

We hope that this simplified process will make the submission process easier and more intuitive for authors who submit corrections, and also that it will enable us to process them much more frequently than the monthly process we've been using up till this point.

We are excited to see how this new process will work in practice, and we welcome feedback from the community on how we can further improve it.
