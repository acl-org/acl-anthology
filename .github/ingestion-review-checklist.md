Administrative checklist:
- [ ] Make sure the branch is merged with the latest `master` branch
- [ ] Ensure that there are editors listed in the `<meta>` block
- [ ] In the Github sidebar, add the PR to the current milestone
- [ ] In the Github sidebar, under "Development", link to the corresponding ingestion issue (if applicable)
- [ ] Ensure ORCID iDs are present for (most) authors
- [ ] Ensure OpenReview IDs are present for all authors if it is an OpenReview venue
- [ ] For workshops, add a `<venue>ws</venue>` tag to its meta block
- [ ] For workshops, add a backlink from the main event's `<event>` block
- [ ] Add events to their relevant SIGs

Navigate to the preview site and check the following:
   - [ ] Verify that volume titles are consistent with past years (click on the venue link to see them)
   - [ ] Skim through the complete listing, looking for mis-parsed author names
   - [ ] Download the frontmatter and verify that the table of contents matches at least three randomly-selected papers
   - [ ] Download 3–5 PDFs (including the first and last one) and make sure they match the paper's metadata (title, authors, page numbers, etc)
   - [ ] Search the PDFs for "Anonymous ACL submission" or similar to identify non-final uploaded papers

After the PR is closed, for all events:
- [ ] Archive the ingestion materials in format `YYYY-MM-DD-{event}`

Create followup issues for the following tasks (usually just for ACL events)
- [ ] Create DOIs
- [ ] Ingest videos
- [ ] Add awards
