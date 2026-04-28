- [ ] In the Github sidebar, add the PR to the current milestone
- [ ] In the Github sidebar, add the PR to the "Anthology Work Items" project
- [ ] In the Github sidebar, under "Development", link to the corresponding ingestion issue (if applicable)
- [ ] Make sure the branch is merged with the latest `master` branch
- [ ] Ensure that there are editors listed in the `<meta>` block
- [ ] For workshops, add a `<venue>ws</venue>` tag to its meta block
- [ ] For workshops, add a backlink from the main event's `<event>` block
- [ ] Add events to their relevant SIGs

Navigate to the preview site (it will be generated after the first build) and check the following:
   - [ ] Click on the venue name to bring up the venue listing to verify that volume titles are consistent
   - [ ] Skim through the complete listing, looking for mis-parsed author names
   - [ ] Download the frontmatter and verify that the table of contents matches at least three randomly-selected papers
   - [ ] Download 3–5 PDFs (including the first and last one) and make sure they are correct (title, authors, page numbers)

After the PR is closed, for all events:
- [ ] Archive the ingestion materials in format `YYYY-MM-DD-{event}`

Merging PRs for ACL events will trigger a new issue for adding DOIs:
- [ ] This is an ACL event
