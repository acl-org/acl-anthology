#!/usr/bin/env python3

"""Usage: update_author-page_issues.py

Updates all issues containing "Author page:" in the title to follow the latest template

Set your OS environment variable "GITHUB_TOKEN" to your personal token or hardcode it in the code. Make sure to not reveal it to others!

"""

import os
import textwrap
import requests

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Can hardcode token here
REPO_OWNER = 'acl-org'
REPO_NAME = 'acl-anthology'

# Base URL
BASE_URL = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}'

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}


def get_issues_with_title(title):
    issues_url = f'{BASE_URL}/issues'
    params = {'state': 'open', 'per_page': 100}
    issues = []

    while issues_url:
        response = requests.get(issues_url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()

        for issue in data:
            if title in issue.get('title', '') and 'pull_request' not in issue:
                issues.append(issue)

        issues_url = response.links.get('next', {}).get('url')

    return issues


def add_comment_to_issue(issue_number, comment):
    url = f'{BASE_URL}/issues/{issue_number}/comments'
    payload = {'body': comment}
    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    print(f'Comment added to issue #{issue_number}')


def edit_body_of_issue(issue_number, new_body):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}'
    payload = {'body': new_body}
    response = requests.patch(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    print(f'Edited body of issue (ID: {issue_number}) updated.')


def main(issue_ids):
    print('🔎 Fetching issues...')
    issues = get_issues_with_title("Author Page:") + get_issues_with_title("Author Metadata:")
    print(f"Found {len(issues)} issues.")

    for issue in issues:
        number = issue["number"]

        if issue_ids and number not in issue_ids:
            # print(f"Skipping issue #{number}: {issue['title']}")
            continue

        print(f'---\nProcessing issue #{number}: {issue["title"]}')

        issue_body = issue["body"]
        if "### Author ORCID" not in issue_body:
            issue_body_list = issue_body.split("### Type of Author Metadata Correction")
            issue_body_list.insert(
                1,
                textwrap.dedent("""
                    ### Author ORCID

                    -Add ORCID here-

                    ### Institution of highest (anticipated) degree

                    -Add insitution here-
                                
                    ### Your papers (if required, see comment below)
                    
                    -Provide Anthology IDs or Anthology URLs here-

                    ### Type of Author Metadata Correction
                """),
            )
            issue_body = "".join(issue_body_list)
            edit_body_of_issue(number, issue_body)

            add_comment_to_issue(
                number,
                textwrap.dedent("""
                    Hello: we are attempting to close out a large backlog of author page requests. As part of these efforts,
                    we are collecting additional information which will help us assign papers to the correct author
                    in the future. Please modify the updated description above with the requested information.

                    If you are requesting to split an author page (i.e., your page has some papers that are not yours),
                    please also provide a list of your papers, in the form of Anthology IDs or URLS 
                    (e.g., 2023.wmt-1.13 or https://aclanthology.org/2023.wmt-1.13/).
                """)
            )


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Update author page issues')
    parser.add_argument('issue_ids', nargs='+', type=int, help='List of issue IDs to update')
    args = parser.parse_args()

    main(args.issue_ids)
