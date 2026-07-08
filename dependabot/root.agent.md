# Dependabot Agent

This file documents Dependabot-related configuration guidance and agent behavior for this repository.

## Recommended Dependabot setup

GitHub Dependabot configuration is normally stored in `.github/dependabot.yml`.
For this repository, a typical configuration includes:

- `package-ecosystem: "pip"` for Python dependency updates
- `package-ecosystem: "github-actions"` for workflow updates
- a `schedule` such as `weekly`
- `open-pull-requests-limit` to avoid flooding the repo

## Example configuration

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

## Agent instructions

Use this document to guide automation or review tooling that handles Dependabot changes.

- Validate that new Dependabot PRs update only dependency-related files.
- Confirm the repository still passes test or lint checks after dependency bumps.
- Prefer small, frequent updates over large batch upgrades.
- If a direct dependency bump causes failures, flag the PR for manual review.

## Next steps

If desired, add `.github/dependabot.yml` and define the exact update policy for this repository.
