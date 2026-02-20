---
title: New Author System in the ACL Anthology
date: "2026-01-26"
description: >
    Introducing ORCID-centered author pages with explicit verification status
---

An important task of the ACL Anthology is to correctly match papers to authors. When a new volume is ingested, the Anthology receives author information as textual metadata along with each PDF. When the site is built, we assemble author pages from all papers that share the same name.

This may sound straightforward, but in practice it’s difficult, for two reasons: the same person may publish under multiple name variants (diacritics, middle initials, name changes), and many names are shared by multiple people. In practice, we resolve both of these issues using a manual process: one mechanism to group papers for a single author with multiple names, and another to explicitly assign a paper to a specific author using [a person ID]({{< ref "/info/names" >}}). This process is time-consuming and labor-intensive.

The following histogram shows the prevalence of known ambiguous names in the Anthology. For example, there are 121 names shared by two people. Most names are unique, but the number of ambiguous names is still significant. In the past few years, especially, the number of ambiguous names has increased sharply, which increases the amount of human effort in resolving these ambiguities.

<table class="table table-sm">
    <thead>
        <tr>
            <th style="text-align:center"># people</th>
            <th style="text-align:right">count</th>
            <th>examples</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="text-align:center">1</td>
            <td style="text-align:right">122,122</td>
            <td>— (unique entries)</td>
        </tr>
        <tr>
            <td style="text-align:center">2</td>
            <td style="text-align:right">121</td>
            <td>Ai, Wei; Amini, Massih R</td>
        </tr>
        <tr>
            <td style="text-align:center">3</td>
            <td style="text-align:right">297</td>
            <td>Agarwal, Shubham; Bartelt, Christian</td>
        </tr>
        <tr>
            <td style="text-align:center">4</td>
            <td style="text-align:right">63</td>
            <td>Zhang, Dongyu; Zhang, Han</td>
        </tr>
        <tr>
            <td style="text-align:center">5</td>
            <td style="text-align:right">22</td>
            <td>Chen, Wei; Li, Yang</td>
        </tr>
        <tr>
            <td style="text-align:center">6</td>
            <td style="text-align:right">9</td>
            <td>Li, Lei; Wang, Di</td>
        </tr>
        <tr>
            <td style="text-align:center">7</td>
            <td style="text-align:right">11</td>
            <td>Chen, Chen; Li, Chen</td>
        </tr>
        <tr>
            <td style="text-align:center">8</td>
            <td style="text-align:right">2</td>
            <td>Liu, Wei; Zhang, Yu</td>
        </tr>
        <tr>
            <td style="text-align:center">9</td>
            <td style="text-align:right">2</td>
            <td>Li, Bo; Wang, Hao</td>
        </tr>
        <tr>
            <td style="text-align:center">10</td>
            <td style="text-align:right">2</td>
            <td>Chen, Hao; Li, Xiang</td>
        </tr>
        <tr>
            <td style="text-align:center">14</td>
            <td style="text-align:right">1</td>
            <td>Zhang, Li (only known example)</td>
        </tr>
        <tr>
            <td style="text-align:center">25</td>
            <td style="text-align:right">1</td>
            <td>Liu, Yang (only known example)</td>
        </tr>
    </tbody>
</table>

To address this, we are introducing a new author system centered on [ORCID iDs](https://orcid.org), a widely used persistent identifier for researchers. Papers with ORCID iDs will be automatically linked together and used to create "verified" author pages. Authors without ORCID iDs will still have author pages, but these will be marked as "unverified" to indicate that the papers listed may not all belong to the same person.

The best way to ensure your papers are correctly attributed is to **create an ORCID iD and add it everywhere you submit papers**: in particular, to your OpenReview profile and to conference submission systems such as Softconf. If you notice papers that don’t belong together, you can use the “Fix author” link on the author page to report it.

For more information, you can read about [how we verify authors]({{< ref "/info/verification" >}}) and [how we use ORCID iDs]({{< ref "/info/orcid" >}}).
