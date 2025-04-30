from github import Github
import sys
import os

github_token = os.getenv("GITHUB_TOKEN")
github = Github(github_token)
github_repo = github.get_repo("acl-org/acl-anthology")

pr = github_repo.create_pull(
    title=f"Bulk metadata corrections",
    body="Automated PR for bulk metadata corrections",
    head="bulk-corrections-2024-12-31",
    base="master",
)

print(f"Created PR: {pr.html_url}", file=sys.stderr)
