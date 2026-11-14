"""Tests for preview workflow concurrency."""

from pathlib import Path
import shutil
import subprocess

import pytest
import yaml


@pytest.fixture
def workflow():
    path = Path(__file__).resolve().parent.parent / ".github/workflows/preview.yml"
    return yaml.safe_load(path.read_text())


def test_only_scheduled_preview_builds_can_cancel_running_previews(workflow):
    assert "concurrency" not in workflow
    assert "concurrency" not in workflow["jobs"]["decide"]
    preview = workflow["jobs"]["preview"]
    assert "needs.decide.outputs.should_build == 'true'" in preview["if"]
    assert preview["concurrency"] == {
        "group": "preview-${{ github.event.pull_request.number }}",
        "cancel-in-progress": True,
    }


@pytest.mark.parametrize("already_notified", [False, True])
def test_preview_notification_uses_current_checklist(workflow, already_notified):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the preview notification tests")
    step = next(
        step
        for step in workflow["jobs"]["preview"]["steps"]
        if step.get("name") == "Notify ingestion reviewers of preview"
    )
    script = step["with"]["script"].replace(
        "${{ steps.extract_branch.outputs.branch }}", "preview-branch"
    )
    setup = """
import assert from 'node:assert/strict';
const heading = 'Navigate to the preview site and check the following:';
const linkedHeading = 'Navigate to [the preview](https://preview.aclanthology.org/preview-branch) site and check the following:';
const checklist = '   - [x] Preserve this completed check';
const marker = '<!-- ingestion-preview-pr-7 -->';
const pr = {
  number: 7,
  title: 'Ingest SampleConf',
  body: `Closes #12.\\n\\n${heading}\\n${checklist}\\n\\nNew maintainer notes.`,
};
const context = {
  repo: { owner: 'sample', repo: 'anthology' },
  payload: { pull_request: { number: 7, title: 'Old title', body: 'Old body' } },
};
const updates = [];
const comments = [];
const listComments = () => {};
const github = {
  rest: {
    pulls: {
      get: async args => {
        assert.deepEqual(args, { owner: 'sample', repo: 'anthology', pull_number: 7 });
        return { data: pr };
      },
      update: async args => { updates.push(args); },
    },
    issues: {
      listComments,
      createComment: async args => { comments.push(args); },
    },
  },
  graphql: async (query, args) => {
    assert.equal(args.number, 7);
    return { repository: { pullRequest: { closingIssuesReferences: { nodes: [{
      number: 12, repository: { name: 'anthology', owner: { login: 'sample' } },
    }] } } } };
  },
  paginate: async (method, args) => {
    assert.equal(method, listComments);
    assert.equal(args.issue_number, 12);
    return alreadyNotified ? [{ body: marker }] : [];
  },
};
async function notify() {
"""
    assertions = """
}
await notify();
assert.equal(updates.length, 1);
assert.equal(updates[0].body, pr.body.replace(heading, linkedHeading));
assert.equal(comments.length, alreadyNotified ? 0 : 1);
if (!alreadyNotified) {
  assert.equal(comments[0].issue_number, 12);
  assert.ok(comments[0].body.includes(`${linkedHeading}\\n${checklist}`));
  assert.ok(comments[0].body.includes(marker));
}
"""
    source = (
        f"const alreadyNotified = {str(already_notified).lower()};\n"
        + setup
        + script
        + assertions
    )
    subprocess.run([node, "--input-type=module"], input=source, text=True, check=True)
