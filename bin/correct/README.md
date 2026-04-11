# Correction Scripts

Scripts for processing corrections to metadata for papers and authors.
Updates are reflected in changes to volume files (in data/xml/)
and the author database (data/yaml/people.yaml). Changes to PDFs and attachments
are not supported, nor are volume-level changes.

## Bulk processing scripts

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

## Non-bulk processing scripts

These are run specifying particular authors as arguments.
An issue number may be provided with the `--issue` flag,
but this is only used for commit messages.

- `disable_name_matching.py`: Updates existing verified authors to prevent
implicit matching to papers.

- `rename_person.py`: Change an author ID.

- `unlink_items.py`: Removes explicitly linked papers from a verified author.

- `verify_author.py`: Add ORCID/degree to verify an author; also allows
merging additional authors, or listing specific papers to link
(or exclude from linking) to the author.
