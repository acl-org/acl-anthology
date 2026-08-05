# Correction Scripts

Scripts for processing corrections to metadata for papers and authors.
Updates are reflected in changes to volume files (in data/xml/)
and the author database (data/json/people.json). Changes to PDFs and attachments
are not supported, nor are volume-level changes.

## Bulk author scripts: issue-based

These scripts query the GitHub issue tracker and use their data to implement
corrections in a branch. Specific issue numbers may be given as arguments;
otherwise, all relevant issues will be retrieved.

Before running the script it is necessary to obtain a Personal Access Token
and store it in the `GITHUB_TOKEN` environment variable.

Currently these scripts should be run with `--dry-run` to avoid triggering
a new PR (which requires elevated privileges).

- `bulk_process_metadata.py`: For paper metadata issues updating the title, abstract,
and/or author list. _Volume_ metadata issues are currently unsupported.

- `bulk_process_simple_verifications.py`: For issues that merely request to verify
an unverified author page with ORCID.

## Bulk author scripts: non-issue-based

- `refresh_or_orcids.py`: For authors with an OpenReview ID stored on one or more
papers, but no ORCID, query the OpenReview API to try to obtain the ORCID.
Requires specifying OpenReview account credentials in environment variables.

## Non-bulk author scripts

These are run specifying particular authors as arguments.
An issue number may be provided with the `--issue` flag,
but this is only used for commit messages.

- `batch_edit_person_name_on_papers.py`: Edit an author's name across their
papers (or limit to a subset of their papers).

- `disable_name_matching.py`: Update existing verified authors to prevent
implicit matching to papers.

- `fetch_orcid_from_openreview.py`: Fetch a single OpenReview user's ORCID iD.

- `rename_person.py`: Change an author ID.

- `unlink_items.py`: Remove explicitly linked papers from a verified author.

- `verify_author.py`: Add ORCID/degree to verify an author; also allows
merging additional authors, or listing specific papers to link
(or exclude from linking) to the author.

## Other scripts

- `convert_markdown_in_abstracts.py`: Go through the abstracts in the database
and improve formatting: convert Markdown to text markup XML; linkify URLs;
apply smart quotes; and other touch-ups.

- `likely_name_split.py`: Examine names in the database and apply heuristics
to suggest likely errors in first/last splits.
