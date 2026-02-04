---
Title: Author pages
linktitle: Author pages
subtitle: How to keep your author page up-to-date
date: "2026-01-28"
---
Every author appearing on a paper in the Anthology is given an author page. The ACL Anthology distinguishes between _verified_ and _unverified_ authors.

A verified author has an ORCID icon <i class="fab fa-orcid text-verified"></i> next to the author's name (or sometimes a green question mark <i class="fas fa-question-circle text-verified"></i>). If your author page is verified:
- Anthology papers linked to your ORCID iD will appear on your page.
- Papers by someone with the same name as you, but linked to a different ORCID iD, will not appear on your page.
- Initially, papers by someone with the same name as you, but not linked to an ORCID iD, will still appear on your page. To fix this, please see [How to remove papers from your author page](#how-to-remove-papers-from-your-author-page).

An unverified author page has `/unverified/` appended to its URL, and a gray question mark <i class="fas fa-question-circle text-secondary"></i> next to the author's name. If your author page is unverified:
- Papers that list you as an author with a different spelling will appear on a different author page. For more information, please see [How to add papers to your author page](#how-to-add-papers-to-your-author-page).
- Papers by someone with the same name as you (if they are also not verified) will appear on your author page. For more information, please see [How to remove papers from your author page](#how-to-remove-papers-from-your-author-page).

For more details on how verification works, please see [How the ACL Anthology verifies authors]({{< ref "/info/verification">}}). To learn how to get your author page verified, please continue to [How to get your author page verified](#how-to-get-your-author-page-verified).

### How to get your author page verified

1. Obtain an ORCID iD and update your ORCID profile:
   - Visit [the ORCID registration form](https://orcid.org/register) if you need to create one, or navigate to your existing ORCID profile page and click the edit button.
   - Add name variants: Set your given and family names, your published name, and any name variants you have published under (e.g., with or without middle initials, former names, etc.). It is especially important to make sure you have at least one Latin-script variant of your name. ([This profile](https://orcid.org/0000-0002-1831-3457) is a good example.)
   - Make sure your name is visible to everyone.
   - Add educational history and affiliations: When we manually disambiguate an author, we may need to know the institution from which you received (or expect to receive) your highest degree, as part of our [human-focused person ID system]({{< ref "/info/names" >}}).
   - Less importantly, it can be helpful to the disambiguation process if you make the effort to add a few representative publications.

   For more information about ORCID iDs and how the Anthology uses them, please [ORCID iDs in the ACL Anthology]({{< ref "/info/orcid">}}).

2. Link your profiles on conference management systems to your ORCID iD:
   - **OpenReview:** Visit the ["Edit Profile" page](https://openreview.net/profile/edit). (If necessary, enter your username and password and click on "Login to OpenReview.") Click on the "Personal Links" section. Enter your ORCID in the "ORCID URL" field, and click on the "Save Profile Changes" button.
   - **Softconf/START:** Visit the ["Update Profile" page](https://www.softconf.com/naacl2021/super/scmd.cgi?ucmd=updateProfile). (If necessary, click on "To Login Page", enter your username and password, click on the "ENTER" button, and click on ["Update Profile"](https://www.softconf.com/naacl2021/super/scmd.cgi?ucmd=updateProfile) again.) Scroll down to the "Additional Information for Authors and Reviewers" section. Enter your ORCID in the "ORCID" field, and click on the "SUBMIT DATA" button.

   In each of these systems, the name that you enter is the one that gets used in your papers' metadata. Please make sure that this name matches the name that you use in your papers' PDF files, and that this name matches one of the ORCID variants, ideally your published name.

3. Let the Anthology know about your ORCID iD:
   - Find your ACL Anthology author page (by using the search bar, or by finding one of your papers and clicking on your name).
   - Look at the icon next to your name at the top of the page. If it is a green ORCID icon <i class="fab fa-orcid text-verified"></i>, then your author page is verified already!
   - Otherwise, click on the "Fix author" button at the bottom of the links on the right-hand side of the page.
   - Fill out at least the required fields, and check the "Verification" checkbox.
   - Click on the "Create" button, and wait for the issue to be reviewed by Anthology staff.

### How to remove papers from your author page

When your author page is first verified, any papers published under your name will appear on your page. However, if another author has the same name as you, their papers may also appear on your page.

To fix this, please verify your author page, if you haven't already, using the [instructions above](#how-to-get-your-author-page-verified).

Then, please file a split/disambiguate request, as follows:
- Find your ACL Anthology author page (by using the search bar, or by finding one of your papers and clicking on your name).
- Click on the "Fix author" button at the bottom of the links on the right-hand side of the page.
- Fill out at least the required fields, check the "Split/disambiguate" checkbox, and list which papers should be kept or which papers should be removed in the "Supporting Information" field.
- Click on the "Create" button, and wait for the issue to be reviewed by Anthology staff.

### How to add papers to your author page

After your author page is verified, any papers published under your name, if they are not linked to an ORCID iD, may appear on a different author page.

To fix this, please first of all check that the names on the other papers are correct. We treat the information on the PDF as authoritative; this means that the metadata should match exactly what is printed on the PDF. Please review your papers and [follow the steps here]({{< ref "info/corrections/#metadata-corrections" >}}) to correct any discrepancies. Sometimes, this will resolve the problem.

Second, please verify your author page, if you haven't already, using the [instructions above](#how-to-get-your-author-page-verified).

If the names are correct and your author page is verified, then please file a merge request, as follows:
- Find your ACL Anthology author page (by using the search bar, or by finding one of your papers and clicking on your name).
- Click on the "Fix author" button at the bottom of the links on the right-hand side of the page.
- Fill out at least the required fields, check the "Merge profiles" checkbox, and list the papers to be added or pages to be merged in the "Supporting Information" field.
- Click on the "Create" button, and wait for the issue to be reviewed by Anthology staff.
