
"""Usage: update_author-page_issues.py

Updates all issues containing "Author page:" in the title to follow the latest template

Set your OS environment variable "GITHUB_TOKEN" to your personal token or hardcode it in the code. Make sure to not reveal it to others!

"""

import os
import requests

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") #Can hardcode token here
REPO_OWNER = 'acl-org'
REPO_NAME = 'acl-anthology'

# Base URL
BASE_URL = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}'

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
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

def main():
    print('🔎 Fetching issues...')
    issues = get_issues_with_title("Author Page:")

    for issue in issues:
        number = issue["number"]
        print(f'---\nProcessing issue #{number}: {issue["title"]}')
        
        add_comment_to_issue(number, "Hi! We have just added a few new fields to help us manage our database of author pages better. You can see the new fields in the body of the issue. Please fill these out and let us know when done so that we can continue working on your issue. Thank you for your coperation!")
        
        issue_body = issue["body"]
        if "### Author ORCID" not in issue_body:
            issue_body_list = issue_body.split("### Type of Author Metadata Correction")
            issue_body_list.insert(1, "### Author ORCID\n\n-Add ORCID here-\n\n### Institution of highest (anticipated) degree\n\n-Add insitution here-\n\n### Author Name (only if published in another script)\n\n -add author name here if needed-\n\n### Is the authors name read right to left? (only if published in another script)\n\n- [ ] Script is read right-to-left.\n\n### Type of Author Metadata Correction")
            issue_body = "".join(issue_body_list)
            edit_body_of_issue(number, issue_body)


if __name__ == '__main__':
    main()
