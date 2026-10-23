# Maintaining organizer checklists and reminders

The workflows are runners, not the source of submission instructions.

| To change | Edit |
| --- | --- |
| Shared organizer tasks | [checklists/common.md](checklists/common.md) |
| Platform, ISBN, or new-venue instructions | The corresponding file in [checklists/](checklists/) |
| Timeline layout and checklist introduction | [timeline.md](timeline.md) |
| Reminder comment wording | [reminder.md](reminder.md) |
| Deadlines, reminder cadence, question labels, or checklist selection | [settings.json](settings.json) |
| Full reference documentation | [Information for Submitters](../../hugo/content/info/contrib.md) |

## Editing tasks

Tasks are ordinary Markdown with a stable identifier:

```markdown
- [ ] Deliver the versioned snapshot. <!-- task:deliver-snapshot due:delivery context:submission -->
```

Keep the `task:` ID when improving wording: that preserves completed checkmarks.
Use a new ID for a genuinely new requirement. IDs must be unique across all
checklist files and use lowercase letters, numbers, and hyphens.

Optional attributes:

- `due:publication`, `due:delivery`, or `due:freeze` associates a task with a
  named milestone. Without `due:`, a task has no automatic deadline or pings.
- `when:` limits a task to one supported condition: `current`, `historical`,
  `acl`, `new-venue`, `softconf`, `openreview`, `easychair`,
  `unknown-platform`, or `unknown-affiliation`.
- `context:submission` requests reconfirmation when the venue, volume title,
  platform selections, or new-venue status changes. Changed task dates and
  date placeholders also request reconfirmation.

The `checklists` list in the settings selects whole files. All conditions in
an entry's `when` array must hold. Mixed-platform submissions receive all
applicable checklists without duplicating shared tasks. These are named
conditions, not executable expressions.

## Dates and placeholders

The publication answer and optional earlier cutoff must be real `YYYY-MM-DD`
dates. Delivery is publication minus `delivery_days_before_publication`.
The cutoff target is the earlier explicitly agreed date, or the delivery
deadline if no earlier date is recorded. Unknown or invalid dates are shown
for clarification, not invented. An invalid or too-late cutoff has no automatic
cutoff reminder until corrected.

The explicit historical-material checkbox preserves the historical ORCID
exception and disables automatic delivery dates. Do not mark a current
submission historical merely because its deadline has passed.

Supported placeholders:

- Task text: `{{publication_date}}`, `{{delivery_date}}`, `{{freeze_date}}`.
- Timeline: those dates plus `{{notes}}`, `{{checklists}}`,
  `{{reminder_lead_days}}`, and `{{overdue_interval_days}}`. Cadence text uses
  the same settings as the scheduler.
- Reminder: `{{issue_creator}}`, `{{issue_url}}`, and `{{reminders}}`.

Keep these placeholders spelled exactly as shown. Invalid settings, missing
templates, duplicate task IDs, and unknown placeholders fail validation before
the automation writes anything.

## Reminder policy

The current settings send one warning seven days before a dated task's deadline
and daily starting the day after it. There is no deadline-day ping. Change the
lead-day list or overdue interval in the settings to adjust this policy.

Only open, `ingestion`-labeled issues with a generated checklist receive pings.
Each comment mentions the issue creator and groups all reminders due that day.
Completed tasks stop receiving reminders, as do closed issues. Existing staff
assignees are not changed. Bot comment markers prevent duplicate notifications
on reruns; a missed schedule does not generate a backlog of comments.

GitHub Actions checks daily using UTC dates; execution times are best effort.
Six-month outreach to conferences is separate and is not implemented here.

## Updating and testing

An issue action adds the plan after submission and refreshes it when answers
change. The daily reminder check also refreshes existing managed plans, so
wording and settings changes take effect without asking organizers to resubmit.
Only the generated section is replaced; original answers and notes outside it
are preserved. Organizers should only toggle checkboxes inside that section.
Unexpected manual edits there are reported rather than overwritten.

Run the dependency-free tests with Node 24:

```sh
node --test .github/scripts/ingestion-guidance.test.cjs
```

The manual **Update ingestion submission guidance** workflow accepts an issue
number and defaults to a dry run. It can explicitly opt an older form-based
request into the generated plan. The **Remind ingestion submitters** workflow
also offers a dry run, optionally restricted to one issue. Dry runs log proposed
changes without editing issues or posting comments.

Test actual GitHub form rendering and task ticking only in an approved test
context. Do not create production test issues or send test pings automatically.
