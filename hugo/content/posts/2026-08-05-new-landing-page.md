---
title: An updated landing page
date: "2026-08-05"
description: >
    A modernized, compacter, mobile-friendly update to our home page
---

Today we are introducing a new landing page for the ACL Anthology.

[The old front page]({{<ref "/old" >}}) was organized around a "matrix view," which contained a complete history of events for a selected list of venues. However, it had a number of issues: it was unwieldy to navigate, didn't draw attention to current or recent events and hid others entirely, and was difficult to navigate on mobile devices. It was really showing its age.

<div class="row g-3 my-4">
  <figure class="col-md-6 mb-0">
    <img src="../../images/2026-08-05/front-page-old.png" alt="Old page" class="img-fluid border" />
    <figcaption class="small text-muted mt-2">The old matrix view presented complete histories of some venues with unwieldy horizontal scrolling.</figcaption>
  </figure>
  <figure class="col-md-6 mb-0">
    <img src="../../images/2026-08-05/front-page-new.png" alt="New page" class="img-fluid border" />
    <figcaption class="small text-muted mt-2">The new page highlights recent and flagship venues and allows direct venue searching and filtering by year.</figcaption>
  </figure>
</div>

At the same time, it had a recognizable appearance and provided direct access to many proceedings. Our redesign introduces the following changes:

- The appearance is distinctly new, but preserves the Anthology's unique look.
- It introduces a new venue grouping that first highlights venues with recent additions. This is followed by flagship venues, which includes ACL's main conferences and journals, and additional major venues determined by size and age criteria.[^1] Finally, there is an expandable list of the remaining workshop and non-workshop venues.
- We introduce a new filter that allows users to surface any of the 530 venues ingested in the Anthology. Users of the Anthology can also filter displayed years by decades. By default, the most recent years of each venue are shown, up to the available width.
- The content fits within the horizontal screen space, including on mobile devices.

This result is the outcome of [an extensive design discussion](https://github.com/acl-org/acl-anthology/pull/9158) and informal feedback from others in the NLP community. We will continue to maintain [the old version]({{<ref "/old" >}}) for those who prefer it.

The Anthology is run by volunteers from the NLP community. This includes the staff that maintains this infrastructure, and also the many people who contribute the volumes that constitute its extensive open resources. As always, we welcome [your feedback](https://aclanthology.org/faq/#feedback).

[^1]: A venue qualifies as "major" if it is a journal with 100+ papers; a conference with 1000+ unique authors; a workshop with 1000+ authors _and_ 1000+ papers; or if it has volumes dating back to 1985 or earlier. (The last criterion is to showcase the Anthology's historical reach.)
