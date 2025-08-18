1. [ ] In the Github sidebar, add the PR to the current milestone
1. [ ] In the Github sidebar, add the PR to the "Anthology Work Items" project
1. [ ] In the Github sidebar, under "Development", link to the corresponding ingestion issue (if applicable)
1. [ ] Make sure the branch is merged with the latest `master` branch
1. [ ] Ensure that there are editors listed in the `<meta>` block
1. [ ] For workshops, add a `<venue>ws</venue>` tag to its meta block
1. [ ] For workshops, add a backlink from the main event's `<event>` block
1. [ ] Add events to their relevant SIGs
1. [ ] Look at the venue listing for prior years, and ensure that the new volume titles are consistent. You can do this by clicking on the venue name from a paper page, which will take you to the vendor listing.
1. [ ] Navigate to the event page preview (e.g., https://preview.aclanthology.org/icnlsp-ingestion/events/icnlsp-2021/), and page through, to see if there are any glaring mistakes
1. [ ] Skim through the complete listing, looking for mis-parsed author names.
1. [ ] Download the frontmatter and verify that the table of contents matches at least three randomly-selected papers
1. [ ] Download 3–5 PDFs (including the first and last one) and make sure they are correct (title, authors, page numbers).

After the PR is closed, for all events:
- [ ] Archive the ingestion materials in format `YYYY-MM-DD-{event}`

After the PR is closed, for ACL events:
- [ ] Generate the DOIs for all volumes (`generate_crossref_doi_metadata.py`)
- [ ] Upload to [Crossref](https://doi.crossref.org/servlet/home)
- [ ] Add the DOIs to the XML in a separate PR (`add_dois.py`)
