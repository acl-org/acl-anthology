---
Title: New workflow for processing metadata
date: "2024-12-27"
Description: >
    A simplified workflow for processing metadata corrections should make it easier for authors to submit corrections and for Anthology staff and volunteers to process them expeditionsly.
---
After proceedings are published, authors often discover errors to the paper metadata, including misspelled author names, missing or miss-ordered authors, and titles or abstracts that were subtly modified during the publication process. Until today, corrections to these papers involved a lot of manual effort on both the part of authors (who had to search out a form and fill it out) and Anthology staff (who had to manually process and interpret these forms and make the corrections). The result was hundreds of issues accumulating on the [Anthology Github repository](https://github.com/acl-org/acl-anthology/issues?q=is%3Aissue+is%3Aopen+label%3Acorrection+label%3Ametadata), and a delay of weeks or even months to manage them.

![target](/images/2024-12-27/many-requests.png)

We are therefore happy to announce a new simplified workflow that we hope will address these problems. The new workflow introduces a yellow "Fix metadata" button on each paper page in the Anthology. Clicking on this button will display a dialog allowing for easy manipulation of the title, author list, and abstract. Upon submission, this dialog will lead the submitter to the creation of a structured Github issue for the correction. The user needs only to submit the issue, and leave the rest to Anthology staff.

For the curious, from that point, we make use of further Github automations to make the process as easy as possible. A Github workflow annotates the issue with an image of the paper and a link to its paper page, allowing for easy visual verification of the corrections. We then run a script that can process all approved requests, automatically creating a pull request with all approved issues.

We hope that this simplified process will make the submission process easier for authors who notice corrections, and that it will also enable us to process them on a weekly basis, rather than the monthly process we've been using up until now.

We are excited to see how this new process will work in practice, and we welcome feedback from the community on how we can further improve it.
